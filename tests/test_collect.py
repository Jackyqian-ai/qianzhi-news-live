import importlib.util
from pathlib import Path
import tempfile
import sqlite3
import unittest
spec=importlib.util.spec_from_file_location('collector',Path(__file__).resolve().parents[1]/'scripts/collect.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class CollectorTests(unittest.TestCase):
 def test_cache_time_is_not_publication(self):
  rows=c.parse_hotlist({'status':'cache','updatedTime':1791257994876,'items':[{'title':'新闻','url':'https://example.com/a'}]},'zhihu','2026-10-06T12:00:00+08:00')
  self.assertEqual(rows[0]['upstream_status'],'cache')
  self.assertIsNone(rows[0]['published_at'])
  self.assertNotEqual(rows[0]['upstream_updated_at'],rows[0]['collected_at'])
 def test_invalid_upstream_status_rejected(self):
  with self.assertRaises(ValueError):c.parse_hotlist({'status':'error','items':[]},'zhihu','x')
 def test_rss_age_timezone_future(self):
  raw=b'''<rss><channel>
   <item><title>Old</title><pubDate>Sun, 04 Oct 2026 00:00:00 +0800</pubDate></item>
   <item><title>Recent</title><pubDate>Tue, 06 Oct 2026 10:00:00 +0800</pubDate></item>
   <item><title>NoTZ</title><pubDate>2026-10-06T10:00:00</pubDate></item>
   <item><title>Future</title><pubDate>2026-10-07T10:00:00+08:00</pubDate></item>
   <item><title>Undated</title></item>
  </channel></rss>'''
  rows=c.parse_feed(raw,'rss','2026-10-06T12:00:00+08:00',24)
  self.assertEqual([r['title'] for r in rows],['Recent','NoTZ','Future','Undated'])
  self.assertEqual([r['publication_status'] for r in rows],['explicit','timezone_unspecified','future_timestamp','missing'])
 def test_atom_alternate_link(self):
  raw=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom</title><link rel="self" href="https://example.com/self"/><link href="https://example.com/article"/><published>2026-10-06T00:00:00Z</published><summary>text</summary></entry></feed>'''
  r=c.parse_feed(raw,'atom','2026-10-06T12:00:00+08:00',24)[0]
  self.assertEqual(r['url'],'https://example.com/article')
 def test_html_response_rejected(self):
  with self.assertRaises(ValueError):c.parse_feed(b'<html><body>Blocked</body></html>','rss','2026-10-06T12:00:00+08:00',24)
 def test_same_run_duplicate_is_one_observation(self):
  x=c.parse_hotlist({'status':'success','items':[{'title':'One','url':'https://example.com/a'}]},'a','2026-10-06T12:00:00+08:00')[0]
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'test.db'
   for i in ['1','2']:
    c.save_database(db,{'id':i,'started_at':'a','completed_at':'b'},[],[x,x])
   with sqlite3.connect(db) as conn:
    self.assertEqual(conn.execute('select count(*),max(observation_count) from items').fetchone(),(1,2))
    self.assertEqual(conn.execute('select count(*) from observations').fetchone()[0],2)

class ConfigTests(unittest.TestCase):
 def test_custom_unicode_archive_and_data_directories(self):
  import json
  with tempfile.TemporaryDirectory() as td:
   vault=Path(td)/'My Vault';vault.mkdir();vault=vault.resolve()
   cfg=Path(td)/'local.json'
   cfg.write_text(json.dumps({'vault':str(vault),'news_dir':'资讯/每日新闻','data_dir':'原始/新闻'}))
   resolved=c.load_settings(cfg)
   self.assertEqual(resolved['news_dir'],vault/'资讯/每日新闻')
   self.assertEqual(resolved['data_dir'],vault/'原始/新闻')
 def test_escape_and_nested_paths_rejected(self):
  import json
  with tempfile.TemporaryDirectory() as td:
   vault=Path(td)/'vault';vault.mkdir();cfg=Path(td)/'config.json'
   for news,data in [('../outside','raw'),('news','news/raw'),('news/raw','news'),('same','same')]:
    cfg.write_text(json.dumps({'vault':str(vault),'news_dir':news,'data_dir':data}))
    with self.assertRaises(ValueError):c.load_settings(cfg)
 def test_configure_preserves_existing_choice(self):
  import subprocess
  with tempfile.TemporaryDirectory() as td:
   script=Path(__file__).resolve().parents[1]/'scripts/configure.py'
   import sys
   base=[sys.executable,str(script),'--vault',td]
   first=subprocess.run(base+['--news-dir','资讯'],capture_output=True)
   self.assertEqual(first.returncode,0,first.stderr)
   cfg=Path(td)/'.news-live.json';before=cfg.read_bytes()
   denied=subprocess.run(base+['--news-dir','Other'],capture_output=True)
   self.assertNotEqual(denied.returncode,0)
   self.assertEqual(cfg.read_bytes(),before)
   replaced=subprocess.run(base+['--news-dir','Other','--replace'],capture_output=True)
   self.assertEqual(replaced.returncode,0,replaced.stderr)

if __name__=='__main__':unittest.main()
