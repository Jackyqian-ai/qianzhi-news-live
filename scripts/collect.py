#!/usr/bin/env python3
"""On-demand public hotlist/RSS collection; standard library, no Docker or keys."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
import json
from pathlib import Path
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Shanghai')
API = 'https://newsnow.busiyi.world/api/s'
HOTLISTS = [('zhihu','知乎'), ('weibo','微博'), ('douyin','抖音'),
 ('bilibili','B站'), ('baidu','百度热搜'), ('toutiao','今日头条'),
 ('tieba','贴吧'), ('thepaper','澎湃新闻'), ('ifeng','凤凰网'),
 ('36kr-renqi','36氪'), ('wallstreetcn','华尔街见闻'), ('cls','财联社')]
FEEDS = [('tmtpost','钛媒体','https://www.tmtpost.com/feed'),
 ('eeo','经济观察报','https://www.eeo.com.cn/rss.xml')]


def now():
    return datetime.now(TZ)


def stamp(value):
    """Normalize upstream times without inventing a missing timezone."""
    if value is None or value == '':
        return None, 'missing'
    try:
        if isinstance(value, (int,float)) or re.fullmatch(r'\d{10,13}', str(value)):
            n = float(value)
            dt = datetime.fromtimestamp(n / 1000 if n > 1e11 else n, timezone.utc)
        else:
            raw = str(value).strip()
            try:
                dt = datetime.fromisoformat(raw.replace('Z','+00:00'))
            except ValueError:
                dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            return dt.isoformat(), 'timezone_unspecified'
        return dt.astimezone(TZ).isoformat(), 'explicit'
    except (ValueError,TypeError,OverflowError,OSError):
        return None, 'unparsed'


def plain(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]*>', ' ', str(value or '')))).strip()


def public_url(value):
    p = urllib.parse.urlsplit(str(value or '').strip())
    return str(value).strip() if p.scheme in ('http','https') and p.hostname and not p.username else ''


def identity(kind, source, title, url):
    # Source-local identity preserves cross-platform corroboration; semantic event merge is human work.
    return hashlib.sha256(f'{kind}\0{source}\0{url or title}'.encode()).hexdigest()


def parse_hotlist(data, source, collected):
    if not isinstance(data,dict) or data.get('status') not in ('success','cache'):
        raise ValueError('hotlist upstream status is not success/cache')
    if not isinstance(data.get('items'),list):
        raise ValueError('hotlist items is not a list')
    updated, confidence = stamp(data.get('updatedTime'))
    result=[]
    for rank, item in enumerate(data['items'],1):
        if not isinstance(item,dict):
            continue
        title=plain(item.get('title'))
        if not title:
            continue
        url=public_url(item.get('url')) or public_url(item.get('mobileUrl'))
        result.append({'key':identity('hotlist',source,title,url),'kind':'hotlist',
          'source_id':source,'title':title,'url':url,'rank':rank,'summary':'',
          'published_at':None,'publication_status':'not_provided',
          'upstream_updated_at':updated,'upstream_time_status':confidence,
          'upstream_status':data['status'],'collected_at':collected})
    return result


def parse_feed(raw, source, collected, hours):
    root=ET.fromstring(raw)
    local=lambda e: e.tag.rsplit('}',1)[-1]
    entries=[e for e in root.iter() if local(e) in ('item','entry')]
    if local(root) not in ('rss','feed','RDF'):
        raise ValueError('response is not RSS/Atom')
    cutoff=datetime.fromisoformat(collected)-timedelta(hours=hours)
    rows=[]
    for entry in entries:
        fields={}
        url=''
        for e in entry:
            tag=local(e)
            fields.setdefault(tag,''.join(e.itertext()).strip())
            if tag=='link':
                if e.attrib.get('href') and e.attrib.get('rel','alternate')=='alternate':
                    url=e.attrib['href']
                elif e.text and not url:
                    url=e.text.strip()
        title=plain(fields.get('title'))
        if not title:
            continue
        url=public_url(url)
        rawdate=fields.get('pubDate') or fields.get('published') or fields.get('date')
        published, confidence=stamp(rawdate)
        pubstatus=confidence
        if published and confidence=='explicit':
            dt=datetime.fromisoformat(published)
            if dt < cutoff:
                continue
            if dt > datetime.fromisoformat(collected)+timedelta(minutes=5):
                pubstatus='future_timestamp'
        rows.append({'key':identity('rss',source,title,url),'kind':'rss',
          'source_id':source,'title':title,'url':url,'rank':None,
          'summary':plain(fields.get('description') or fields.get('summary') or fields.get('content'))[:2500],
          'published_at':published,'published_raw':rawdate,'publication_status':pubstatus,
          'feed_updated_at':fields.get('updated'),
          'upstream_updated_at':None,'upstream_time_status':'not_provided',
          'upstream_status':'feed','collected_at':collected})
    return rows


def fetch(spec, rawdir, hours, timeout):
    kind, sid, name, url=spec
    status={'kind':kind,'source_id':sid,'name':name,'request_url':url,
      'started_at':now().isoformat(),'status':'failed','attempts':0}
    rows=[]
    for attempt in range(2):
        status['attempts']=attempt+1
        try:
            req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0',
              'Accept':'application/json, application/rss+xml, application/atom+xml, */*',
              'Accept-Language':'zh-CN,zh;q=0.9,en;q=0.8'})
            with urllib.request.urlopen(req,timeout=timeout) as response:
                raw=response.read(4_000_001)
                if len(raw)>4_000_000:
                    raise ValueError('response exceeds 4MB')
                status['http_status']=response.status
                status['response_date']=response.headers.get('Date')
            completed=now().isoformat()
            path=rawdir/(sid+('.json' if kind=='hotlist' else '.xml'))
            path.write_bytes(raw)
            status['raw_file']=str(path)
            rows=parse_hotlist(json.loads(raw),sid,completed) if kind=='hotlist' else parse_feed(raw,sid,completed,hours)
            status.update(status='success',items=len(rows),completed_at=completed)
            if kind=='hotlist':
                obj=json.loads(raw)
                status['upstream_status']=obj.get('status')
                status['upstream_updated_at'], status['upstream_time_status']=stamp(obj.get('updatedTime'))
            status.pop('error',None)
            break
        except (urllib.error.URLError,TimeoutError,OSError,ValueError,ET.ParseError) as e:
            status['error']=f'{type(e).__name__}: {e}'
            if isinstance(e,urllib.error.HTTPError):
                status['http_status']=e.code
                if 400<=e.code<500 and e.code not in (408,429):
                    break
            if attempt==0:
                time.sleep(1)
    status.setdefault('completed_at',now().isoformat())
    return status, rows


def save_database(dbpath, run, statuses, items):
    with sqlite3.connect(dbpath) as db:
        db.executescript('''
          CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, started_at TEXT, completed_at TEXT);
          CREATE TABLE IF NOT EXISTS source_status(run_id TEXT, source_id TEXT, detail TEXT,
            PRIMARY KEY(run_id,source_id));
          CREATE TABLE IF NOT EXISTS items(key TEXT PRIMARY KEY, first_seen_at TEXT, last_seen_at TEXT,
            observation_count INTEGER, detail TEXT);
          CREATE TABLE IF NOT EXISTS observations(run_id TEXT, item_key TEXT,
            PRIMARY KEY(run_id,item_key));
        ''')
        db.execute('INSERT INTO runs VALUES(?,?,?)',(run['id'],run['started_at'],run['completed_at']))
        for s in statuses:
            db.execute('INSERT INTO source_status VALUES(?,?,?)',(run['id'],s['source_id'],json.dumps(s,ensure_ascii=False)))
        unique={x['key']:x for x in items}
        for key,x in unique.items():
            db.execute('''INSERT INTO items VALUES(?,?,?,1,?) ON CONFLICT(key) DO UPDATE SET
              last_seen_at=excluded.last_seen_at, observation_count=items.observation_count+1,
              detail=excluded.detail''',(key,x['collected_at'],x['collected_at'],json.dumps(x,ensure_ascii=False)))
            db.execute('INSERT INTO observations VALUES(?,?)',(run['id'],key))


def load_settings(config_path):
    """Resolve an explicit local vault configuration; never infer another user's vault."""
    settings=json.loads(Path(config_path).expanduser().read_text(encoding='utf-8'))
    vault=Path(settings['vault']).expanduser().resolve()
    if not vault.is_dir():
        raise ValueError('Configured vault does not exist')
    resolved={'vault':vault}
    for key,default in [('news_dir','1.输入/新闻资讯'),('data_dir','9.系统/news-live-data')]:
        path=Path(settings.get(key,default)).expanduser()
        path=(path if path.is_absolute() else vault/path).resolve()
        if path==vault or vault not in path.parents:
            raise ValueError(key+' must be a subdirectory of the selected vault')
        resolved[key]=path
    if (resolved['news_dir']==resolved['data_dir'] or
        resolved['news_dir'] in resolved['data_dir'].parents or
        resolved['data_dir'] in resolved['news_dir'].parents):
        raise ValueError('news_dir and data_dir must be separate non-nested directories')
    return resolved


