#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Replace both physical divider models, retaining parent wiring as an explicit unverified boundary."""
import json,os,re
from pathlib import Path
from collections import Counter
from decimal import Decimal
import networkx as nx
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as h
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-pll-divider-load3p2-parent'
PARENT_SHA='8147a7cbae9d1a43b362733a3b52c218c5d04ef519cedf9abf35cd17ff27911e'
MODEL_SHA='4331b1e4d301d99c3f035c03a80906281e83533755c5927ceeccb6dea216e1c5'
ARITY={'npn13g2':4,'rppd':3,'cap_cmim':2,'ptap1':2}
PORTS=['clkp','clkn','qp','qn','div_avdd','avss','sub','wire_cref']
def intrinsic(row):
    row=[s.lower()for s in row]
    k=next(i for i,s in enumerate(row)if '='in s)-1
    model=row[k];assert model in ARITY and k==ARITY[model]+1
    words=row[k+1:];params={s.split('=',1)[0]:h.number(s.split('=',1)[1])for s in words};assert len(params)==len(words)
    return row[1:k],model,params
def boundary(group):
    return {p:'a_'+group[1:]+'_'+p for p in PORTS[:-1]}|{'wire_cref':'wire_cref','bulk':'a_count_vss'}
def grouped(rows,group):
    return [r for r in rows if any(r[0].lower().startswith(k+'_'+group+'_')for k in 'xrc')]
def graph(rows,group,normalize_candidate):
    union=h.Union()
    for r in rows:
        if r[0].lower().startswith('r'):
            assert len(r)==4 and h.number(r[3])>0;union.join(r[1].lower(),r[2].lower())
    public={v:k for k,v in boundary(group).items()if k!='wire_cref'}
    public_roots={union.find(n):p for n,p in public.items()};assert len(public_roots)==8,'Collapsed public/body short'
    graph=nx.Graph();changed=[]
    roles={'npn13g2':['C','B','E','S'],'rppd':['END','END','BODY'],'cap_cmim':['PLUS','MINUS'],'ptap1':['TIE','WELL']}
    for row in rows:
        if not row[0].lower().startswith('x'):continue
        nodes,model,params=intrinsic(row);name=row[0].lower()
        if model=='ptap1':
            assert set(params) in ({'r'},{'r','w','l'})
            if 'w'in params:assert params.pop('w')==params.pop('l')==Decimal('2e-6')
        if normalize_candidate and model=='rppd'and params['w'].quantize(Decimal('1e-12'))==Decimal('8e-6')and params['l'].quantize(Decimal('1e-12'))==Decimal('3.2e-6'):
            changed.append(name);params['l']=Decimal('2.12e-6')
        # Native extraction serializes dimension floats; a picometer grid is
        # 1000x finer than the source GDS nanometer grid. Record that policy.
        params={k:str(v.quantize(Decimal('1e-12')))for k,v in params.items()}
        graph.add_node(('D',name),color=('device',model,tuple(sorted(params.items()))))
        for i,(node,role)in enumerate(zip(nodes,roles[model],strict=True)):
            root=union.find(node);net=('N',root);terminal=('T',name,i)
            graph.add_node(net,color=('net',public_roots.get(root,'internal')))
            graph.add_node(terminal,color=('terminal',role));graph.add_edge(('D',name),terminal);graph.add_edge(terminal,net)
    assert len([n for n in graph if n[0]=='D'])==91
    assert len(changed)==(4 if normalize_candidate else 0)
    return graph,changed
