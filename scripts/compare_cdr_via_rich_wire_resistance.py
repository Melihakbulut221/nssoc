#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare actual CDR conductor resistance using unchanged native device locations."""
import copy,json,os
from pathlib import Path
import analyze_cdr_wire_resistance as linear
import build_pcie_local_vco_hybrid_v6 as parser
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-via-rich-wire-comparison'
SOLVER_SHA='0b3be4b3e7b20fe722240f569a3f55b0f0ab5cb0ef1bafc3b44e92cfd9082288'

def physical_key(d):
    return d['model'],d['pcell']['transform'],d['pcell']['bbox']

def validate_mapping(old,new,mapping):
    a={d['native_id']:d for d in old};b={d['native_id']:d for d in new}
    assert len(a)==len(b)==len(mapping)==484 and set(mapping)==set(a)and set(mapping.values())==set(b)
    nets={};reverse={}
    for i,j in mapping.items():
        x,y=a[i],b[j]
        assert physical_key(x)==physical_key(y)and x['parameters']==y['parameters']
        xt={t['name']:t['net']for t in x['terminals']};yt={t['name']:t['net']for t in y['terminals']}
        assert set(xt)==set(yt)
        for t,n in xt.items():
            m=yt[t];assert nets.setdefault(n,m)==m and reverse.setdefault(m,n)==n
            if not n.startswith('$'):assert n==m
    return dict(old_to_new_native_nets=nets,device_count=len(mapping))