def main():
    p=argparse.ArgumentParser(description=__doc__)
    destination=p.add_mutually_exclusive_group(required=True)
    destination.add_argument('--output',type=Path,help='Raw collection directory, not AI news notes')
    destination.add_argument('--config',type=Path,help='Local .news-live.json configuration')
    p.add_argument('--hours',type=int,default=24,help='RSS lookback; undated entries remain flagged')
    p.add_argument('--sources',help='Optional comma-separated source IDs for a targeted rerun')
    p.add_argument('--timeout',type=int,default=12)
    a=p.parse_args()
    if a.config:
        try:
            a.output=load_settings(a.config)['data_dir']
        except (OSError,ValueError,KeyError) as e:
            p.error(str(e))
    a.output=a.output.expanduser().resolve()
    if not 1<=a.hours<=168 or not 1<=a.timeout<=30:
        p.error('hours must be 1..168 and timeout 1..30')
    started=now()
    specs=[('hotlist',sid,name,API+'?'+urllib.parse.urlencode({'id':sid})+'&latest') for sid,name in HOTLISTS]
    specs += [('rss',sid,name,url) for sid,name,url in FEEDS]
    if a.sources:
        chosen=set(a.sources.split(','))
        unknown=chosen-{s[1] for s in specs}
        if unknown:p.error('Unknown sources: '+','.join(sorted(unknown)))
        specs=[s for s in specs if s[1] in chosen]
    day=a.output/started.strftime('%Y-%m-%d')
    runid=started.strftime('%H%M%S')+'-'+uuid.uuid4().hex[:8]
    rundir=day/runid
    rawdir=rundir/'raw'
    rawdir.mkdir(parents=True)
    statuses=[]
    items=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for status,rows in pool.map(lambda s:fetch(s,rawdir,a.hours,a.timeout),specs):
            statuses.append(status)
            items.extend(rows)
    run={'id':runid,'started_at':started.isoformat(),'completed_at':now().isoformat(),
       'source':'news-live direct public collection','rss_lookback_hours':a.hours,
       'coverage':'invocation snapshot; not continuous monitoring or whole-day heat',
       'source_status':statuses,'items':items}
    (rundir/'snapshot.json').write_text(json.dumps(run,ensure_ascii=False,indent=2))
    save_database(day/'news-live.sqlite3',run,statuses,items)
    summary={'snapshot':str(rundir/'snapshot.json'),'database':str(day/'news-live.sqlite3'),
      'started_at':run['started_at'],'completed_at':run['completed_at'],'items':len(items),
      'successful_sources':[s['source_id'] for s in statuses if s['status']=='success'],
      'failed_sources':[{'id':s['source_id'],'error':s.get('error')} for s in statuses if s['status']=='failed']}
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0 if any(s['status']=='success' for s in statuses) else 2

if __name__=='__main__':
    sys.exit(main())
