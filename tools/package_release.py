"""Build versioned, source-only toolkit and self-contained Skill release assets."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tomllib
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ROOT_FILES={'README.md','README.en.md','LICENSE','THIRD_PARTY_NOTICES.md','CONTRIBUTING.md',
            'SECURITY.md','CHANGELOG.md','pyproject.toml','uv.lock','toolkit.py','.gitignore','开始使用.html'}
ROOT_DIRS={'.github','docs','examples','skills','tests','tools'}
EXCLUDE={'.venv','.git','__pycache__','outputs','demo-generated','dist'}
SUFFIXES={'.md','.py','.json','.toml','.lock','.txt','.html','.yml','.yaml'}

def source_files(root):
    root=Path(root).resolve();files=[]
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if set(rel.parts)&EXCLUDE or not p.is_file():continue
        if rel.as_posix()=='docs/anx-day3-copy.md':continue
        if not (len(rel.parts)==1 and rel.name in ROOT_FILES or len(rel.parts)>1 and rel.parts[0] in ROOT_DIRS):continue
        if p.is_symlink() or not p.resolve().is_relative_to(root):raise ValueError('发布源不允许链接: '+str(rel))
        if len(rel.parts)>1 and p.suffix not in SUFFIXES:raise ValueError('不支持的发行文件类型: '+str(rel))
        text=p.read_text(encoding='utf-8-sig')
        if re.search(r'[A-Za-z]:[\\/]+(?:Users|Projects)[\\/]+',text) or re.search(r'/(?:Users|home)/[A-Za-z0-9_.-]+/',text):raise ValueError('私人绝对路径: '+str(rel))
        if re.search(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b',text):raise ValueError('疑似凭据: '+str(rel))
        if '-----BEGIN '+'PRIVATE KEY-----' in text:raise ValueError('疑似私钥: '+str(rel))
        files.append(p)
    return files

def write_zip(path,entries):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(entries):
            info=zipfile.ZipInfo(name,date_time=(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3;info.external_attr=0o100644<<16
            z.writestr(info,data)
    with zipfile.ZipFile(path) as z:assert z.testzip() is None

def build(root,out):
    root=Path(root).resolve();out=Path(out).resolve()
    version=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?',version):raise ValueError('版本格式错误')
    names=[f'jianying-codex-toolkit-v{version}.zip',f'jianying-codex-toolkit-skill-v{version}.zip']
    targets=[out/n for n in names]+[out/'SHA256SUMS.txt',out/'release-manifest.json']
    if any(p.exists() for p in targets):raise FileExistsError('版本产物已存在；不覆盖已发版本')
    files=source_files(root)
    for required in ['LICENSE','README.md','skills/jianying-codex-toolkit/SKILL.md']:
        if not (root/required).is_file():raise ValueError('缺少发行文件: '+required)
    full=[('jianying-codex-toolkit/'+p.relative_to(root).as_posix(),p.read_bytes()) for p in files]
    skill_root=root/'skills/jianying-codex-toolkit'
    skill=[('jianying-codex-toolkit/'+p.relative_to(skill_root).as_posix(),p.read_bytes()) for p in files if p.is_relative_to(skill_root)]
    skill.append(('jianying-codex-toolkit/LICENSE',(root/'LICENSE').read_bytes()))
    if (root/'THIRD_PARTY_NOTICES.md').exists():skill.append(('jianying-codex-toolkit/THIRD_PARTY_NOTICES.md',(root/'THIRD_PARTY_NOTICES.md').read_bytes()))
    out.mkdir(parents=True,exist_ok=True)
    write_zip(targets[0],full);write_zip(targets[1],skill)
    artifacts=[dict(name=p.name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in targets[:2]]
    result=dict(version=version,source_files=len(files),artifacts=artifacts)
    with targets[2].open('x',encoding='utf-8',newline='\n') as f:f.write(''.join(a['sha256']+'  '+a['name']+'\n' for a in artifacts))
    with targets[3].open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=ROOT/'dist');args=parser.parse_args()
    print(json.dumps(build(ROOT,args.out),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
