"""Copy the self-contained skill to a new user-specified directory, never replace."""
import argparse
import os
from pathlib import Path
import shutil

def main():
    parser=argparse.ArgumentParser(description='安装到新技能目录；目标已存在则停止')
    default=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'skills'/'jianying-codex-toolkit'
    parser.add_argument('--dest',type=Path,default=default)
    args=parser.parse_args();source=Path(__file__).resolve().parents[1]/'skills/jianying-codex-toolkit'
    dest=args.dest.expanduser().resolve()
    if dest.exists():parser.error('目标已存在，不覆盖；请先比较版本或使用其他新目录')
    shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    print(dest)

if __name__=='__main__':main()
