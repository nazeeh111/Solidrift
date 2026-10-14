"""Synthetic stored-report controls, not native solver evidence."""
import copy,json,tempfile
from pathlib import Path
import unittest
from solidrift.io import read_input,write_obj,InputError
from solidrift.numeric import check
from solidrift.verify import verify,output_integral,bind_signature
from solidrift.reducer import failure_signature
from test_reducer import octahedron

class StoredIntegrals(unittest.TestCase):
    def test_authentic_recorded_case_verifies_with_schema1_mirrors(self):
        # Stored native evidence is a compatibility oracle; this runs no Blender.
        fixtures=Path(__file__).parent/'fixtures'
        sources=Path(__file__).parents[1]/'solidrift/fixtures'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'originals').mkdir()
            for target,name in [('A.obj','Offset3.obj'),('B.obj','Offset4.obj')]:
                (root/'originals'/target).write_bytes((sources/name).read_bytes())
            p=root/'report.json';p.write_bytes((fixtures/'native-report.json').read_bytes())
            self.assertEqual(verify(p)['replayed_steps'],60)

    def test_signature_mirrors_bind_fields_and_verdict(self):
        inputs=[{'volume':1.0},{'volume':2.0}];output={'volume':1.0}
        signature=failure_signature(inputs,output)
        self.assertTrue(bind_signature(signature,inputs,output)['matches'])
        for field,value in [('output_volume',999999999),('matches',False),('input_a_volume',2),('tolerance',10),('absolute_difference_from_a',10)]:
            bad=dict(signature);bad[field]=value
            with self.subTest(field=field),self.assertRaises(InputError):bind_signature(bad,inputs,output)

    def test_tiny_integral_has_no_absolute_tolerance_floor(self):
        mesh=octahedron().geometry();mesh['vertices']=[[x*1e-20,y*1e-20,z*1e-20] for x,y,z in mesh['vertices']]
        mesh['volume']=check(mesh['vertices'],mesh['faces'])['volume']
        self.assertAlmostEqual(output_integral(mesh)['volume']/mesh['volume'],1)
        mesh['volume']*=1.001
        with self.assertRaisesRegex(InputError,'volume|integral'):output_integral(mesh)

    def test_output_integral_rejects_malformed_nonfinite_and_wrong_index(self):
        mesh=octahedron().geometry();mesh['volume']=check(mesh['vertices'],mesh['faces'])['volume']
        for field in ('coordinates','scalar','index'):
            bad=copy.deepcopy(mesh)
            if field=='coordinates':bad['vertices'][0][0]=float('inf')
            if field=='scalar':bad['volume']=float('nan')
            if field=='index':bad['faces'][0][0]=len(bad['vertices'])
            with self.subTest(field=field),self.assertRaises(InputError):output_integral(bad)

    def test_changed_output_scalar_cannot_pass_geometry_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'originals').mkdir()
            a=octahedron().geometry();b=copy.deepcopy(a)
            b['vertices']=[[2*x,2*y,2*z] for x,y,z in b['vertices']]
            sources=[];inputs={}
            for name,mesh in [('A.obj',a),('B.obj',b)]:
                p=root/'originals'/name;write_obj(p,mesh)
                _,stored,source=read_input(p);source['stored_path']='originals/'+name
                sources.append(source);inputs[name]=stored
            # A is contained in B. A synthetic successful union is exactly B.
            output=copy.deepcopy(inputs['B.obj']);output['volume']=check(output['vertices'],output['faces'])['volume']
            report={'schema_version':1,'status':'no_failure','sources':sources,
                    'baseline':{'inputs':inputs,'outputs':{'FLOAT':output,'MANIFOLD':copy.deepcopy(output)},'failure_signature':failure_signature([check(m['vertices'],m['faces']) for m in inputs.values()],output)}}
            p=root/'report.json';p.write_text(json.dumps(report))
            self.assertTrue(verify(p)['valid'])
            # Keep the complete surface unchanged and corrupt only its scalar.
            report['baseline']['outputs']['FLOAT']['volume']+=1
            p.write_text(json.dumps(report))
            with self.assertRaisesRegex(InputError,'volume|integral'):verify(p)

if __name__=='__main__':unittest.main()
