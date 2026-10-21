"""Explicit optional integration check. Requires generated demo, FFmpeg and draft extra on Windows."""
import argparse
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import platform
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('editkit',ROOT/'skills/jianying-codex-toolkit/scripts/editkit.py')
kit=importlib.util.module_from_spec(spec);spec.loader.exec_module(kit)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ffmpeg',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    from pymediainfo import MediaInfo
    reports=[]
    for scene in kit.profiles():
        plan=kit.load(ROOT/'demo-generated'/f'{scene}.json')
        report=kit.checked(plan,ROOT/'demo-generated')
        video=out/f'{scene}.mp4'
        kit.render_preview(plan,ROOT/'demo-generated',video,args.ffmpeg)
        kit.run([args.ffmpeg,'-v','error','-nostdin','-i',video,'-f','null','-'])
        info=MediaInfo.parse(str(video))
        track=next(t for t in info.tracks if t.track_type=='Video')
        assert int(track.frame_count)==90,(scene,track.frame_count)
        assert (track.width,track.height)==(plan['project']['width'],plan['project']['height'])
        draft=kit.native_draft(plan,ROOT/'demo-generated',out/f'{scene}-draft') if platform.system()=='Windows' else None
        if draft:
            native=kit.load(draft/'draft_content.json')
            assert native['duration']==3000000
            assert any(t['type']=='text' for t in native['tracks'])
            assert not any(s.get('volume',1)==0 for t in native['tracks'] if t['type']=='video' for s in t['segments'])
        kit.write_new(out/f'{scene}-review.html',kit.review_html(plan,ROOT/'demo-generated'))
        reports.append(dict(scene=scene,frames=int(track.frame_count),width=track.width,height=track.height,
                            full_decode=True,draft_generated=bool(draft),native_opened=False,native_exported=False))
    raw=subprocess.run([args.ffmpeg,'-v','error','-i',str(out/'interview.mp4'),'-map','0:a:0',
                        '-f','s16le','-ac','1','-ar','48000','-'],capture_output=True,check=True).stdout
    values=struct.unpack('<'+'h'*(len(raw)//2),raw)
    rms=lambda start,stop:(sum((v/32768)**2 for v in values[round(start*48000):round(stop*48000)])/round((stop-start)*48000))**.5
    voiced=rms(.2,.8);silence=rms(2.2,2.8)
    assert voiced>.02 and silence<.002,(voiced,silence)
    result=dict(date='2026-10-21',system=platform.system(),python=sys.version.split()[0],environment='project .venv, uv sync --extra draft',
                dependencies={n:importlib.metadata.version(n) for n in ['pyJianYingDraft','pymediainfo','Pillow','numpy']},
                core_unit_tests='see unittest command; counted separately',synthetic_scenes=reports,
                interview_signal_test=dict(voiced_rms=voiced,silent_rms=silence,meaning='test-tone preservation only; not human listening'),
                ffprobe_live='not run: executable absent; inventory without probe tested',
                not_verified=['Mac native app','Linux execution','Jianying native open/save/export of these new drafts',
                              'real footage aesthetics','human listening','HTML browser rendering','external CI'],
                no_customer_media=True)
    kit.write_new(out/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
