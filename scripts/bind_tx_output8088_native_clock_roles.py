#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Native clock-load role binder candidate. No electrical or phase acceptance."""
import copy,hashlib,json,os,runpy,sys
from pathlib import Path
SOURCE_RUN=40083738813
SOURCE_HEAD='11ed6ba3e7ecd4b184ee0161c5b8a1699c539a56'
SUMMARY='e872278654de17a300e5004c463a1ad37b5c9e1116ed7d8720e2872f8124c2b9'
PARTS='278156444c2bd2159f6f029f8f3a9d51ad156d1a84a751ea41e4e75e6b5b6a51'
PIN={"topology.json":"03caa3a4f54f8e14402894a81321e33796f6ec6c502ec39fcc59e4db20e1dd5d","bind-native-interfaces.py":"afebfeb3a6c2a4c8c90760786450577b9c2f4b7994c28d05b833f7ebeebbca7a","interfaces.json":"13bfff54e68a5355547fc64e4ebdd64e347c5b54a43b8c924b9ece724b009aaf","original-physical/integration-result.json":"4e6bfef0b32c90e9ddcc57c382566aa75ab01bf070f58587f161f6739ef3e48a","composed/output8088-wire.spice":"8286d54832432603f78739f30d0087e99a46f026d82a37ecd5e450d2167231c8","composed/composition.json":"093dba5b465ee54cc8232d28c196be13eaf7c74637ed742989c44d75976e9708","wires/source/native01/result.json":"8469220a158803d8e461e08d1ab999ba4bc82a6f3c24f21a166e93918dc7f319","physical/layout/layout.gds":"9ed77cbd9cf7eff9939e9a9b94c6e516d98937b0174776f4a3dd6380c04d3ac0","physical/flat_lvs/result.lvsdb":"809722e328b8d1bc30176e0ad9951886d283e8873e6bf70ba433c858b2b07c3c","core-metadata/source/handoff-result.json":"0872a917cb63cac3631ad9b59c1e0aaca001346d2bff1d7bbbfc4a67859ef796","core-metadata/source/core/layout/result.json":"b6a29ebb58dd4ef4127a69d94974676421ca9005d8076bf6c727e0a19bd3e621","composed/intrinsic/native.json":"de0dbe551886517b6eb0f182993bb2e4efd7482f6a339763f481e02925c705b1","composed/intrinsic/source/anchors.json":"447c285a3912324fb1598659eaaf5ce8e931700c2b7ef9332674a94e48206bea"}
def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def bind(g):
    # Namespace comes only from the byte-pinned original native binder execution.
    pya=g['pya'];rows=g['rows'];records=g['records'];devices=g['devices']
    endpoint=g['endpoint'];public=g['public'];probe=g['probe'];anchors=g['anchors']
    contract=g['contract'];nodes=g['plan']['nodes']
    assert len(nodes)==31 and len({m['label']for m in nodes})==31
    assert len({m['clock']for m in nodes})==31
    assert sum(m['label']=='f'and m['clock']=='s'for m in nodes)==1
    expected={};all_bases=set();all_tails=set();tail_clusters=set()
    data_ids={t['native_id']for r in g['expected'].values()for t in r['terminals']}
    assert len(data_ids)==372
    def cluster(did,terminal):return rows[did,terminal]['native_cluster']
    def nx(did):
        d=devices[did];assert d.device_class().name=='npn13G2'
        p={x.name.lower():d.parameter(x.id())for x in d.device_class().parameter_definitions()}
        assert p['nx']==8.0,'Actual selector/tail emitter multiplier changed'
        return p
    def terminal(did,name):
        a=rows[did,name];rec=records[did]
        ts=[t for t in rec['terminals']if t['terminal']==name];assert len(ts)==1
        t=ts[0]
        assert a['native_cluster']==t['native_cluster']
        if name=='B':
            assert a['disposition']=='ACTUAL_TERMINAL_METAL_REFERENCE_WITH_UNMODELED_DEVICE_ACCESS_R'
            assert t['reference_label']==a['reference_label']
            assert contract['wire_node_map'][a['reference_label']]==t['node']
            assert probe(a['metal'],pya.Point(*a['point_dbu'])).cluster_id==a['native_cluster']
        return dict(native_id=did,instance=rec['instance'],terminal=name,
                    anchor=copy.deepcopy(a),composed=copy.deepcopy(t))
    for macro in nodes:
        label=macro['label'];box=g['shifted'](g['cm']['placements'][label]['bbox_um'])
        local={did for did,bounds in g['hbts'].items()if(bounds&box)==bounds}
        assert len(local)==19,(label,'Actual mux must contain exactly19 HBTs',len(local))
        bank_collectors={};selector_emitters=set();macro_ids=[]
        for leg,bank,input_name in zip('pn',('a','b'),macro['inputs'],strict=True):
            key=macro['clock']+leg;assert key not in expected and key in public
            sink=endpoint(label+'.s'+leg)
            assert sink['native_cluster']==public[key],'Native clock port polarity/connection changed'
            pi=g['integration']['external_ports'][key]
            point=pya.Box.from_s(pi['box_dbu']).center()
            assert probe(pi['layer'],point).cluster_id==public[key]
            pa=[a for a in anchors['public']if a['name']==key];assert len(pa)==1
            assert pa[0]['reference_label']=='P_'+key
            assert contract['wire_node_map']['P_'+key]==key
            ids=sorted(did for did in local if cluster(did,'B')==sink['native_cluster'])
            assert len(ids)==2,(key,'Clock must drive two actual selector bases',ids)
            assert not(set(ids)&data_ids)and not(set(ids)&all_bases)
            all_bases.update(ids);macro_ids.extend(ids)
            # Independent role/polarity proof: positive selects A, negative B.
            # Collector must be the emitter node of all six already-native-bound
            # input HBTs in that bank, and both selectors share the real tail.
            bank_data=sorted(t['native_id']for suffix in 'pn'
                             for t in g['expected'][input_name+suffix]['terminals'])
            assert len(set(bank_data))==6 and set(bank_data)<=local
            ec={cluster(did,'E')for did in bank_data};assert len(ec)==1
            collector=next(iter(ec));bank_collectors[bank]=collector
            terms=[]
            for did in ids:
                assert cluster(did,'C')==collector,'Clock selector is attached to wrong data bank'
                selector_emitters.add(cluster(did,'E'));parameters=nx(did)
                terms.append(dict(native_id=did,parameters=parameters,
                                  terminals={t:terminal(did,t)for t in('C','B','E','S')}))
            expected[key]=dict(macro=label,clock=macro['clock'],leg=leg,selected_bank=bank,
                selected_input=input_name,public_port=key,native_cluster=public[key],
                public_point_dbu=[point.x,point.y],public_layer=pi['layer'],
                public_anchor=copy.deepcopy(pa[0]),sink=sink,selector_devices=terms,
                data_bank_devices=bank_data,data_emitter_cluster=collector)
        assert bank_collectors['a']!=bank_collectors['b']
        assert len(selector_emitters)==1
        tail=next(iter(selector_emitters))
        assert tail not in bank_collectors.values()and tail not in tail_clusters
        tail_clusters.add(tail)
        iref=endpoint(label+'.iref')['native_cluster']
        avss=endpoint(label+'.avss')['native_cluster']
        tails=sorted(did for did in local if cluster(did,'C')==tail and
                     cluster(did,'B')==iref and cluster(did,'E')==avss)
        assert len(tails)==2 and not(set(tails)&(data_ids|all_bases|all_tails))
        all_tails.update(tails)
        for did in tails:nx(did)
        for leg in 'pn':
            expected[macro['clock']+leg].update(tail_cluster=tail,
                tail_devices=[dict(native_id=d,parameters=nx(d),
                    terminals={t:terminal(d,t)for t in('C','B','E','S')})for d in tails])
    assert len(expected)==62 and len(all_bases)==124 and len(all_tails)==62
    assert len({x['native_cluster']for x in expected.values()})==62
    assert len({d['terminals']['B']['composed']['node']for x in expected.values()
                for d in x['selector_devices']})==124
    def verify(candidate):
        assert set(candidate)==set(expected),'Missing or aliased native clock'
        for key,item in candidate.items():
            assert item==expected[key],'Actual native clock polarity, role or model plane changed'
    verify(expected);controls=[]
    for fault in('missing_clock','swapped_clock_polarity','wrong_clock_owner',
                 'wrong_bank_role','data_device_as_selector','missing_selector',
                 'duplicate_selector','wrong_Nx','wrong_base_node','wrong_base_cluster',
                 'wrong_public_point','wrong_sink_point','wrong_collector','wrong_tail'):
        wrong=copy.deepcopy(expected);key=next(iter(wrong));item=wrong[key]
        d=item['selector_devices'][0]
        if fault=='missing_clock':del wrong[key]
        elif fault=='swapped_clock_polarity':
            other=key[:-1]+('n'if key.endswith('p')else'p')
            wrong[key],wrong[other]=wrong[other],wrong[key]
        elif fault=='wrong_clock_owner':item['macro']='foreign_macro'
        elif fault=='wrong_bank_role':item['selected_bank']='b'if item['selected_bank']=='a'else'a'
        elif fault=='data_device_as_selector':d['native_id']=item['data_bank_devices'][0]
        elif fault=='missing_selector':item['selector_devices'].pop()
        elif fault=='duplicate_selector':item['selector_devices'][1]=copy.deepcopy(d)
        elif fault=='wrong_Nx':d['parameters']['nx']=4.0
        elif fault=='wrong_base_node':d['terminals']['B']['composed']['node']='0'
        elif fault=='wrong_base_cluster':d['terminals']['B']['anchor']['native_cluster']=-1
        elif fault=='wrong_public_point':item['public_point_dbu'][0]+=1
        elif fault=='wrong_sink_point':item['sink']['point_dbu'][0]+=1
        elif fault=='wrong_collector':d['terminals']['C']['anchor']['native_cluster']=-1
        else:item['tail_cluster']=-1
        try:verify(wrong)
        except AssertionError as e:controls.append(dict(name=fault,rejected=True,reason=str(e)))
        else:raise AssertionError('Accepted '+fault)
    actual_faults=[]
    for macro in nodes:
        p=endpoint(macro['label']+'.sp');n=endpoint(macro['label']+'.sn')
        assert p['native_cluster']!=public[macro['clock']+'n']
        assert n['native_cluster']!=public[macro['clock']+'p']
        actual_faults.append(dict(macro=macro['label'],wrong_p_to_n_rejected=True,
                                  wrong_n_to_p_rejected=True))
    return dict(status='PASS_NATIVE_CLOCK_ROLE_BINDING_REQUIRES_REAL_DRIVER_AND_LOADED_WAVES',
                clocks=expected,counts=dict(pairs=31,public_clock_legs=62,selector_HBT_bases=124,
                    tail_HBTs=62,original_native_terminals_rechecked=28620),
                role_controls=controls,actual_polarity_faults=actual_faults,
                source_run=SOURCE_RUN,source_head=SOURCE_HEAD,summary_sha256=SUMMARY,parts_sha256=PARTS,
                native_reprobe=True,real_clock_drivers_implemented=False,electrical_accepted=False,
                reset_distribution_accepted=False,full31_tree_accepted=False,PLL_connected=False,
                full_phy_accepted=False,mainchip_integrated=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
    assert len(sys.argv)==4,'restored qualified workspace, exact source summary, new output directory required'
    workspace,summary,out=map(Path,sys.argv[1:]);assert sha(summary)==SUMMARY
    s=json.loads(summary.read_text());assert s['source_head']==SOURCE_HEAD
    assert s['status']=='PASS_ACTUAL8088_NATIVE124_INPUTS372_BASES64_DRIVER_HANDOFFS_FOUR_OUTPUT_PORTS_REQUIRES_LOADED_WAVES'
    assert s['sources_unchanged']and s['interfaces_sha256']==PIN['interfaces.json']
    for p,h in PIN.items():assert s['outputs'][p]==h and sha(workspace/p)==h,(p,'Qualified input changed')
    # New directory only. The original qualified files, including interfaces.json,
    # are immutable. Original native binder is executed without any source edit.
    out.mkdir(parents=True,exist_ok=False)
    oldargv=sys.argv
    try:
        sys.argv=[str(workspace/'bind-native-interfaces.py'),str(workspace),str(out/'original-interfaces.json')]
        g=runpy.run_path(sys.argv[0],run_name='__main__')
    finally:sys.argv=oldargv
    assert sha(out/'original-interfaces.json')==PIN['interfaces.json']
    result=bind(g)
    assert all(sha(workspace/p)==h for p,h in PIN.items())
    result['qualified_inputs_unchanged']=True;result['qualified_input_hashes']=PIN
    (out/'clock-roles.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'])
if __name__=='__main__':main()
