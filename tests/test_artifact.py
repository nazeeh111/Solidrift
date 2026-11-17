import copy,json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from solidrift.artifact import canonical,capture,check_artifact,from_report,geometry_hash,operands,publish_file,transform
from solidrift.io import InputError

ROOT=Path(__file__).resolve().parents[1]

class ArtifactTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();root=Path(cls.tmp.name);(root/'originals').mkdir()
  for i in (3,4):shutil.copyfile(ROOT/f'solidrift/fixtures/Offset{i}.obj',root/'originals'/('A.obj' if i==3 else 'B.obj'))
  shutil.copyfile(ROOT/'tests/fixtures/native-report.json',root/'report.json');cls.report=root/'report.json';cls.original=operands([root/'originals/A.obj',root/'originals/B.obj']);cls.artifact=from_report(cls.report)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_full_repair_and_undo_original_geometry(self):
  changed=transform(self.artifact,self.original);self.assertEqual([geometry_hash(x) for x in changed],self.artifact['after_geometry_sha256'])
  self.assertEqual([geometry_hash(x) for x in transform(self.artifact,changed,undo=True)],self.artifact['before_geometry_sha256'])
 def test_changed_coordinate_topology_and_duplicate_change_refused(self):
  for mutate in ('coordinate','topology'):
   pair=copy.deepcopy(self.original)
   if mutate=='coordinate':pair[0]['vertices'][0][0]+=1
   else:pair[0]['faces'][0]=pair[0]['faces'][0][::-1]
   with self.subTest(mutate=mutate),self.assertRaises(InputError):transform(self.artifact,pair)
  artifact=copy.deepcopy(self.artifact);artifact['changes'].append(copy.deepcopy(artifact['changes'][0]))
  with self.assertRaises(InputError):transform(artifact,self.original)
 def test_report_and_artifact_tamper_refused(self):
  root=Path(self.tmp.name);p=root/'artifact.json';p.write_bytes(canonical(self.artifact));self.assertEqual(check_artifact(self.report,p),self.artifact)
  changed=copy.deepcopy(self.artifact);changed['side']=not bool(changed['side']);p.write_bytes(canonical(changed))
  with self.assertRaises(InputError):check_artifact(self.report,p)
  p.write_bytes(canonical(self.artifact));r=json.loads(self.report.read_bytes());r['repair']['accepted']['patch'][0]['after'][0]+=1;other=root/'changed-report.json';other.write_text(json.dumps(r))
  with self.assertRaises(InputError):check_artifact(other,p)
 def test_capture_regular_descriptor_bounds_and_symlink_policy(self):
  root=Path(self.tmp.name);fifo=root/'fifo';os.mkfifo(fifo)
  with self.assertRaisesRegex(InputError,'regular file'):capture(fifo)
  large=root/'large';large.write_bytes(b'12345')
  with self.assertRaisesRegex(InputError,'bounded size'):capture(large,4)
  link=root/'link';link.symlink_to(large);self.assertEqual(capture(link,5),b'12345')
  large.write_bytes(b'1234')
  with patch('solidrift.artifact.os.read',side_effect=[b'1234',b'5']):
   with self.assertRaisesRegex(InputError,'bounded size'):capture(large,4)
  close=os.close
  with patch('solidrift.artifact.os.close',wraps=close) as closed:
   with self.assertRaises(InputError):capture(fifo)
  self.assertEqual(closed.call_count,1)
 def test_output_no_clobber_failure_retry(self):
  root=Path(self.tmp.name);existing=root/'existing';existing.write_bytes(b'keep')
  with self.assertRaises(FileExistsError):publish_file(existing,b'new')
  self.assertEqual(existing.read_bytes(),b'keep');new=root/'new'
  with patch('solidrift.artifact.os.fsync',side_effect=OSError('injected write fault')):
   with self.assertRaises(OSError):publish_file(new,b'data')
  self.assertFalse(new.exists());self.assertFalse(list(root.glob('.new.*.pending')))
  publish_file(new,b'data');self.assertEqual(new.read_bytes(),b'data')
  committed=root/'committed'
  with patch('solidrift.artifact.os.unlink',side_effect=PermissionError('synthetic cleanup denial')):
   publish_file(committed,b'complete')
  self.assertEqual(committed.read_bytes(),b'complete')
