"""Generate owned synthetic media and six sample plans; no customer assets."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('editkit',ROOT/'skills/jianying-codex-toolkit/scripts/editkit.py')
kit=importlib.util.module_from_spec(spec);spec.loader.exec_module(kit)

def main():
    p=argparse.ArgumentParser();p.add_argument('--ffmpeg',required=True);p.add_argument('--out',required=True)
    args=p.parse_args();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    def render(name,args2):
        subprocess.run([args.ffmpeg,'-v','error','-nostdin','-n',*args2,str(out/name)],check=True)
    render('wide.mp4',['-f','lavfi','-i','testsrc2=size=640x360:rate=30:duration=6',
           '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=6','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest'])
    render('portrait.mp4',['-f','lavfi','-i','testsrc2=size=360x640:rate=30:duration=6',
           '-c:v','libx264','-pix_fmt','yuv420p','-an'])
    render('still.png',['-f','lavfi','-i','color=c=0x32594B:s=640x360','-frames:v','1'])
    render('tone.wav',['-f','lavfi','-i','sine=frequency=220:sample_rate=48000:duration=6'])
    media=[]
    for mid,name,kind,w,h,a in [('W','wide.mp4','video',640,360,True),('P','portrait.mp4','video',360,640,False),
                               ('I','still.png','image',640,360,False),('A','tone.wav','audio',None,None,True)]:
        st=(out/name).stat()
        media.append(dict(id=mid,path=name,kind=kind,width=w,height=h,has_audio=a,duration_us=6000000 if kind!='image' else None,
                          size_bytes=st.st_size,mtime_ns=st.st_mtime_ns,credit='FFmpeg synthetic test',rights='generated test signal'))
    shapes={'event':(360,640),'product':(640,360),'tutorial':(640,360),'interview':(640,360),'brand':(640,360),'montage':(360,640)}
    for scene,(w,h) in shapes.items():
        mids=['W','P','I'] if scene not in ['interview','tutorial'] else ['W','W','I']
        clips=[dict(id=f'C{n+1}',media_id=mid,start_frame=n*30,in_frame=0,duration_frames=30,
                    fit='contain' if n!=1 or scene in ['interview','tutorial'] else 'cover',volume=1,
                    purpose=['建立场景','连续动作或观点','收束'][n]) for n,mid in enumerate(mids)]
        audio=[] if scene in ['interview','tutorial'] else [dict(media_id='A',start_frame=0,in_frame=0,duration_frames=90,volume=.12,role='music')]
        plan=dict(schema_version=1,project=dict(name=f'合成测试-{scene}',scene=scene,width=w,height=h,fps='30'),
                  media=media,clips=clips,titles=[dict(text=f'Synthetic demo / {scene}',start_frame=0,duration_frames=90)],audio=audio,
                  notes='仅测试代码路径，正弦波不是正式配乐，测试图不是语义选片或真实对白验收')
        kit.write_new(out/f'{scene}.json',plan)
        # Shareable examples omit machine-specific mtimes; files are supplied by this generator.
        example=json.loads(json.dumps(plan))
        for m in example['media']:m.pop('mtime_ns',None);m.pop('size_bytes',None)
        dest=ROOT/'examples'/f'{scene}.json'
        if not dest.exists():kit.write_new(dest,example)
    print(out)

if __name__=='__main__':main()