def prepare(original,model):
    old=h.statements(original);child=h.statements(model)
    assert old[0][0]=='.subckt'and old[-1][0]=='.ends'
    assert [n.lower()for n in child[0][2:]]==PORTS and child[-1]==['.ends',child[0][1]]
    assert Counter(r[0][0].upper()for r in child[1:-1])==dict(X=91,R=382,C=649)
    retained=[r for r in old[1:-1]if r not in grouped(old[1:-1],'xdiv1')and r not in grouped(old[1:-1],'xdiv2')]
    added=[];mapping={};proof=[]
    for group in ['xdiv1','xdiv2']:
        prior=grouped(old[1:-1],group);assert Counter(r[0][0].upper()for r in prior)==dict(X=91,R=379,C=646)
        ext=boundary(group)
        def rename(n):return ext[n.lower()]if n.lower()in ext else group+'.'+n.lower()
        new=[]
        for row in child[1:-1]:
            k=next(i for i,s in enumerate(row)if '='in s)-1 if row[0].startswith('X')else 3
            name='X_'+group+'_xd'+str(int(row[0][2:])).zfill(4)if row[0].startswith('XD')else row[0][0]+'_'+group+'_'+row[0].lower()
            new.append([name,*map(rename,row[1:k]),*row[k:]])
        assert len({r[0].lower()for r in new})==1122
        assert not any(n.lower().startswith(group+'.')for r in retained for n in r[1:]),'External reference into replaced divider interior'
        a,_=graph(prior,group,False);b,changes=graph(new,group,True)
        match=nx.algorithms.isomorphism.GraphMatcher(a,b,node_match=lambda x,y:x['color']==y['color'])
        assert match.is_isomorphic(),'Native divider intrinsic topology changed beyond four declared loads'
        device_map={k[1]:v[1]for k,v in match.mapping.items()if k[0]=='D'};assert len(device_map)==91
        proof.append(dict(group=group,old_counts=dict(X=91,R=379,C=646),new_counts=dict(X=91,R=382,C=649),
            normalized_load_changes=changes,intrinsic_topology_equivalent_except_four_load_lengths=True,
            device_bijection=device_map,ports=ext,comparison_dimension_quantization_m='1e-12',
            note='Resistor endpoints are interchangeable for native b=ps=0; HBT, MIM and body terminal roles remain ordered. No wire capacitors or resistor values are changed by this intrinsic-only comparison.'))
        mapping[group]=ext;added+=new
    records=retained+added
    assert len({r[0].lower()for r in records})==len(records)
    text='\n'.join(' '.join(r)for r in [old[0],*records,old[-1]])+'\n'
    return text,retained,added,proof
