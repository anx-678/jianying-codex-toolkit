"""Portable editing-plan CLI. Standard library core; optional native-draft adapter."""
import argparse
from fractions import Fraction
import html
import importlib.metadata
import json
import math
import os
from pathlib import Path, PureWindowsPath
import platform
import shutil
import subprocess
import sys
import tempfile

ASSETS=Path(__file__).resolve().parents[1]/'assets'
MEDIA={'.mp4':'video','.mov':'video','.mkv':'video','.webm':'video','.m4v':'video',
       '.mp3':'audio','.wav':'audio','.m4a':'audio','.aac':'audio','.flac':'audio',
       '.jpg':'image','.jpeg':'image','.png':'image','.webp':'image'}

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError('非有限数字: '+s)))

def write_new(path, obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        f.write(obj if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def profiles():return load(ASSETS/'scenes.json')

def fps_value(fps):
    rate=Fraction(str(fps))
    if not 1<=rate<=120:raise ValueError('fps 必须在 1–120 之间')
    return rate

def frame_us(frame,fps):return round(Fraction(frame)*1000000/fps_value(fps))

def media_path(root, relative):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute() or PureWindowsPath(relative).anchor:
        raise ValueError('素材必须使用相对路径')
    p=(root/relative).resolve()
    if not p.is_relative_to(root.resolve()):raise ValueError('素材越出根目录')
    if not p.is_file():raise ValueError('素材不存在: '+relative)
    return p

def run(cmd,cwd=None):
    result=subprocess.run([str(c) for c in cmd],capture_output=True,text=True,encoding='utf-8',errors='replace',cwd=cwd)
    if result.returncode:raise ValueError(result.stderr[-4000:] or result.stdout[-4000:])
    return result.stdout

def inventory(root, ffprobe=None, mediainfo=False):
    root=Path(root).resolve()
    if not root.is_dir():raise ValueError('素材根目录不存在')
    if mediainfo:
        from pymediainfo import MediaInfo
    rows=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.suffix.lower() not in MEDIA:continue
        if not p.resolve().is_relative_to(root):raise ValueError('素材链接越出根目录: '+p.name)
        kind=MEDIA[p.suffix.lower()];st=p.stat()
        row=dict(id=f'M{len(rows)+1:04d}',path=p.relative_to(root).as_posix(),kind=kind,
                 size_bytes=st.st_size,mtime_ns=st.st_mtime_ns,duration_us=None,
                 width=None,height=None,has_audio=None,probe_status='unavailable')
        if mediainfo:
            try:
                info=MediaInfo.parse(str(p))
                visual=next((t for t in info.tracks if t.track_type in ['Video','Image']),None)
                audio=any(t.track_type=='Audio' for t in info.tracks)
                row.update(width=getattr(visual,'width',None),height=getattr(visual,'height',None),
                           has_audio=audio,probe_status='ok',probe_provider='pymediainfo')
                timed=next((t for t in info.tracks if t.track_type in ['Video','Audio']),None)
                duration=getattr(timed,'duration',None)
                if duration is not None:row['duration_us']=round(float(duration)*1000)
                row['rotation']=int(float(getattr(visual,'rotation',0) or 0))
                sar=Fraction(str(getattr(visual,'pixel_aspect_ratio',1) or 1))
                row['sample_aspect_ratio']=f'{sar.numerator}:{sar.denominator}'
            except (ValueError,OSError,RuntimeError,OverflowError,ZeroDivisionError) as e:
                row.update(probe_status='error',probe_error=str(e))
        elif ffprobe:
            try:
                data=json.loads(run([ffprobe,'-v','error','-show_format','-show_streams','-of','json',p]))
                streams=data.get('streams',[])
                v=next((s for s in streams if s.get('codec_type')=='video'),{})
                row.update(width=v.get('width'),height=v.get('height'),
                           has_audio=any(s.get('codec_type')=='audio' for s in streams),probe_status='ok')
                duration=data.get('format',{}).get('duration') or v.get('duration')
                if duration is not None:row['duration_us']=round(float(duration)*1000000)
                rotation=next((x.get('rotation') for x in v.get('side_data_list',[]) if 'rotation' in x),0)
                row['rotation']=int(rotation or v.get('tags',{}).get('rotate',0))
                row['sample_aspect_ratio']=v.get('sample_aspect_ratio','1:1')
            except (ValueError, OSError) as e:
                row.update(probe_status='error',probe_error=str(e))
        rows.append(row)
    return rows

def integer(v,minimum=0):return type(v) is int and v>=minimum
def finite(v):return type(v) in (int,float) and math.isfinite(v)

def validate_plan(plan, root):
    errors=[];warnings=[];root=Path(root).resolve()
    def error(s):errors.append(s)
    def keys(obj,allowed,label):
        if not isinstance(obj,dict):error(label+' 必须是对象');return False
        extra=set(obj)-set(allowed)
        if extra:error(label+' 不支持字段: '+', '.join(sorted(extra)))
        return True
    if not keys(plan,['schema_version','project','media','clips','titles','audio','notes'],'plan'):
        return dict(errors=errors,warnings=warnings)
    if plan.get('schema_version')!=1:error('schema_version 必须为 1')
    project=plan.get('project',{})
    if not keys(project,['name','scene','width','height','fps','audience','goal','platform'],'project'):
        return dict(errors=errors,warnings=warnings)
    name=project.get('name')
    if not isinstance(name,str) or not name.strip():error('项目 name 不能为空')
    if not isinstance(project.get('scene'),str) or project['scene'] not in profiles():error('未知 scene')
    for field in ['width','height']:
        if not integer(project.get(field),2) or project[field]%2 or project[field]>8192:
            error(field+' 必须是 2–8192 内的偶数整数')
    try:fps=fps_value(project['fps'])
    except (KeyError,ValueError,ZeroDivisionError,TypeError):
        error('fps 格式无效');fps=Fraction(30)
    media={}
    if not isinstance(plan.get('media'),list):error('media 必须为数组')
    for m in plan.get('media',[]) if isinstance(plan.get('media'),list) else []:
        if not keys(m,['id','path','kind','duration_us','width','height','has_audio','size_bytes','mtime_ns',
                       'probe_status','probe_provider','probe_error','rotation','sample_aspect_ratio','source_date','credit','rights'],'media'):continue
        mid=m.get('id')
        if not isinstance(mid,str) or not mid or mid in media:error('素材 ID 缺失或重复');continue
        media[mid]=m
        try:
            path=media_path(root,m.get('path'))
            st=path.stat()
            if m.get('size_bytes',st.st_size)!=st.st_size or m.get('mtime_ns',st.st_mtime_ns)!=st.st_mtime_ns:
                error(mid+' 素材已经改变，请重新盘点并复核源区间')
        except (ValueError,OSError) as e:error(mid+' '+str(e))
        if m.get('kind') not in ['video','image','audio']:error(mid+' 素材类型无效')
    clips=plan.get('clips',[])
    if not isinstance(clips,list) or not clips:error('clips 必须是非空数组');clips=[]
    end=0;ids=set()
    def timing(c,label,allowed):
        if not keys(c,allowed,label):return False
        good=True
        for field,minimum in [('start_frame',0),('duration_frames',1)]:
            if not integer(c.get(field),minimum):error(label+' '+field+' 必须为整数帧');good=False
        return good
    def source(c,label,kinds):
        mid=c.get('media_id')
        m=media.get(mid) if isinstance(mid,str) else None
        if not m:error(label+' 素材 ID 未找到');return None
        if m.get('kind') not in kinds:error(label+' 素材类型不匹配')
        if not integer(c.get('in_frame',0)):error(label+' in_frame 必须为非负整数帧');return m
        if m.get('kind')!='image':
            duration=m.get('duration_us')
            if not integer(duration,1):error(label+' 未知源时长，先使用 ffprobe 重新盘点')
            elif frame_us(c.get('in_frame',0)+c['duration_frames'],fps)>duration:
                error(label+' 区间超过源时长')
        elif c.get('in_frame',0)!=0:error(label+' 静态图片 in_frame 必须为 0')
        if not finite(c.get('volume',1)) or not 0<=c.get('volume',1)<=2:error(label+' volume 应在 0–2 之间')
        return m
    for n,c in enumerate(clips):
        label=f'clips[{n}]'
        if not timing(c,label,['id','media_id','start_frame','in_frame','duration_frames','fit','volume','purpose','caption_note']):continue
        cid=c.get('id')
        if not isinstance(cid,str) or not cid or cid in ids:error('镜头 ID 缺失或重复')
        if isinstance(cid,str):ids.add(cid)
        if c['start_frame']!=end:error(label+' 主画面必须按顺序连续，不允许空隙或重叠')
        end=c['start_frame']+c['duration_frames']
        m=source(c,label,['video','image'])
        if c.get('fit') not in ['contain','cover']:error(label+' fit 必须为 contain 或 cover')
        if m:
            if not integer(m.get('width'),1) or not integer(m.get('height'),1):error(label+' 缺少画面尺寸')
            if m.get('kind')=='video' and type(m.get('has_audio')) is not bool:error(label+' 未知原声状态')
            rotation=m.get('rotation',0)
            if type(rotation) is not int or rotation%360:error(label+' 旋转元数据须先生成正确方向代理并重新盘点')
            if m.get('sample_aspect_ratio','1:1') not in ['1:1','0:1','N/A']:error(label+' 非方形像素须先规范代理')
            if c.get('fit')=='cover':warnings.append(label+' 居中裁切需人工确认主体；焦点重构请预合成')
    for group in ['titles','audio']:
        entries=plan.get(group,[])
        if not isinstance(entries,list):error(group+' 必须为数组');continue
        for n,c in enumerate(entries):
            label=f'{group}[{n}]'
            allowed=['text','start_frame','duration_frames'] if group=='titles' else ['media_id','start_frame','in_frame','duration_frames','volume','role']
            if not timing(c,label,allowed):continue
            if c['start_frame']+c['duration_frames']>end:error(label+' 超过成片范围')
            if group=='titles':
                if not isinstance(c.get('text'),str) or not c['text'].strip():error(label+' text 不能为空')
            else:
                source(c,label,['audio'])
                if c.get('role') not in ['music','dialogue','ambient','effect']:error(label+' 未知音轨 role')
    if project.get('scene')=='interview' and any(c.get('volume',1)==0 for c in clips if isinstance(c,dict)):
        warnings.append('访谈存在静音镜头，确认对白另有独立音轨且语义连续')
    if any(c.get('role')=='music' for c in (plan.get('audio') or []) if isinstance(c,dict)):
        warnings.append('检查配乐版本、实际听感、对白遮蔽和使用范围；工具不自动证明音乐许可')
    return dict(errors=errors,warnings=warnings,total_frames=end,duration_us=frame_us(end,fps))

def checked(plan,root):
    report=validate_plan(plan,root)
    if report['errors']:raise ValueError('\n'.join(report['errors']))
    return report

def frame_range(c,fps):
    start=frame_us(c['start_frame'],fps)
    return start,frame_us(c['start_frame']+c['duration_frames'],fps)-start

def native_draft(plan, root, output):
    checked(plan,root)
    if platform.system()!='Windows':raise ValueError('此草稿适配器仅有 Windows 验证；Mac 请用剪映手工或单独验证上游 MCP')
    p=plan['project'];fps=p['fps']
    if fps_value(fps).denominator!=1:raise ValueError('原生草稿适配器暂只支持整数 fps；预览与计划支持分数 fps')
    import pyJianYingDraft as d
    if importlib.metadata.version('pyJianYingDraft')!='0.3.0':raise ValueError('草稿适配器当前锁定 pyJianYingDraft==0.3.0')
    output=Path(output).resolve()
    if output.exists():raise FileExistsError(str(output))
    output.mkdir(parents=True)
    s=d.DraftFolder(str(output)).create_draft('editkit-draft',p['width'],p['height'],int(fps_value(fps)))
    s.append_track(d.TrackSpec(d.TrackType.video,'画面'))
    s.append_track(d.TrackSpec(d.TrackType.text,'标题'))
    media={m['id']:m for m in plan['media']}
    for c in plan['clips']:
        m=media[c['media_id']];start,dur=frame_range(c,fps)
        material=d.VideoMaterial(str(media_path(root,m['path'])))
        ratio=max(m['width']/p['width'],m['height']/p['height'])/min(m['width']/p['width'],m['height']/p['height'])
        scale=ratio if c['fit']=='cover' else 1
        kwargs=dict(volume=c.get('volume',1),clip_settings=d.ClipSettings(scale_x=scale,scale_y=scale))
        if m['kind']=='video':kwargs['source_timerange']=d.trange(frame_us(c.get('in_frame',0),fps),dur)
        seg=d.VideoSegment(material,d.trange(start,dur),**kwargs)
        s.add_segment(seg,'画面')
    for n,c in enumerate(plan.get('titles',[])):
        start,dur=frame_range(c,fps)
        # One native track per cue also permits deliberate overlapping labels.
        name=f'标题{n}';s.append_track(d.TrackSpec(d.TrackType.text,name))
        s.add_segment(d.TextSegment(c['text'],d.trange(start,dur),style=d.TextStyle(size=8,align=1),
                      clip_settings=d.ClipSettings(transform_y=-.75)),name)
    for n,c in enumerate(plan.get('audio',[])):
        name=f'{c["role"]}{n}';s.append_track(d.TrackSpec(d.TrackType.audio,name))
        start,dur=frame_range(c,fps);m=media[c['media_id']]
        s.add_segment(d.AudioSegment(str(media_path(root,m['path'])),d.trange(start,dur),
                      source_timerange=d.trange(frame_us(c.get('in_frame',0),fps),dur),volume=c.get('volume',1)),name)
    s.save()
    write_new(output/'editkit-plan.json',plan)
    write_new(output/'status.json',dict(draft_generated=True,native_opened=False,native_exported=False,
                                       audio_listened=False,media='absolute references; retain originals'))
    return output/'editkit-draft'

def render_preview(plan,root,output,ffmpeg):
    report=checked(plan,root)
    output=Path(output).resolve()
    if output.exists():raise FileExistsError(str(output))
    output.parent.mkdir(parents=True,exist_ok=True)
    p=plan['project'];fps=p['fps'];w=p['width'];h=p['height']
    media={m['id']:m for m in plan['media']}
    with tempfile.TemporaryDirectory(prefix='editkit-') as temp:
        tmp=Path(temp)
        parts=[]
        for n,c in enumerate(plan['clips']):
            m=media[c['media_id']];duration=frame_us(c['duration_frames'],fps)/1e6
            cmd=[ffmpeg,'-v','error','-nostdin','-n']
            if m['kind']=='image':cmd+=['-loop','1','-framerate',str(fps)]
            else:cmd+=['-ss',str(frame_us(c.get('in_frame',0),fps)/1e6)]
            cmd+=['-i',str(media_path(root,m['path']))]
            has_audio=m['kind']=='video' and m.get('has_audio')
            if not has_audio:cmd+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
            if c['fit']=='contain':vf=f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black'
            else:vf=f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
            part=tmp/f'part{n}.mp4';parts.append(part.name)
            cmd+=['-map','0:v:0','-map','0:a:0' if has_audio else '1:a:0',
                  '-vf',vf+',setsar=1','-af',f'volume={c.get("volume",1)},apad',
                  '-t',str(duration),'-r',str(fps),'-frames:v',str(c['duration_frames']),
                  '-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2',str(part)]
            run(cmd)
        (tmp/'concat.txt').write_text(''.join(f"file '{s}'\n" for s in parts),encoding='utf-8')
        # Re-encode concat to normalize audio timestamps; no shortest truncation.
        run([ffmpeg,'-v','error','-nostdin','-n','-f','concat','-safe','0','-i','concat.txt',
             '-c:v','libx264','-preset','fast','-c:a','aac','base.mp4'],cwd=tmp)
        filters=[]
        if plan.get('titles'):
            header='[Script Info]\nScriptType: v4.00+\nPlayResX: '+str(w)+'\nPlayResY: '+str(h)+'\n[V4+ Styles]\n'
            header+='Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV\n'
            header+=f'Style: Default,Arial,{round(h*.038)},&H00FFFFFF,&H00000000,1,2,0,2,{round(w*.06)},{round(w*.06)},{round(h*.08)}\n'
            header+='[Events]\nFormat: Layer,Start,End,Style,Text\n'
            def stamp(fr):
                cs=round(frame_us(fr,fps)/10000);return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'
            for c in plan['titles']:
                text=c['text'].replace('\\','\\\\').replace('{','\\{').replace('}','\\}').replace('\n',r'\N')
                header+=f'Dialogue: 0,{stamp(c["start_frame"])},{stamp(c["start_frame"]+c["duration_frames"])},Default,{text}\n'
            (tmp/'titles.ass').write_text(header,encoding='utf-8')
            filters=['-vf','subtitles=titles.ass']
        cmd=[ffmpeg,'-v','error','-nostdin','-n','-i','base.mp4']
        mix=['[0:a]apad[a0]'];labels=['[a0]']
        for n,c in enumerate(plan.get('audio',[]),1):
            m=media[c['media_id']];dur=frame_us(c['duration_frames'],fps)/1e6
            cmd+=['-ss',str(frame_us(c.get('in_frame',0),fps)/1e6),'-t',str(dur),'-i',str(media_path(root,m['path']))]
            delay=round(frame_us(c['start_frame'],fps)/1000)
            mix.append(f'[{n}:a]aresample=48000,volume={c.get("volume",1)},adelay={delay}:all=1,apad[a{n}]')
            labels.append(f'[a{n}]')
        mix.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=longest:normalize=0[amix]')
        cmd+=['-filter_complex',';'.join(mix),'-map','0:v:0','-map','[amix]',*filters,
              '-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac',
              '-frames:v',str(report['total_frames']),'-t',str(report['duration_us']/1e6),'-movflags','+faststart','preview.mp4']
        run(cmd,cwd=tmp)
        # Reserve destination without replacing an existing file, even after a long render.
        with (tmp/'preview.mp4').open('rb') as src,output.open('xb') as dst:shutil.copyfileobj(src,dst)
    return dict(output=str(output),kind='FFmpeg program preview; not Jianying native export',
                total_frames=report['total_frames'],audio_listened=False)

def review_html(plan,root):
    result=validate_plan(plan,root);p=plan['project'];esc=lambda x:html.escape(str(x))
    rows=''.join('<tr>'+''.join('<td>'+esc(c.get(k,''))+'</td>' for k in
         ['id','media_id','start_frame','in_frame','duration_frames','fit','purpose'])+'</tr>' for c in plan.get('clips',[]))
    checks=['叙事与目标一致','主体与文字未裁断','对白语义连续','技术或操作顺序真实','音乐实际试听','标题位置与安全区','工程保存重开','剪映原生导出','发布使用范围']
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>剪辑审片单</title><style>body{font:17px/1.8 system-ui;margin:30px auto;padding:0 20px;max-width:960px;color:#203129;background:#f5f3ed}table{border-collapse:collapse;min-width:650px}td,th{border-bottom:1px solid #b9c6bd;padding:10px;text-align:left}.scroll{overflow:auto}pre{white-space:pre-wrap}label{display:block;padding:8px}input{margin-right:12px}</style><h1>'+esc(p['name'])+'</h1><p>这是审片记录，不代表下列事项已经通过。勾选仅在本页面暂存，不自动保存。</p><div class="scroll"><table><tr>'+''.join('<th>'+s+'</th>' for s in ['镜头','素材','开始帧','源入帧','时长帧','布局','用途'])+'</tr>'+rows+'</table></div><h2>人工审片</h2>'+''.join('<label><input type="checkbox">'+s+'</label>' for s in checks)+'<h2>机器校验</h2><pre>'+esc(json.dumps(result,ensure_ascii=False,indent=2))+'</pre></html>'

def main(argv=None):
    parser=argparse.ArgumentParser(description='Codex × 剪映通用本地工具包 v0.1.1')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('profiles');sub.add_parser('doctor')
    s=sub.add_parser('init');s.add_argument('--scene',choices=list(profiles()),required=True);s.add_argument('--out',required=True)
    s.add_argument('--name',required=True);s.add_argument('--width',type=int,required=True);s.add_argument('--height',type=int,required=True);s.add_argument('--fps',required=True)
    s=sub.add_parser('inventory');s.add_argument('--media-root',required=True);s.add_argument('--out',required=True);s.add_argument('--ffprobe',default=shutil.which('ffprobe'))
    s.add_argument('--mediainfo',action='store_true',help='显式使用已安装的 pymediainfo 代替 ffprobe')
    for name in ['validate','review','draft','preview']:
        s=sub.add_parser(name);s.add_argument('plan');s.add_argument('--media-root',required=True)
        if name!='validate':s.add_argument('--out',required=True)
        if name=='preview':s.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    args=parser.parse_args(argv)
    try:
        if args.command=='profiles':result=profiles()
        elif args.command=='doctor':
            result=dict(python=sys.version.split()[0],executable=sys.executable,platform=platform.system(),
                        ffmpeg=shutil.which('ffmpeg'),ffprobe=shutil.which('ffprobe'),
                        native_app_control='not included; use available authorized native tools',
                        native_export='manual Jianying UI; no automatic export backend')
            try:result['pyJianYingDraft']=importlib.metadata.version('pyJianYingDraft')
            except importlib.metadata.PackageNotFoundError:result['pyJianYingDraft']=None
        elif args.command=='init':
            fps_value(args.fps)
            if args.width<2 or args.height<2 or args.width%2 or args.height%2 or max(args.width,args.height)>8192:raise ValueError('画幅必须为 2–8192 的偶数尺寸')
            root=Path(args.out)
            root.mkdir(parents=True,exist_ok=False)
            plan=dict(schema_version=1,project=dict(name=args.name,scene=args.scene,width=args.width,height=args.height,fps=args.fps),media=[],clips=[],titles=[],audio=[])
            write_new(root/'plan.json',plan);write_new(root/'scene.json',profiles()[args.scene])
            write_new(root/'brief.md',(ASSETS/'brief.md').read_text(encoding='utf-8'))
            result=dict(project=str(root),status='needs source inventory, inspection and clip selection; not a completed edit')
        elif args.command=='inventory':
            result=inventory(Path(args.media_root),args.ffprobe,mediainfo=args.mediainfo);write_new(args.out,result)
        else:
            plan=load(args.plan);root=Path(args.media_root).resolve()
            if args.command=='validate':result=validate_plan(plan,root)
            elif args.command=='review':write_new(args.out,review_html(plan,root));result={'review':args.out}
            elif args.command=='draft':result={'draft':str(native_draft(plan,root,args.out)),'native_opened':False,'native_exported':False}
            else:
                if not args.ffmpeg:raise ValueError('未找到 FFmpeg；请通过 --ffmpeg 指定，不自动下载安装')
                result=render_preview(plan,root,args.out,args.ffmpeg)
        print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))
        return 1 if isinstance(result,dict) and result.get('errors') else 0
    except (ValueError,KeyError,TypeError,OSError,ImportError) as e:
        print(json.dumps({'error':str(e)},ensure_ascii=False),file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
