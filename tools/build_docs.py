"""Build a self-contained, offline Chinese reading entry from repository sources."""
import html
from html.parser import HTMLParser
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
REF=Path('skills/jianying-codex-toolkit/references')
PAGES=[('start','开始使用',Path('README.md')),('learn','学习路线',Path('docs/learning.md')),
       ('scenes','六类场景',REF/'scenarios.md'),('plan','剪辑计划',REF/'plan-format.md'),
       ('backends','平台与后端',REF/'backends.md'),('revise','修改与审片',REF/'revisions.md'),
       ('share','版本与发布',Path('docs/releases/v0.1.1.md'))]

def inline(s):
    s=html.escape(s)
    s=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<a href="\2">\1</a>',s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)

def render(s):
    lines=s.splitlines();out=[];n=0
    while n<len(lines):
        line=lines[n]
        if not line.strip():n+=1;continue
        if line.startswith('```'):
            code=[];n+=1
            while n<len(lines) and not lines[n].startswith('```'):code.append(lines[n]);n+=1
            out.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>');n+=1;continue
        h=re.match(r'^(#{1,5}) (.+)',line)
        if h:
            level=len(h[1])+1;out.append(f'<h{level}>'+inline(h[2])+f'</h{level}>');n+=1;continue
        if line.startswith('|'):
            rows=[]
            while n<len(lines) and lines[n].startswith('|'):
                cells=[c.strip() for c in lines[n].strip('|').split('|')]
                if not all(re.fullmatch(':?-+:?',c) for c in cells):rows.append(cells)
                n+=1
            out.append('<div class="scroll"><table><thead><tr>'+''.join('<th scope="col">'+inline(c)+'</th>' for c in rows[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in row)+'</tr>' for row in rows[1:])+'</tbody></table></div>');continue
        if line.startswith('- '):
            items=[]
            while n<len(lines) and lines[n].startswith('- '):items.append('<li>'+inline(lines[n][2:])+'</li>');n+=1
            out.append('<ul>'+''.join(items)+'</ul>');continue
        para=[line];n+=1
        while n<len(lines) and lines[n].strip() and not re.match(r'^(#|\||```|- )',lines[n]):para.append(lines[n]);n+=1
        out.append('<p>'+inline(' '.join(para))+'</p>')
    return '\n'.join(out)

def main():
    nav=''.join(f'<a href="#{key}">{title}</a>' for key,title,path in PAGES)
    body=''.join(f'<section id="{key}">{render((ROOT/path).read_text(encoding="utf-8"))}<a class="back" href="#top">回到目录</a></section>' for key,title,path in PAGES)
    css='''
    :root{--paper:#f5f3ed;--ink:#203129;--accent:#176547;--line:#c8d0c8;--muted:#4b5d52}*{box-sizing:border-box}body{margin:0;color:var(--ink);background:var(--paper);font:17px/1.85 system-ui,"Microsoft YaHei","PingFang SC",sans-serif}a{color:var(--accent);text-underline-offset:4px}a:focus-visible{outline:3px solid #ad4d20;outline-offset:4px}.layout{display:grid;grid-template-columns:240px minmax(0,1fr)}aside{position:sticky;top:0;height:100vh;padding:38px 25px;background:#e9ede5;border-right:1px solid var(--line)}.brand{font-size:22px;line-height:1.5;font-weight:700}nav{margin-top:30px}nav a{display:block;padding:12px 0;border-bottom:1px solid var(--line);text-decoration:none}.meta,footer{font-size:14px;color:var(--muted)}main{padding:54px 50px 80px;max-width:1080px;min-width:0}h1{font-size:42px;line-height:1.4;letter-spacing:-.02em;margin:20px 0}header p{max-width:36em;color:var(--muted)}h2{font-size:29px;line-height:1.5}h3{font-size:22px;margin-top:36px}section{margin-top:48px;padding-top:28px;border-top:1px solid var(--line)}p,li{max-width:42em}li{margin:10px 0}.scroll{overflow:auto}table{border-collapse:collapse;min-width:640px;font-size:14px}td,th{vertical-align:top;text-align:left;border-bottom:1px solid var(--line);padding:14px;min-width:110px}th{background:#e9ede5}pre{overflow:auto;padding:20px;background:#e5eae3;font-size:13px;line-height:1.7}code{font-family:Consolas,monospace;overflow-wrap:anywhere}p code,li code{font-size:.9em;background:#e5eae3;padding:2px 4px}.back{font-size:14px;display:inline-block;margin-top:20px}.skip{position:absolute;top:-100px;left:15px;background:var(--ink);color:white;padding:10px}.skip:focus{top:10px}footer{margin-top:50px}
    @media(max-width:800px){.layout{display:block}aside{position:static;height:auto;padding:24px;border-right:0;border-bottom:1px solid var(--line)}nav{display:grid;grid-template-columns:1fr 1fr;gap:0 20px;margin-top:18px}main{padding:30px 22px}h1{font-size:31px}h2{font-size:25px}body{font-size:16px}}
    @media print{aside,.back,.skip{display:none}.layout{display:block}main{padding:0;max-width:none}body{background:white;font-size:11pt}section{break-before:page}pre{white-space:pre-wrap}.scroll{overflow:visible}table{min-width:0}td,th{min-width:0}}
    '''
    doc='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codex × 剪映通用工具包</title><style>'+css+'</style></head><body id="top"><a class="skip" href="#start">跳到正文</a><div class="layout"><aside><div class="brand">Codex × 剪映<br>通用剪辑工具包</div><p class="meta">Anx Day 3 · v0.1.1<br>2026.10.21</p><nav aria-label="章节目录">'+nav+'</nav></aside><main><header><div class="meta">从一次实践，到多场景复用</div><h1>换一批素材，<br>也能从同一套方法开始。</h1><p>让场景决定剪法，用计划衔接判断与执行。包含可安装 Skill、本地工具、六种场景示例和可追溯的验证范围。</p><p><a href="docs/verification.json">查看实际测试范围</a> · <a href="skills/jianying-codex-toolkit/SKILL.md">阅读 Skill</a></p></header>'+body+'<footer>离线正文不加载外部脚本、字体或客户媒体。外部项目链接需联网。MIT原创代码；原生兼容、画面与实际听感按证据单独验收。</footer></main></div></body></html>'
    class Audit(HTMLParser):
        def __init__(self):super().__init__();self.ids=[];self.links=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if 'id' in a:self.ids.append(a['id'])
            if tag=='a':self.links.append(a['href'])
    audit=Audit();audit.feed(doc)
    assert len(audit.ids)==len(set(audit.ids))
    for link in audit.links:
        if link.startswith('#'):assert link[1:] in audit.ids,link
        elif not link.startswith('https://'):assert (ROOT/link).is_file(),link
    (ROOT/'开始使用.html').write_text(doc,encoding='utf-8')
    print(f'Built HTML: {len(PAGES)} sections; {len(audit.links)} links checked')

if __name__=='__main__':main()
