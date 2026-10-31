#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic RC/source controls; never acquire actual native archives."""
import argparse,copy,io,json,os,tempfile,traceback,unittest
from pathlib import Path
from unittest import mock
import cloud_cdr_current_access_rc as r
import cdr_current_access_rc as a
import check_cdr_current_eight_drain_wave_replay as inherited

def fixture():
    raw='.subckt wires A B D E\nR1 A n 2\nR2 n B 3\nR3 A B 10\nR4 D E 7\nC1 A sub 0\nC2 A B 2p\nC3 B D 3p\nC4 D E 4p\n.ends wires\n'
    mapping={n:'w_'+n for n in ('A','B','D','E','n','sub')}
    devices=[];anchors=[];targets=[]
    for i,label in enumerate(('A','B','D','E'),1):
        c=1 if i<=2 else 2
        devices.append(dict(native_id=i,instance='XD'+str(i),model='npn13g2',parameters={'nx':'2'},terminals=[dict(terminal='E',node=mapping[label],anchor=label,native_cluster=c,native_net='$'+str(c))]))
        anchors.append(dict(label=label,wire_component=c,native_cluster=c,point_dbu=[i*100,200],metal=8))
    for c,labels in [(1,('A','B')),(2,('D','E'))]:
        terms=[]
        for d in devices:
            t=d['terminals'][0]
            if t['anchor']in labels:terms.append(dict(id=d['native_id'],model=d['model'],terminal='E',node=t['node'],anchor=t['anchor'],native_net=t['native_net']))
        targets.append(dict(component=c,native_cluster=c,partition={'ports':[],'terminals':[[t['id'],t['model'],'E']for t in terms]},terminals=terms))
    model='.subckt full\n'+'\n'.join('XD'+str(i)+' w_'+label+' npn13g2 nx=2'for i,label in enumerate(('A','B','D','E'),1))+'\n'
    for row in a.parser.statements(raw)[1:-1]:model+=' '.join([row[0],mapping[row[1]],mapping[row[2]],row[3]])+'\n'
    model+='.ends full\n'
    contract=dict(wire_node_map=mapping,device_records=devices,counts=dict(devices=4,R=4,C=4),native_extracted_mim_cards_projected_once=[])
    return model,raw,contract,dict(anchors=anchors),dict(wire_components=[dict(component=c,native_cluster=c)for c in (1,2)]),targets

