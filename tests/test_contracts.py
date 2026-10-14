import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from solidrift.io import InputError, parse_obj, load_report, MAX_REPORT_BYTES
from solidrift.gate import check_exact
from solidrift.surface import correspondence
from solidrift.engine import Budget, BudgetExhausted, displaced
from solidrift.cli import stop_process, view, run
from argparse import Namespace
from test_reducer import octahedron

TRI = b'v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n'

class Inputs(unittest.TestCase):
    def test_index_forms_and_metadata_are_data_only(self):
        data=b'mtllib ../../never-open-this\no test\n'+TRI.replace(b'f 1 2 3',b'vn 0 0 1\nvt 0 0\nf -3/1/1 -2/1/1 -1/1/1')
        mesh,_=parse_obj(data)
        self.assertEqual(mesh['faces'],[[0,1,2]])
    def test_nonfinite_overflow_and_unsupported_records_refused(self):
        for data in [TRI.replace(b'v 0 0 0',b'v nan 0 0'),TRI.replace(b'v 0 0 0',b'v 1e309 0 0'),
                     TRI+b'curv 0 1 1 2 3\n',TRI.replace(b'f 1 2 3',b'f 1 2 0'),
                     TRI.replace(b'f 1 2 3',b'f 1 2 3 1'),TRI.replace(b'f 1 2 3',b'f 1 1 2'),
                     TRI.replace(b'f 1 2 3',b'f 1// 2// 3//'),b'\xff',b'#'+b'x'*8193]:
            with self.subTest(data=data[:40]),self.assertRaises(InputError):parse_obj(data)
    def test_size_and_geometry_limits(self):
        for data in [b'#'+b'x'*(1024*1024),TRI+b'v 1 1 1\n'*254,TRI+b'f 1 2 3\n'*256]:
            with self.assertRaises(InputError):parse_obj(data)
    def test_explicit_binary32_conversion(self):
        _,m= parse_obj(TRI.replace(b'v 1 0 0',b'v 1.00000001 0 0'))
        self.assertEqual(m['changed_coordinate_count'],1)
        self.assertGreater(m['max_absolute_coordinate_delta'],0)
    def test_open_inverted_duplicate_and_unused_meshes_fail_guard(self):
        mesh=octahedron().geometry()
        self.assertTrue(check_exact(mesh['vertices'],mesh['faces'])['valid'])
        cases=[dict(mesh,faces=mesh['faces'][:-1]),dict(mesh,faces=[f[::-1] for f in mesh['faces']]),
               dict(mesh,faces=mesh['faces']+[mesh['faces'][0]]),dict(mesh,vertices=mesh['vertices']+[[20,20,20]])]
        for m in cases:self.assertFalse(check_exact(m['vertices'],m['faces'])['valid'])

class Acceptance(unittest.TestCase):
    def test_equal_volume_translated_reference_rejected(self):
        m=octahedron().geometry();n=copy.deepcopy(m)
        n['vertices']=[[x+10,y,z] for x,y,z in n['vertices']]
        c=correspondence(m,n,1e-6)
        self.assertFalse(c['bijection'] and c.get('within_tolerance'))
    def test_oriented_faces_required_and_pair_bound_upward(self):
        m=octahedron().geometry();n=copy.deepcopy(m)
        n['vertices']=[[x+1e-8,y,z] for x,y,z in n['vertices']]
        c=correspondence(m,n,1e-6)
        self.assertTrue(c['bijection'] and c['within_tolerance'])
        self.assertGreaterEqual(c['whole_paired_surface_distance_upper_bound'],1e-8)
        n['faces']=[f[::-1] for f in n['faces']]
        self.assertFalse(correspondence(m,n)['bijection'])
    def test_patch_before_values_restore_exact_original(self):
        original=octahedron().geometry();changed=displaced(original,[0,2],[0,.001,.002])
        before=copy.deepcopy(original)
        self.assertNotEqual(original['vertices'],changed['vertices'])
        for i in [0,2]:changed['vertices'][i]=list(original['vertices'][i])
        self.assertEqual(changed,before)
    def test_budget_counts_attempted_native_failure(self):
        budget=Budget(1,120)
        def backend(pair,solver):raise RuntimeError('real backend failure')
        with self.assertRaises(RuntimeError):budget.evaluate([], 'FLOAT',backend,'baseline')
        self.assertEqual(budget.queries,1)
        with self.assertRaises(BudgetExhausted):budget.evaluate([], 'FLOAT',backend,'baseline')
        self.assertEqual(budget.queries,1)
    def test_process_cancellation_terminates_and_reaps(self):
        p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True)
        stop_process(p)
        self.assertIsNotNone(p.poll())
    def test_standalone_report_escapes_script_closing_source_name(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.json';p.write_text(json.dumps({'schema_version':1,'status':'refused','sources':[{'name':'</script><img onerror=alert(1)>'}]}))
            target=Path(d)/'r.html'
            view(Namespace(report=p,out=target))
            html=target.read_text()
            self.assertNotIn('</script><img onerror',html)
            self.assertIn('\\u003c/script\\u003e',html)
            with self.assertRaises(InputError):view(Namespace(report=p,out=target))
    def test_analyze_never_clobbers_existing_output(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'output';out.mkdir();sentinel=out/'keep';sentinel.write_text('original')
            a=Path(d)/'a.obj';a.write_bytes(TRI)
            args=Namespace(command='analyze',a=a,b=a,out=out,blender=sys.executable,max_queries=16,max_seconds=120)
            with self.assertRaises(InputError):run(args)
            self.assertEqual(sentinel.read_text(),'original')
    def test_json_nan_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'r.json';p.write_text('{"schema_version":1,"n":NaN}')
            with self.assertRaises(InputError):load_report(p)

if __name__=='__main__':unittest.main()
