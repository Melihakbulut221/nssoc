#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source, provenance and geometry fixture controls; never acquire real inputs."""
import argparse,ast,copy,hashlib,io,json,os,tempfile,traceback,unittest
from pathlib import Path
from unittest import mock
import cloud_cdr_current_access_geometry as r
import cdr_current_access_geometry_native as n
import check_cdr_current_access_rc as original_rc
import check_cdr_current_eight_drain_wave_replay as inherited
class GeometryControls(unittest.TestCase):
    def test_current_nodes_units_and_raw_refusals(self):
        got=n.unit_controls();self.assertEqual(got['positive'],1);self.assertEqual(len(got['refusals']),4)
    def test_exact_instance_path_and_bad_roots(self):
        self.assertEqual(n.parse_path(n.TOP+'/8_1/2_0'),[(8,1),(2,0)])
        for value in(n.TOP,'wrong/2_0',n.TOP+'/02_0',n.TOP+'/1_0/../2_0',n.TOP+'/1_-1'):
            with self.assertRaises(AssertionError):n.parse_path(value)
    def test_current_all_four_net_incidence(self):
        c=r.source_guard();data=r.decode(r.q.regular(r.ROOT,c['incidence']).read_bytes())
        self.assertEqual(set(data['targets']),{'28','38','135','136'})
        for key,target in data['targets'].items():
            self.assertEqual(len(n.point_rows(target)),c['targets'][key]['node_count'])
            self.assertEqual(len(target['contacts']),c['targets'][key]['contact_count'])
            self.assertEqual(target['native_net'],c['targets'][key]['native_name'])
    def test_same_source_and_authority_refusals(self):
        c=r.source_guard();env=dict(GITHUB_ACTIONS='true',GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_REPOSITORY='Melihakbulut221/nssoc',GITHUB_REF='refs/heads/'+r.BRANCH,GITHUB_RUN_ATTEMPT='1',GITHUB_RUN_ID='123',GITHUB_SHA='a'*40)
        ctx=r.context(env,'nominal_late')
        for key,value in[('GITHUB_REF','refs/heads/main'),('GITHUB_RUN_ATTEMPT','2'),('GITHUB_ACTIONS','false')]:
            with self.assertRaises(AssertionError):r.context(dict(env,**{key:value}),'nominal_late')
        with self.assertRaises(AssertionError):r.context(env,'nominal_early')
        with self.assertRaisesRegex(AssertionError,'readback disabled'):r.perform(ctx,{},b'{}',Path('not-created'),dict(c,readback_authorized=False))
    def test_preserved_native_helpers_exact_source(self):
        c=r.source_guard();raw=(r.ROOT/c['helper_origin']['path']).read_text();new=(r.ROOT/'scripts/cdr_current_access_geometry_native.py').read_text()
        a={x.name:ast.get_source_segment(raw,x)for x in ast.parse(raw).body if isinstance(x,ast.FunctionDef)}
        b={x.name:ast.get_source_segment(new,x)for x in ast.parse(new).body if isinstance(x,ast.FunctionDef)}
        self.assertEqual(len(c['unchanged_helper_functions']),13)
        for name in c['unchanged_helper_functions']:self.assertEqual(a[name],b[name],name)
    def test_exact_global_inputs_and_non_native_source_proof(self):
        c=r.source_guard();self.assertEqual(len(c['selected']),17);self.assertEqual(set(c['selected']),set(c['selected_bytes']))
        self.assertFalse(any('wave.raw'in p or p.endswith('.gz')for p in c['selected']))
        self.assertEqual(c['expected_native_member_count'],2991)
        self.assertTrue(c['inspection_only']);self.assertTrue(c['all_acceptance_false']);self.assertFalse(c['native_simulation'])
        self.assertEqual(c['paths']['gds'],'native/current-mim-bundle/canonical-current-view/parent/layout/nssoc_cdr_pd500_resistor_v59.gds')
    def test_failure_retains_primary_partial_and_no_overwrite(self):
        with tempfile.TemporaryDirectory()as td:
            out=Path(td)/'failed';primary=ValueError('exact-primary');secondary=ValueError('exact-emission')
            def perform(*args,**kwargs):r.q.write_new(args[3]/'partial.json',b'{}');raise primary
            with mock.patch.object(r,'perform',side_effect=perform),mock.patch.object(r.q,'emit',side_effect=secondary):
                with self.assertRaises(ValueError)as caught:r.run(dict(source='a'*40),{},b'{}',out)
            self.assertIs(caught.exception,primary);self.assertTrue((out/'partial.json').is_file());self.assertTrue((out/'emission-error.json').is_file())
            self.assertIn('exact-primary',json.loads((out/'readback-failure.json').read_bytes())['error'])
            with self.assertRaisesRegex(AssertionError,'output no overwrite'):r.run({}, {},b'{}',out)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--native-proof',type=Path,required=True);a=p.parse_args();ctx=r.context(os.environ);primary=None
    try:
        c=r.source_guard();r.checkout_binding(ctx,c);original_rc.a.load_numeric_dependencies()
        old=inherited.controls();stream=io.StringIO()
        def run(cls):return unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
        rc=run(original_rc.AccessControls);geometry=run(GeometryControls)
        fixture=r.decode(r.q.regular(a.native_proof.parent,a.native_proof.name).read_bytes())
        policy=r.decode(r.q.regular(a.native_proof.parent.parent,'runtime-policy.json').read_bytes())
        require=r.require;require({k:policy[k]for k in('source','run_id','attempt')}==ctx,'same-source actual native fixtures')
        lifecycle=r.decode(r.q.regular(a.native_proof.parent.parent,'native-lifecycle.json').read_bytes())
        require(lifecycle['controls_only']is True and lifecycle['primary_error']is None and lifecycle['errors']==[],'complete fixture lifecycle')
        result=dict(status='PASS_CDR_CURRENT_ACCESS_GEOMETRY_SOURCE_CONTROLS',passed=True,current_context=ctx,
          inherited_counts=old['counts'],sampler_test_methods=old['sampler_test_methods'],inherited=old,
          access_test_methods=rc.testsRun,access_tests_successful=rc.wasSuccessful(),
          geometry_test_methods=geometry.testsRun,geometry_tests_successful=geometry.wasSuccessful(),
          test_output=stream.getvalue(),native_fixtures=fixture,native_fixture_pin=r.q.file_pin(a.native_proof),
          actual_native_acquired=False,physical_acceptance=False)
        r.controls_binding(r.encode(result),ctx);r.checkout_binding(ctx,c)
    except BaseException as error:
        primary=error
        if 'result'not in locals():result={}
        result.update(status='FAIL_CDR_CURRENT_ACCESS_GEOMETRY_SOURCE_CONTROLS',passed=False,error=repr(error),traceback=traceback.format_exc(),actual_native_acquired=False,physical_acceptance=False)
        if 'stream'in locals():result['test_output']=stream.getvalue()
    r.q.write_new(a.output,r.encode(result));print(r.encode(result).decode(),flush=True)
    if primary is not None:raise primary
if __name__=='__main__':main()
