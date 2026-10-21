import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release',ROOT/'tools/package_release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'repo';self.root.mkdir()
        for path,content in {
          'pyproject.toml':'[project]\nname="jianying-codex-toolkit"\nversion="0.1.1"\n',
          'README.md':'# Test','LICENSE':'MIT fixture',
          'skills/jianying-codex-toolkit/SKILL.md':'---\nname: jianying-codex-toolkit\n---',
          'skills/jianying-codex-toolkit/scripts/editkit.py':'print("test")',
          'skills/jianying-codex-toolkit/agents/openai.yaml':'interface: {}',
          'skills/jianying-codex-toolkit/assets/scenes.json':'{}',
          '.venv/secret.txt':'do not package','outputs/private.txt':'do not package',
          'demo-generated/private.mp4':'do not package','docs/anx-day3-copy.md':'personal draft',
          'dist/old.zip':'do not recurse'}.items():
            p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf-8')

    def test_build_full_and_self_contained_skill(self):
        result=release.build(self.root,self.root/'dist')
        self.assertEqual(result['version'],'0.1.1')
        full=self.root/'dist/jianying-codex-toolkit-v0.1.1.zip'
        skill=self.root/'dist/jianying-codex-toolkit-skill-v0.1.1.zip'
        for path in [full,skill]:
            with zipfile.ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                self.assertTrue(any(n.endswith('/LICENSE') for n in z.namelist()))
                self.assertFalse(any('secret' in n or 'private' in n or 'old.zip' in n or 'anx-day3-copy' in n for n in z.namelist()))
        with zipfile.ZipFile(skill) as z:
            self.assertIn('jianying-codex-toolkit/SKILL.md',z.namelist())
            self.assertIn('jianying-codex-toolkit/scripts/editkit.py',z.namelist())
        self.assertTrue((self.root/'dist/SHA256SUMS.txt').is_file())
        manifest=json.loads((self.root/'dist/release-manifest.json').read_text())
        self.assertEqual(len(manifest['artifacts']),2)

    def test_repeat_does_not_overwrite(self):
        release.build(self.root,self.root/'dist')
        with self.assertRaises(FileExistsError):release.build(self.root,self.root/'dist')

    def test_private_paths_fail_closed_before_artifact_write(self):
        (self.root/'README.md').write_text('C:'+ '/'+'Users/example/private.txt')
        with self.assertRaises(ValueError):release.build(self.root,self.root/'dist')
        self.assertFalse((self.root/'dist/jianying-codex-toolkit-v0.1.1.zip').exists())

    def test_json_escaped_windows_and_posix_home_paths_rejected(self):
        paths=['C:'+chr(92)+'Users'+chr(92)+'example'+chr(92)+'private.txt','/'+'Users/example/private.txt','/'+'home/example/private.txt']
        for path in paths:
            (self.root/'README.md').write_text(json.dumps({'path':path}))
            with self.assertRaises(ValueError):release.build(self.root,self.root/'dist')

    def test_binary_and_credentials_rejected(self):
        for name,content in [('tools/payload.exe','binary'),('docs/token.txt','ghp_'+'x'*36)]:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
            with self.assertRaises(ValueError):release.build(self.root,self.root/'dist')
            p.unlink()

    def test_deterministic_zip_for_same_sources(self):
        release.build(self.root,self.root/'out1')
        release.build(self.root,self.root/'out2')
        for name in ['jianying-codex-toolkit-v0.1.1.zip','jianying-codex-toolkit-skill-v0.1.1.zip']:
            self.assertEqual((self.root/'out1'/name).read_bytes(),(self.root/'out2'/name).read_bytes())

if __name__=='__main__':unittest.main()