def load_model(version):
    prefix='cdr-'+version+'-mim-composition';pin=json.loads((ROOT/('docs/evidence/'+prefix+'-pass-20261018.json')).read_text())
    selected=['pd484-mim-wire.spice','composition.json'];dest=OUT/version
    prior,proof=reports.restore_report(prefix,pin['run'],pin['summary_sha256'],pin['parts_sha256'],dest,selected)
    assert prior==pin['report']and prior['sources_unchanged']and len(prior['controls'])==19
    c=json.loads((dest/'composition.json').read_text());assert c==prior['composition']
    wireprefix='cdr-retimed-'+version+'-wire-inputs';wp=json.loads((ROOT/('docs/evidence/'+wireprefix+'-pass-20261018.json')).read_text())
    w,wp_proof=reports.restore_report(wireprefix,wp['run'],wp['summary_sha256'],wp['parts_sha256'],dest/'geometry',['wire/device-locations01.json'])
    assert w['source_head']==wp['source_head']and w['sources_unchanged']and w['outputs']==wp['outputs']
    bp=json.loads((ROOT/('docs/evidence/cdr-retimed-'+version+'-binding-pass-20261018.json')).read_text())
    assert prior['model_source']['summary_sha256']==bp['summary_sha256']
    assert bp['report']['physical_source']['summary_sha256']==wp['summary_sha256']
    locations=json.loads((dest/'geometry/wire/device-locations01.json').read_text())['devices']
    records={d['native_id']:d for d in c['device_records']};assert len(records)==len(locations)==484
    for d in locations:
        rec=records[d['native_id']];assert rec['model']==('npn13g2'if d['model']=='npn13G2'else d['model'])
        assert {t['name']:t['net']for t in d['terminals']}=={t['terminal']:t['native_net']for t in rec['terminals']}
    edges=[]
    for row in parser.statements((dest/'pd484-mim-wire.spice').read_text())[1:-1]:
        if row[0].startswith('R'):
            assert len(row)==4;edges.append((row[0],row[1].lower(),row[2].lower(),float(parser.number(row[3]))))
    assert len(edges)==c['counts']['R']
    protected={str(dest/n):prior['outputs'][n]for n in selected}
    protected[str(dest/'geometry/wire/device-locations01.json')]=w['outputs']['wire/device-locations01.json']
    return dict(composition=c,locations=locations,records=records,edges=edges,proof=proof,geometry_proof=wp_proof,protected=protected)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',full_phy_accepted=False,qualified_pex=False,source_head=os.environ['GITHUB_SHA'],electrical_waveform_acceptance=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        assert sha(Path(linear.__file__))==SOLVER_SHA;r['linear_controls']=linear.controls()
        old=load_model('strapped-v6');new=load_model('via-rich-v7')
        a={physical_key(d):d['native_id']for d in old['locations']};b={physical_key(d):d['native_id']for d in new['locations']}
        assert len(a)==len(b)==484 and set(a)==set(b)
        mapping={a[k]:b[k]for k in a};r['physical_mapping']=validate_mapping(old['locations'],new['locations'],mapping)
        r['mapping_controls']=[]
        for case in ('missing_device','swapped_physical_identity'):
            changed=dict(mapping);ids=sorted(changed)
            if case=='missing_device':del changed[ids[0]]
            else:changed[ids[0]],changed[ids[1]]=changed[ids[1]],changed[ids[0]]
            try:validate_mapping(old['locations'],new['locations'],changed)
            except AssertionError:r['mapping_controls'].append(dict(case=case,rejected=True))
            else:raise AssertionError('Accepted '+case)
        pin=json.loads((ROOT/'docs/evidence/cdr-strapped-v6-wire-bottleneck-20261018.json').read_text())
        previous=pin['report_excerpt']['linear_wire_resistance_diagnosis']['evaluations'];assert len(previous)==64
        evaluations=[]
        for row in previous:
            lid=int(row['load'].removeprefix('xd'));qid=int(row['collector'].removeprefix('xd'));values={}
            for version,state,dl,dq in [('strapped-v6',old,lid,qid),('via-rich-v7',new,mapping[lid],mapping[qid])]:
                load=state['records'][dl];q=state['records'][dq];assert load['model']=='rppd'and q['model']=='npn13g2'
                lt={t['terminal']:t for t in load['terminals']};qt={t['terminal']:t for t in q['terminals']}
                assert lt['rppd_1']['native_net']=='avdd'and lt['rppd_2']['native_net']==qt['C']['native_net']
                start,stop=('avdd',lt['rppd_1']['node'])if row['kind']=='supply'else(lt['rppd_2']['node'],qt['C']['node'])
                solution=linear.solve(state['edges'],start.lower(),stop.lower())
                raw={v.lower():k for k,v in state['composition']['wire_node_map'].items()}
                for e in solution['dominant_edges']:e['raw_wire_nodes']=[raw[e['from_node']],raw[e['to_node']]]
                values[version]=dict(load=load['instance'],collector=q['instance'],solution=solution)
            before=values['strapped-v6']['solution']['effective_wire_R_ohm'];after=values['via-rich-v7']['solution']['effective_wire_R_ohm']
            assert abs(before-row['wire_solution']['effective_wire_R_ohm'])<=1e-7*max(1.,before)
            evaluations.append(dict(kind=row['kind'],logical_net=row['logical_net'],old_load=row['load'],old_collector=row['collector'],old_R_ohm=before,new_R_ohm=after,new_over_old=after/before,reduction_percent=100*(1-after/before),models=values))
        assert len(evaluations)==64
        r['evaluations']=evaluations;r['summary']={kind:dict(count=len(xs),old_R_min=min(x['old_R_ohm']for x in xs),old_R_max=max(x['old_R_ohm']for x in xs),new_R_min=min(x['new_R_ohm']for x in xs),new_R_max=max(x['new_R_ohm']for x in xs),reduction_percent_min=min(x['reduction_percent']for x in xs),reduction_percent_max=max(x['reduction_percent']for x in xs))for kind in ('supply','load_to_collector')for xs in [[x for x in evaluations if x['kind']==kind]]}
        r['sources']={v:dict(composition=s['proof'],native_geometry=s['geometry_proof'])for v,s in [('strapped-v6',old),('via-rich-v7',new)]}
        assert all(sha(Path(p))==h for s in (old,new)for p,h in s['protected'].items())and sha(Path(linear.__file__))==SOLVER_SHA
        r['sources_unchanged']=True;r['status']='COMPLETE_NATIVE_LINEAR_WIRE_COMPARISON_LOADED_WAVE_GATES_REMAIN_REQUIRED'
        r['interpretation']='Unit-current two-terminal DC linear wire calculation with other terminals floating, not actual device currents, transient delay, EM or RF/PEX qualification. All64 old calculations reproduced. Physical identity and native topology validated before correspondence. No electrical acceptance is inferred from a resistance reduction.'
    except BaseException as e:r.update(status='FAIL_WIRE_COMPARISON',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
