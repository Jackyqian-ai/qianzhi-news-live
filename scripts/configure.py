#!/usr/bin/env python3
"""Save local Obsidian destinations; no network and no generated news."""
import argparse
import json
from pathlib import Path
from collect import load_settings


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault',type=Path,required=True,help='Existing Obsidian vault')
    parser.add_argument('--news-dir',default='1.输入/新闻资讯',help='Notes directory relative to vault, or absolute inside it')
    parser.add_argument('--data-dir',default='9.系统/news-live-data',help='Raw data directory relative to vault, or absolute inside it')
    parser.add_argument('--config',type=Path,help='Config file location; default <vault>/.news-live.json')
    parser.add_argument('--replace',action='store_true',help='Explicitly replace an existing configuration')
    args=parser.parse_args()
    vault=args.vault.expanduser().resolve()
    if not vault.is_dir():parser.error('Selected vault does not exist')
    target=(args.config or vault/'.news-live.json').expanduser().resolve()
    settings={'vault':str(vault),'news_dir':args.news_dir,'data_dir':args.data_dir,
              'topics':['企业管理','AI应用','心理学']}
    if target.exists():
        try:old=json.loads(target.read_text(encoding='utf-8'))
        except (OSError,ValueError):old=None
        if old!=settings and not args.replace:
            parser.error('Existing config differs; use --replace only to change it intentionally')
    # Validate through a temporary local file before replacing an existing configuration.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td)/'config.json'
        tmp.write_text(json.dumps(settings,ensure_ascii=False),encoding='utf-8')
        try:resolved=load_settings(tmp)
        except (OSError,ValueError,KeyError) as e:parser.error(str(e))
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(settings,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'config':str(target),**{k:str(v) for k,v in resolved.items()}},ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