def verify(text,old,retained,added):
    rows=h.statements(text);before=h.statements(old)
    assert rows[0]==before[0]and rows[-1]==before[-1],'Parent boundary changed'
    actual={r[0].lower():r for r in rows[1:-1]};assert len(actual)==len(rows)-2,'Duplicated record'
    expected={r[0].lower():r for r in retained+added};assert set(actual)==set(expected),'Missing or unknown record'
    for n,row in expected.items():assert actual[n]==row,'Undeclared device/wire/connection change: '+n
    kinds=Counter(r[0][0].upper()for r in rows[1:-1]);assert kinds['X']==845 and kinds['R']+kinds['C']==8660
    assert len([r for r in rows[1:-1]if 'npn13g2'in [s.lower()for s in r]])==102
    return dict(devices=845,wires=8660,retained_records=len(retained),replaced_records=len(added),hbt=102,ports=rows[0][2:])
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],electrical_acquisition_passed=False,
        parent_geometry_updated=False,parent_interconnect_rc_revalidated=False,qualified_pex=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        old,receipt=reports.restore_report('pll-filter-parent-compose-9',38857275591,
            '05211617b84f8545bbaec4acfff8a6bc5fde01d795f00f96dd33256ca136a432',
            'a32351717b64940cf7a43d066e8cd9d37058973b38456bb09defb50c779fe3ec',OUT/'parent',('parent845.spice',))
        result['parent_source']=receipt
        assert old['status']=='PASS_C9_ACTUAL845_MODEL_EXACT_GRAPH_AND_COMPONENT_FAULTS_NOT_ELECTRICAL_ACCEPTANCE'
        assert sha(OUT/'parent/parent845.spice')==old['candidate_sha256']==PARENT_SHA
        new,receipt=reports.restore_report('pll-divider-load3p2-compose',38973446888,
            '08cdd360982945847f18cf452516e28e67c70744d285ce73ebec2a1e783937f7',
            '0003147fa7f884184b085d4735f163fd1137eb7db86a1c681129d59f692a10c8',OUT/'divider',('divider91-wire.spice','native.json'))
        result['divider_source']=receipt
        assert new['status']=='PASS_NATIVE91_ALL382R649C_DIVIDER_COMPOSITION_WITH28_FAULTS_NOT_ACQUISITION_OR_PHY_ACCEPTANCE'and new['source_unchanged']
        assert len(new['intrinsic_controls'])==11 and len(new['composition_controls'])==17
        assert all(c['rejected']for c in new['intrinsic_controls']+new['composition_controls'])
        assert sha(OUT/'divider/divider91-wire.spice')==new['model_sha256']==MODEL_SHA
        original=(OUT/'parent/parent845.spice').read_text();model=(OUT/'divider/divider91-wire.spice').read_text()
        text,kept,added,proof=prepare(original,model);target=OUT/'parent845.spice';target.write_text(text)
        result['positive']=verify(target.read_text(),original,kept,added);result['intrinsic_graphs']=proof;save()
        controls=[]
        for fault in ['missing_new_HBT','wrong_new_load','wrong_new_wire','private_body','swapped_input','wrong_retained_wire']:
            rows=h.statements(text);q=next(i for i,r in enumerate(rows)if r[0].startswith('X_xdiv1_')and 'npn13G2'in r)
            rr=next(i for i,r in enumerate(rows)if r[0].startswith('R_xdiv1_'))
            if fault=='missing_new_HBT':rows.pop(q)
            elif fault=='wrong_new_load':
                i=next(i for i,r in enumerate(rows)if r[0].startswith('X_xdiv1_')and 'rppd'in r and intrinsic(r)[2]['w']==Decimal('8e-6') and intrinsic(r)[2]['l'].quantize(Decimal('1e-12'))==Decimal('3.2e-6'))
                rows[i]=[('l=2.12u'if s.startswith('l=')else s)for s in rows[i]]
            elif fault=='wrong_new_wire':rows[rr][-1]='999'
            elif fault=='private_body':rows[q][4]='xdiv1.private_body'
            elif fault=='swapped_input':
                rows=[[('a_div1_clkn'if s=='a_div1_clkp'else'a_div1_clkp'if s=='a_div1_clkn'else s)for s in r]if r[0].startswith(('R_xdiv1_','C_xdiv1_'))else r for r in rows]
            else:
                i=next(i for i,r in enumerate(rows)if r[0].startswith('R_')and not r[0].startswith(('R_xdiv1_','R_xdiv2_')));rows[i][-1]='999'
            bad='\n'.join(' '.join(r)for r in rows)+'\n';assert bad!=text;(OUT/(fault+'.spice')).write_text(bad)
            try:verify(bad,original,kept,added)
            except AssertionError as e:controls.append(dict(fault=fault,rejected=True,reason=str(e)))
            else:raise AssertionError('Accepted modified parent: '+fault)
        assert len(controls)==6
        assert sha(OUT/'parent/parent845.spice')==PARENT_SHA and sha(OUT/'divider/divider91-wire.spice')==MODEL_SHA
        result.update(status='PASS_BOTH_DIVIDER_RC_MODELS_IN_PARENT_WITH_INTRINSIC_GRAPH_AND_SIX_FAULTS_REQUIRES_PARENT_GEOMETRY_AND_ACQUISITION',
            model_sha256=sha(target),controls=controls,source_unchanged=True,
            scope='Both divider blocks replaced entirely by newly extracted native91/382R649C models. All other parent records retained exactly. Eight declared W8 L2.12->3.2um loads normalized only for separate intrinsic graph proof. Parent intermacro geometry/RC is retained, not yet revalidated for new macro placement. Common body a_count_vss and independent wire_cref boundaries remain explicit. Full1us acquisition and all102HBT controls must be rebuilt from actual new instance IDs.')
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
