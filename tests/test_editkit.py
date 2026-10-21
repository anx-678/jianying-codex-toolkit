import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'skills/jianying-codex-toolkit/scripts/editkit.py'
if SCRIPT.exists():
    spec=importlib.util.spec_from_file_location('editkit', SCRIPT)
    kit=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kit)
else:
    kit=None

class PlanTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(kit, '缺少可执行工具核心')
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'clip.mp4').write_bytes(b'test fixture; metadata supplied by test')
        self.plan={'schema_version':1,'project':{'name':'访谈样片','scene':'interview',
                   'width':1920,'height':1080,'fps':'30000/1001'},
                   'media':[{'id':'V1','path':'clip.mp4','kind':'video','duration_us':10000000,
                             'width':1920,'height':1080,'has_audio':True}],
                   'clips':[{'id':'C1','media_id':'V1','start_frame':0,'in_frame':0,
                             'duration_frames':60,'fit':'contain','volume':1}],
                   'titles':[],'audio':[]}

    def check(self, plan=None):
        return kit.validate_plan(plan or self.plan, self.root)

    def test_valid_interview_keeps_sound(self):
        self.assertEqual(self.check()['errors'],[])
        self.assertEqual(self.plan['clips'][0]['volume'],1)

    def test_source_overrun_rejected(self):
        self.plan['clips'][0]['in_frame']=290
        self.assertTrue(any('源时长' in x for x in self.check()['errors']))

    def test_gap_and_overlap_rejected(self):
        for start in [59,61]:
            p=copy.deepcopy(self.plan)
            p['clips'].append(dict(p['clips'][0],id='C2',start_frame=start))
            self.assertTrue(any('连续' in x for x in self.check(p)['errors']))

    def test_path_escape_rejected(self):
        self.plan['media'][0]['path']='../outside.mp4'
        self.assertTrue(any('根目录' in x for x in self.check()['errors']))

    def test_absolute_path_rejected(self):
        self.plan['media'][0]['path']=str(self.root/'clip.mp4')
        self.assertTrue(any('相对路径' in x for x in self.check()['errors']))

    def test_unknown_effect_not_silently_dropped(self):
        self.plan['clips'][0]['transition']='dissolve'
        self.assertTrue(any('不支持字段' in x for x in self.check()['errors']))

    def test_bool_nan_negative_dimensions_and_duplicate_ids_rejected(self):
        for key,value in [('width',True),('width',-1),('fps','nan')]:
            p=copy.deepcopy(self.plan);p['project'][key]=value
            self.assertTrue(self.check(p)['errors'])
        self.plan['media'].append(self.plan['media'][0].copy())
        self.assertTrue(self.check()['errors'])

    def test_title_and_music_bounds(self):
        self.plan['titles']=[{'text':'越界','start_frame':50,'duration_frames':20}]
        self.assertTrue(any('成片范围' in x for x in self.check()['errors']))

    def test_frame_boundaries_do_not_accumulate_rounding(self):
        durations=[kit.frame_us(n+1,'30000/1001')-kit.frame_us(n,'30000/1001') for n in range(10000)]
        self.assertEqual(sum(durations),kit.frame_us(10000,'30000/1001'))

    def test_missing_and_stale_metadata_not_accepted(self):
        self.plan['media'][0]['duration_us']=None
        self.assertTrue(self.check()['errors'])
        self.plan['media'][0]['duration_us']=10000000
        self.plan['media'][0]['size_bytes']=99999
        self.assertTrue(any('改变' in x for x in self.check()['errors']))

    def test_all_scenes_have_distinct_policies_no_locked_duration(self):
        scenes=kit.profiles()
        self.assertEqual(set(scenes),{'event','product','tutorial','interview','brand','montage'})
        self.assertIn('对白',scenes['interview']['audio'])
        self.assertIn('顺序',scenes['tutorial']['continuity'])
        self.assertNotIn('duration_frames',scenes['event'])

    def test_new_file_never_overwrites(self):
        p=self.root/'existing.json';p.write_text('original')
        with self.assertRaises(FileExistsError):kit.write_new(p, {'test':1})
        self.assertEqual(p.read_text(),'original')

    def test_inventory_readonly_and_relative(self):
        rows=kit.inventory(self.root, None)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['path'],'clip.mp4')
        self.assertIsNone(rows[0]['duration_us'])
        self.assertEqual((self.root/'clip.mp4').read_bytes(),b'test fixture; metadata supplied by test')

    def test_malformed_groups_report_errors_instead_of_crashing(self):
        for field in ['media','clips','audio','titles']:
            p=copy.deepcopy(self.plan);p[field]=None
            self.assertTrue(self.check(p)['errors'])

    def test_native_rejects_fractional_rate_without_creating_output(self):
        if kit.platform.system()!='Windows':self.skipTest('Windows adapter')
        output=self.root/'draft-output'
        try:
            with self.assertRaises(ValueError):kit.native_draft(self.plan,self.root,output)
        except ImportError:self.skipTest('optional draft dependency absent')
        self.assertFalse(output.exists())

    def test_nested_wrong_types_are_validation_errors(self):
        for group,index,key,value in [('clips',0,'id',[]),('clips',0,'media_id',{}),
                                      ('media',0,'rotation','90'),('project',None,'scene',[])]:
            p=copy.deepcopy(self.plan)
            (p[group] if index is None else p[group][index])[key]=value
            self.assertTrue(self.check(p)['errors'])

    def test_probe_result_parsing_and_error_preserve_original(self):
        from unittest.mock import patch
        data={'streams':[{'codec_type':'video','width':1920,'height':1080,'side_data_list':[{'rotation':90}]},
                         {'codec_type':'audio'}],'format':{'duration':'5.25'}}
        with patch.object(kit,'run',return_value=json.dumps(data)):
            row=kit.inventory(self.root,'ffprobe')[0]
        self.assertEqual((row['duration_us'],row['rotation'],row['has_audio']),(5250000,90,True))
        with patch.object(kit,'run',side_effect=ValueError('corrupt media')):
            self.assertEqual(kit.inventory(self.root,'ffprobe')[0]['probe_status'],'error')

    def test_explicit_mediainfo_probe_can_reuse_optional_dependency(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        tracks=[SimpleNamespace(track_type='Video',width=1920,height=1080,duration='5250.0',rotation=None,pixel_aspect_ratio='1.0'),
                SimpleNamespace(track_type='Audio')]
        fake=SimpleNamespace(MediaInfo=SimpleNamespace(parse=lambda p:SimpleNamespace(tracks=tracks)))
        with patch.dict('sys.modules',{'pymediainfo':fake}):
            row=kit.inventory(self.root,None,mediainfo=True)[0]
        self.assertEqual((row['width'],row['duration_us'],row['has_audio']),(1920,5250000,True))

if __name__=='__main__':unittest.main()