class AccessControls(unittest.TestCase):
    def test_projection_units_and_full_conservation(self):
        model,wire,c,*_=fixture();rows,p=a.bind_wire_projection(model,wire,c)
        self.assertEqual(p['counts'],dict(R=4,C=4));self.assertEqual(rows[4]['value_si'],0.)
        alternate=model.replace('2p','0.002n');self.assertEqual([x['value_si']for x in a.bind_wire_projection(alternate,wire,c)[0]],[x['value_si']for x in rows])
        self.assertEqual(p['excluded_native_cards'],[]);self.assertEqual(len(p['excluded_composed_device_names']),4)
    def test_projection_refuses_value_name_count_and_foreign_card(self):
        m,w,c,*_=fixture()
        for bad in (m.replace('w_A w_n 2','w_A w_n 9'),m.replace('R2','R1'),m.replace('R4 w_D w_E 7\n',''),m.replace('.ends full','V1 a b 1\n.ends full')):
            with self.assertRaises((AssertionError,KeyError)):a.bind_wire_projection(bad,w,c)
    def test_network_edges_and_boundary_conservation(self):
        m,w,c,anc,g,ts=fixture();e,_=a.bind_wire_projection(m,w,c);n=a.networks(e,c,anc,g,ts)
        self.assertEqual(len(n['networks']),2);self.assertEqual(len(n['edges']),8)
        self.assertEqual(sum(x['id']=='C3'for x in n['edges']),1)
        self.assertEqual(n['global_classification']['target_to_target_C'],1)
        one=a.networks(e,c,anc,g,ts[:1]);self.assertEqual(len(one['edges']),6);self.assertEqual(one['global_classification']['other_R'],1);self.assertEqual(one['global_classification']['other_C'],1)
        boundary=next(x for x in one['edges']if x['id']=='C3');self.assertEqual(boundary['nodes'],['B','D'])
    def test_network_refuses_disconnected_foreign_and_missing_anchor(self):
        m,w,c,anc,g,ts=fixture();e,_=a.bind_wire_projection(m,w,c)
        for es,cs,aa,gg,tt in [(e[:1]+e[3:],c,anc,g,ts),(e+[dict(id='R5',kind='R',nodes=['A','D'],value_si=1.)],c,anc,g,ts),(e,c,dict(anchors=anc['anchors'][1:]),g,ts)]:
            with self.assertRaises((AssertionError,KeyError)):a.networks(es,cs,aa,gg,tt)
    def test_raw_coordinates_preserve_unknown_layer_and_missing_node(self):
        loc=a.native_locations([('n.ext','scale 1000 1 0.5\nnode "A" 0 0 10 20 metal1\n'),('n.res.ext','rnode "n" 0 3 12 21 0\nresist "A" "n" 2\n')],{'A','n','B'})
        self.assertEqual(loc['nodes']['A']['coordinates'][0]['raw_xy'],[10,20])
        self.assertIsNone(loc['nodes']['n']['coordinates'][0]['layer']);self.assertEqual(loc['unresolved_coordinate_nodes'],['B'])
        self.assertEqual(loc['headers']['n.res.ext']['scale_tokens'],['1000','1','0.5'])
        with self.assertRaises(AssertionError):a.native_locations([('a.ext','scale 1 1 1\nscale 1 1 2\n')],{'A'})
    def test_solver_analytic_parallel_and_series(self):
        e=[('ab','a','b',2.),('bc','b','c',3.),('ac','a','c',10.)]
        self.assertAlmostEqual(a.solve(e,'a','c')['effective_wire_R_ohm'],10/3)
        self.assertAlmostEqual(a.solve(e[:2],'a','c')['effective_wire_R_ohm'],5.)
    def test_solver_reversal_permutation(self):
        e=[('ab','a','b',2.),('bc','b','c',3.),('ac','a','c',10.)]
        expected=a.solve(e,'a','c')['effective_wire_R_ohm']
        for changed in (list(reversed(e)),[(n,b,a,r)for n,a,b,r in e],e[1:]+e[:1]):
            self.assertAlmostEqual(a.solve(changed,'c','a')['effective_wire_R_ohm'],expected)
    def test_solver_units_and_sensitivity(self):
        e=[('ab','a','b',2.),('bc','b','c',3.),('ac','a','c',10.)]
        original=a.solve(e,'a','c');scaled=a.solve([(n,x,y,r*1000)for n,x,y,r in e],'a','c')
        self.assertAlmostEqual(scaled['effective_wire_R_ohm']/1000,original['effective_wire_R_ohm'])
        self.assertAlmostEqual(original['energy_sum_ohm'],original['effective_wire_R_ohm'])
        self.assertGreater(a.solve([('ab','a','b',20.),*e[1:]],'a','c')['effective_wire_R_ohm'],original['effective_wire_R_ohm'])
    def test_solver_rejects_singular_disconnected_negative_nonfinite(self):
        for v in (0.,-1.,float('nan'),float('inf')):
            with self.assertRaises(AssertionError):a.solve([('ab','a','b',v)],'a','b')
        with self.assertRaises(AssertionError):a.solve([('aa','a','a',1.)],'a','a')
        with self.assertRaises(ValueError):a.solve([('ab','a','b',1.),('cd','c','d',1.)],'a','d')
        with self.assertRaises(ValueError):a.solve([],'a','b')
        with self.assertRaises(AssertionError):a.rc_rows('.subckt x\nR1 a b -1\n.ends\n')
    def test_paths_and_all_terminal_pairs(self):
        m,w,c,anc,g,ts=fixture();e,_=a.bind_wire_projection(m,w,c);n=a.networks(e,c,anc,g,ts)
        result=a.evaluate(n);self.assertEqual(len(result['evaluations']),2)
        first=result['evaluations'][0];self.assertEqual(first['actual_graph_path']['edges'],['R1','R2']);self.assertAlmostEqual(first['solution']['effective_wire_R_ohm'],10/3)
        with self.assertRaises(AssertionError):a.shortest_path([('r','a','b',1.)],'a','c')
    def test_exact_solver_and_context_authority(self):
        c=r.source_guard();self.assertTrue(a.solver_source_guard(r.ROOT/c['linear_solver']['path'])['original_body_unchanged'])
        env=dict(GITHUB_ACTIONS='true',GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_REPOSITORY='Melihakbulut221/nssoc',GITHUB_REF='refs/heads/'+r.BRANCH,GITHUB_RUN_ATTEMPT='1',GITHUB_RUN_ID='123',GITHUB_SHA='a'*40)
        ctx=r.context(env,'nominal_late')
        for key,value in [('GITHUB_REF','refs/heads/main'),('GITHUB_RUN_ATTEMPT','2'),('GITHUB_ACTIONS','false')]:
            with self.assertRaises(AssertionError):r.context(dict(env,**{key:value}),'nominal_late')
        with self.assertRaises(AssertionError):r.context(env,'nominal_early')
        with self.assertRaisesRegex(AssertionError,'readback disabled'):r.perform(ctx,{},b'{}',Path('uncreated'),dict(c,readback_authorized=False))
    def test_failure_retains_partial_primary_and_does_not_clobber(self):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);out=root/'failed';primary=ValueError('primary failure');secondary=ValueError('emission failure')
            def perform(*args,**kwargs):r.q.write_new(args[3]/'partial.json',b'{}');raise primary
            with mock.patch.object(r,'perform',side_effect=perform),mock.patch.object(r.q,'emit',side_effect=secondary):
                with self.assertRaises(ValueError)as caught:r.run(dict(source='a'*40),{},b'{}',out)
            self.assertIs(caught.exception,primary);self.assertTrue((out/'partial.json').is_file());self.assertIn('primary failure',json.loads((out/'readback-failure.json').read_bytes())['error'])
            self.assertTrue((out/'emission-error.json').is_file())
            with self.assertRaisesRegex(AssertionError,'output no overwrite'):r.run({}, {},b'{}',out)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();ctx=r.context(os.environ);primary=None
    try:
        c=r.source_guard();r.checkout_binding(ctx,c)
        old=inherited.controls();stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(AccessControls)
        outcome=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        result=dict(status='PASS_CDR_CURRENT_ACCESS_RC_SOURCE_CONTROLS'if outcome.wasSuccessful()else'FAIL_CDR_CURRENT_ACCESS_RC_SOURCE_CONTROLS',passed=outcome.wasSuccessful(),current_context=ctx,inherited_counts=old['counts'],sampler_test_methods=old['sampler_test_methods'],access_test_methods=outcome.testsRun,access_tests_successful=outcome.wasSuccessful(),access_test_output=stream.getvalue(),inherited=old,actual_native_acquired=False,physical_acceptance=False)
        r.require(outcome.testsRun==12 and outcome.wasSuccessful(),'all twelve RC controls pass')
        r.controls_binding(r.encode(result),ctx);r.checkout_binding(ctx,c)
    except BaseException as error:
        primary=error
        if 'result'not in locals():result={}
        result.update(status='FAIL_CDR_CURRENT_ACCESS_RC_SOURCE_CONTROLS',passed=False,error=repr(error),traceback=traceback.format_exc(),actual_native_acquired=False,physical_acceptance=False)
    r.q.write_new(args.output,r.encode(result));print(r.encode(result).decode(),flush=True)
    if primary is not None:raise primary
if __name__=='__main__':main()
