from __future__ import annotations
import importlib.util, json, tempfile, unittest, argparse, hashlib, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
BOOT=module(ROOT/'skills/siege-zeke-bootstrap/scripts/siege_zeke_bootstrap.py','boot')
SYNC=module(ROOT/'skills/siege-zeke-drive-sync/scripts/siege_zeke_sync.py','sync')

class GatewayTests(unittest.TestCase):
    def test_producer_is_simple_and_non_secret(self): self.assertEqual(BOOT.PRODUCER,{"producer":"WKZ"})
    def test_redaction(self):
        text=BOOT.redact('token=abc secret=def password=ghi authorization=jkl')
        self.assertNotIn('abc',text); self.assertEqual(text.count('<redacted>'),4)
    def test_three_way_decisions(self):
        self.assertEqual(SYNC.decision('b','a','a'),'push')
        self.assertEqual(SYNC.decision('a','b','a'),'pull')
        self.assertEqual(SYNC.decision('b','c','a'),'SYNC-409')
        self.assertEqual(SYNC.decision('a','a','a'),'equal')
    def test_common_files_are_valid_json(self):
        paths=[ROOT/'GLOBAL.json',ROOT/'producer.json',ROOT/'projects/TXT-ANALYZE/PROJECT.json',
          ROOT/'projects/TXT-ANALYZE/CANONICAL-MAP.json',ROOT/'projects/TXT-ANALYZE/REQUIRED-DATA.json']
        for path in paths: self.assertIsInstance(json.loads(path.read_text(encoding='utf-8')),dict)
    def test_portable_data_hashes_match_manifest(self):
        manifest=json.loads((ROOT/'projects/TXT-ANALYZE/REQUIRED-DATA.json').read_text(encoding='utf-8'))
        for item in manifest['items']:
            source=ROOT/'projects/TXT-ANALYZE'/item['stage_path']
            self.assertTrue(source.is_file()); self.assertEqual(BOOT.sha(source),item['sha256'])
    def test_rulebook_copy_matches_registered_source(self):
        source=json.loads((ROOT/'rulebook/SOURCE.json').read_text(encoding='utf-8'))
        self.assertEqual(BOOT.sha(ROOT/'rulebook'/source['managed_file']),source['managed_sha256'])
        self.assertEqual(BOOT.sha(Path(source['source_path'])),source['source_sha256'])
    def test_secrets_are_not_packaged(self):
        forbidden={'token.json','credentials.json'}
        self.assertFalse(any(p.name.lower() in forbidden for p in ROOT.rglob('*') if p.is_file()))
    def test_canonical_rows_have_access_contract(self):
        data=json.loads((ROOT/'projects/TXT-ANALYZE/CANONICAL-MAP.json').read_text(encoding='utf-8'))
        for row in data['artifacts']:
            for key in ('drive_parent_id','mime_type','producer','permitted_operations','required_validation'): self.assertIn(key,row)
    def test_bootstrap_rejects_unregistered_same_id_project(self):
        with tempfile.TemporaryDirectory() as td:
            fake=Path(td); (fake/'PROJECT.json').write_text(json.dumps({'project_id':'TXT-ANALYZE'})); (fake/'REQUIRED-DATA.json').write_text('{"items":[]}'); (fake/'CHILDREN.json').write_text('{"children":[{"work_id":"FAKE"}]}'); (fake/'children').mkdir(); child=fake/'children/FAKE.json'; child.write_text(json.dumps({'work_id':'FAKE','parent_project_id':'TXT-ANALYZE','producer':'WKZ','state':'running','allowed_paths':[]}))
            a=argparse.Namespace(workspace=str(fake),project=str(fake),project_id='TXT-ANALYZE',credential_locator=str(fake/'token'),child=str(child),apply=False,stage=None)
            self.assertFalse(BOOT.inspect(a)['ok'])
    def test_sync_accepts_real_core_run_stage_and_resolves_authority(self):
        script=ROOT/'skills/siege-zeke-drive-sync/scripts/siege_zeke_sync.py'; stage=ROOT.parents[1]/'work/runs/TC-20260814-006/sync-test-stage'; stage.mkdir(parents=True,exist_ok=True)
        cmd=[sys.executable,str(script),'compare','--workspace',r'D:\projects\txt-analyze','--map',str(ROOT/'projects/TXT-ANALYZE/CANONICAL-MAP.json'),'--stage',str(stage),'--project',str(ROOT/'projects/TXT-ANALYZE'),'--child',str(ROOT/'projects/TXT-ANALYZE/children/TA-20260813-001.json')]
        run=subprocess.run(cmd,capture_output=True,text=True); self.assertNotIn('F225',run.stderr+run.stdout); self.assertNotIn('F224',run.stderr+run.stdout)
    def test_bootstrap_has_no_caller_supplied_global_config(self):
        text=(ROOT/'skills/siege-zeke-bootstrap/scripts/siege_zeke_bootstrap.py').read_text(encoding='utf-8')
        self.assertNotIn('add_argument("--global-config"',text)
    def test_sync_has_no_caller_supplied_global_config(self):
        text=(ROOT/'skills/siege-zeke-drive-sync/scripts/siege_zeke_sync.py').read_text(encoding='utf-8')
        self.assertNotIn('add_argument("--global-config"',text)

if __name__=='__main__': unittest.main()
