#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind all8088 native raw devices, named MOS junctions and65 distinct body nets.

This is the physically assembled parent, not64 ideal-connected driver models.
Wire RC is deliberately absent until the independent native RC stage passes.
"""
import argparse,copy,json,os,re,subprocess
from collections import Counter
from decimal import Decimal
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as model
import cloud_tx_driver_localpins_intrinsic as driver
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-tx-output8088-power128return64-intrinsic'
TOP='nssoc_tx_output8088_parent_v1';MODEL='nssoc_tx_output8088_intrinsic_v1'
CENSUS=dict(npn13G2=593,sg13_hv_nmos=2560,sg13_lv_nmos=1408,sg13_lv_pmos=1408,rppd=504,rsil=2,ptap1=1485,ntap1=128)
ORDER=dict(npn13G2=['C','B','E','S'],sg13_hv_nmos=['D','G','S','B'],sg13_lv_nmos=['D','G','S','B'],sg13_lv_pmos=['D','G','S','B'],rppd=['rppd_1','rppd_2','rppd_sub'],rsil=['rsil_1','rsil_2','rsil_sub'],ptap1=['TIE','WELL'],ntap1=['TIE','WELL'])
def native_export():
    import pya
    path=OUT/'source/source/source/flat_lvs/result.lvsdb'
    db=pya.LayoutVsSchematic();db.read(str(path));c=db.netlist().top_circuit()
    assert c.name==TOP and c.pin_count()==165
    anchors=json.loads((OUT/'source/anchors.json').read_text())
    rows={(r['device'],r['terminal']):r for r in anchors['rows']};assert len(rows)==28620
    geometry=json.loads((OUT/'source/source/native01/result.json').read_text())
    coverage={r['native_cluster']:r for r in geometry['native_net_coverage']if r['device_terminals']}
    assert len(coverage)==768
    devices=[];used=set()
    for d in c.each_device():
        cls=d.device_class();terms={}
        for t in cls.terminal_definitions():
            n=d.net_for_terminal(t.id());w=rows[d.id(),t.name]
            assert w['model']==cls.name and w['native_cluster']==n.cluster_id
            assert dict(device=d.id(),model=cls.name,terminal=t.name)in coverage[n.cluster_id]['device_terminals']
            terms[t.name]=dict(cluster=n.cluster_id,native_name=n.name,disposition=w['disposition'])
            if 'reference_label'in w:terms[t.name]['reference_label']=w['reference_label']
            used.add((d.id(),t.name))
        assert set(terms)==set(ORDER[cls.name])
        devices.append(dict(id=d.id(),model=cls.name,parameters={p.name:d.parameter(p.id())for p in cls.parameter_definitions()},terminals=terms))
    assert Counter(d['model']for d in devices)==CENSUS and used==set(rows)
    ports=[dict(name=p.name(),cluster=c.net_for_pin(p.id()).cluster_id)for p in c.each_pin()]
    assert len(ports)==len({p['name'].lower()for p in ports})==len({p['cluster']for p in ports})==165
    assert set(p['name']for p in ports)==set(geometry['native_ports'])
    body={t['cluster']for d in devices for t in d['terminals'].values()if t['disposition']=='RETAINED_FINITE_CONTACT_COMMON_BODY_NO_SPREADING_R'}
    wire={t['cluster']for d in devices for t in d['terminals'].values()if t['disposition']=='ACTUAL_TERMINAL_METAL_REFERENCE_WITH_UNMODELED_DEVICE_ACCESS_R'}
    assert len(body)==65 and len(wire)==703 and not body&wire and body|wire==set(coverage)
    assert all(not coverage[n]['metal_area_dbu2']and not coverage[n]['public_ports']for n in body)
    assert all(p['cluster']in wire for p in ports)
    bulk={d['terminals']['B']['cluster']for d in devices if d['model']in ('sg13_lv_nmos','sg13_hv_nmos')}
    hbt_body={d['terminals']['S']['cluster']for d in devices if d['model']=='npn13G2'}
    wells={d['terminals']['B']['cluster']for d in devices if d['model']=='sg13_lv_pmos'}
    assert len(bulk)==1 and hbt_body==bulk and len(wells)==64 and not wells&bulk and body==wells|bulk
    result=dict(status='EXPORTED_ALL8088_NATIVE_PARAMS_AND28620_TERMINALS_NOT_ELECTRICAL_ACCEPTANCE',devices=devices,ports=ports,body_clusters=sorted(body),wire_clusters=sorted(wire),census=CENSUS,counts=dict(devices=8088,terminals=28620,ports=165,body_nets=65,wire_nets=703,mos_fingers=5376),input_sha256={str(path):sha(path),str(OUT/'source/anchors.json'):sha(OUT/'source/anchors.json'),str(OUT/'source/source/native01/result.json'):sha(OUT/'source/source/native01/result.json')})
    (OUT/'native.json').write_text(json.dumps(result,indent=2)+'\n')
def decimal(v):return Decimal(str(v))
def parameters(d,tech):
    p=d['parameters'];kind=d['model']
    if kind.startswith('sg13_'):
        assert set(p)=={'L','W','AS','AD','PS','PD','rfmode'}
        assert all(decimal(p[k]).is_finite()and decimal(p[k])>0 for k in ('L','W','AS','AD','PS','PD'))and p['rfmode']==0
        return {k.lower():str(v)+('p'if k in ('AS','AD')else'u'if k in ('L','W','PS','PD')else'')for k,v in p.items()}|dict(ng='1',m='1')
    if kind=='npn13G2':
        assert set(p)=={'Nx','we','le','m'}and p['m']==1
        assert p['Nx']==int(p['Nx'])and p['Nx']>0 and decimal(p['we'])==Decimal('.07')and decimal(p['le'])==Decimal('.9')
        return dict(nx=str(int(p['Nx'])),we=str(p['we'])+'u',le=str(p['le'])+'u')
    if kind in ('rppd','rsil'):
        assert set(p)=={'w','l','ps','b','m'}and p['b']==0 and p['m']==1
        # Native504rppd and2rsil non-meander resistors have b=0 and ps=0. The pinned
        # PDK computes leff=(b+1)*l+(2/kappa*weff+ps)*b; no bend spacing applies.
        assert all(decimal(p[k])>0 for k in ('w','l'))and p['ps']==0
        return {k:str(p[k])+'u'for k in ('w','l','ps')}|dict(b='0',m='1',sw_et='1')
    assert kind in ('ptap1','ntap1')and set(p)=={'A','P'}and p['A']>0 and p['P']>0
    return {'R':str(driver.resistance(d,tech))}
def build(native,tech):
    public={p['cluster']:p['name']for p in native['ports']}
    clusters={t['cluster']for d in native['devices']for t in d['terminals'].values()}
    nodes={n:public.get(n,'n_'+str(n))for n in clusters}
    assert len(nodes)==len({v.lower()for v in nodes.values()})==768
    ports=[p['name']for p in native['ports']]
    lines=['* Whole8088-device native intrinsic model. Requires actual whole-parent RC and loaded acceptance.','.subckt '+MODEL+' '+' '.join(ports)]
    records=[]
    for d in native['devices']:
        order=ORDER[d['model']];ns=[nodes[d['terminals'][t]['cluster']]for t in order]
        params=parameters(d,tech);compact='npn13g2'if d['model']=='npn13G2'else d['model'];name='XD'+str(d['id'])
        lines.append(' '.join([name,*ns,compact,*[k+'='+v for k,v in params.items()]]))
        records.append(dict(instance=name,native_id=d['id'],native_model=d['model'],model=compact,named_terminal_order=order,nodes=ns,parameters=params,terminals=d['terminals']))
    lines+=['.ends '+MODEL,'']
    return '\n'.join(lines),dict(devices=records,ports=ports,node_map=nodes,body_map={str(n):nodes[n]for n in native['body_clusters']},census=CENSUS,counts=native['counts'])
def verify(text,native,tech):
    rows=model.statements(text);ports=[p['name']for p in native['ports']]
    assert rows[0]==['.subckt',MODEL,*ports]and rows[-1]==['.ends',MODEL]
    actual={r[0]:r for r in rows[1:-1]};assert len(actual)==len(rows)-2==8088
    assert set(actual)=={'XD'+str(d['id'])for d in native['devices']}
    public={p['cluster']:p['name']for p in native['ports']}
    node=lambda n:public.get(n,'n_'+str(n))
    for d in native['devices']:
        order=ORDER[d['model']];row=actual['XD'+str(d['id'])];kind=d['model'];p=d['parameters']
        assert row[1:1+len(order)]==[node(d['terminals'][t]['cluster'])for t in order],'Native terminal/body identity changed'
        assert row[1+len(order)]==('npn13g2'if kind=='npn13G2'else kind),'Compact model changed'
        words=row[2+len(order):];params={k:model.number(v)for k,v in(x.split('=',1)for x in words)}
        assert len(params)==len(words),'Duplicate parameters'
        if kind.startswith('sg13_'):
            assert set(params)=={k.lower()for k in p}|{'ng','m'}
            assert params['ng']==params['m']==1
            for k,v in p.items():
                unit=Decimal('1e-12')if k in ('AS','AD')else Decimal('1e-6')if k in ('L','W','PS','PD')else Decimal(1)
                assert params[k.lower()]==decimal(v)*unit,'MOS native junction/geometry changed'
        elif kind=='npn13G2':
            assert set(params)=={'nx','we','le'}
            assert params['nx']==p['Nx']and params['we']==decimal(p['we'])*Decimal('1e-6')and params['le']==decimal(p['le'])*Decimal('1e-6')
        elif kind in ('rppd','rsil'):
            assert set(params)=={'w','l','ps','b','m','sw_et'}
            assert all(params[k]==decimal(p[k])*Decimal('1e-6')for k in ('w','l','ps'))
            assert params['b']==0 and params['m']==params['sw_et']==1
        else:
            assert set(params)=={'R'}
            conductance=decimal(p['A'])*Decimal('1e-12')/model.number(tech[kind+'_raspec'])+decimal(p['P'])*Decimal('1e-6')/model.number(tech[kind+'_rpspec'])
            assert abs(params['R']*conductance-1)<=Decimal('1e-26')
    return True
def controls(text,native,tech):
    original=model.statements(text);out=[]
    for name in ('missing_mos','wrong_mos_width','wrong_mos_junction','swap_drain_source','swap_gate_source','missing_rfmode','aggregate_finger_multiplier','wrong_hbt_size','swap_hbt_collector_emitter','missing_hbt','wrong_resistor_width','missing_contact','changed_contact_R','body_short_to_supply','cross_driver_well_short'):
        rows=copy.deepcopy(original)
        kind='npn13g2'if'hbt'in name else'rppd'if name=='wrong_resistor_width'else'ptap1'if'contact'in name else'sg13_lv_pmos'if name=='cross_driver_well_short'else'sg13_lv_nmos'
        i=next(i for i,r in enumerate(rows)if kind in r)
        if name.startswith('missing_')and name!='missing_rfmode':del rows[i]
        elif name.startswith('swap_'):
            x,y=(1,3)if name in ('swap_drain_source','swap_hbt_collector_emitter')else(2,3)
            assert rows[i][x]!=rows[i][y];rows[i][x],rows[i][y]=rows[i][y],rows[i][x]
        elif name=='body_short_to_supply':assert rows[i][4]!='avss';rows[i][4]='avss'
        elif name=='cross_driver_well_short':
            other=next(r for r in rows if kind in r and r[4]!=rows[i][4]);rows[i][4]=other[4]
        else:
            key={'wrong_mos_width':'w','wrong_mos_junction':'ad','missing_rfmode':'rfmode','aggregate_finger_multiplier':'m','wrong_hbt_size':'nx','wrong_resistor_width':'w','changed_contact_R':'R'}[name]
            j=next(j for j,s in enumerate(rows[i])if s.startswith(key+'='))
            if name=='missing_rfmode':del rows[i][j]
            else:rows[i][j]=key+'=999'
        changed='\n'.join(' '.join(r)for r in rows)+'\n'
        try:verify(changed,native,tech)
        except (AssertionError,ValueError):out.append(dict(name=name,rejected=True,sha256=__import__('hashlib').sha256(changed.encode()).hexdigest()))
        else:raise AssertionError('Accepted '+name)
    assert len(out)==15
    for name in ('wrong_rsil_length','missing_rsil_spacing','rsil_self_heating_disabled','rsil_body_short_to_avss'):
        rows=copy.deepcopy(original);i=next(i for i,r in enumerate(rows)if 'rsil'in r)
        if name=='rsil_body_short_to_avss':
            assert rows[i][3]!='avss';rows[i][3]='avss'
        else:
            key={'wrong_rsil_length':'l','missing_rsil_spacing':'ps','rsil_self_heating_disabled':'sw_et'}[name]
            j=next(j for j,x in enumerate(rows[i])if x.startswith(key+'='))
            if name=='missing_rsil_spacing':del rows[i][j]
            else:rows[i][j]=key+('=1u'if key=='l'else'=0')
        changed='\n'.join(' '.join(r)for r in rows)+'\n'
        assert changed!=text
        try:verify(changed,native,tech)
        except (AssertionError,ValueError):out.append(dict(name=name,rejected=True,sha256=__import__('hashlib').sha256(changed.encode()).hexdigest()))
        else:raise AssertionError('Accepted '+name)
    assert len(out)==19;return out
def main():
    p=argparse.ArgumentParser();p.add_argument('--native-export',action='store_true');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    delta=json.loads((ROOT/'scripts/tx-output8088-power128return64-intrinsic-method.json').read_text())
    original=(ROOT/delta['baseline_path']).read_text()
    assert sha(ROOT/delta['baseline_path'])==delta['baseline_sha256']and sha(Path(__file__))==delta['candidate_sha256']
    pieces=[];cursor=0
    for change in delta['changes']:
        assert cursor<=change['start']<=change['end']<=len(original)
        pieces.extend([original[cursor:change['start']],change['replacement']]);cursor=change['end']
    pieces.append(original[cursor:]);assert ''.join(pieces)==Path(__file__).read_text()
    if a.native_export:native_export();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,qualified_substrate=False,wire_rc_included=False,native_simulation_passed=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128return64-native-anchors-pass-20261023.json').read_text())
        assert pin['run']==39898478620 and pin['summary_sha256']=='350eabcb2b1014a6fad1c76512800b51392906d4c2a859697562f58cf829ce0b'
        selected=['anchors.json','source/native01/result.json','source/source/flat_lvs/result.lvsdb']
        prior,proof=reports.restore_report('tx-output8088-power128return64-native-anchors',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior['sources_unchanged']and prior['status'].startswith('PASS_ALL28620')
        r['physical_source']=proof
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        with(OUT/'native-export.log').open('w')as log:code=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native-export'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r['native_returncode']=code;save()
        if code:print((OUT/'native-export.log').read_text(errors='replace')[-14000:])
        assert code==0
        native=json.loads((OUT/'native.json').read_text())
        for path,digest in driver.PINS.items():
            target=OUT/'pdk'/path;target.parent.mkdir(parents=True,exist_ok=True)
            fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+driver.PDK+'/ihp-sg13g2/'+path,digest,target)
        driver.validate_model_libraries(OUT/'pdk')
        tech=json.loads((OUT/'pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        resistors=[d for d in native['devices']if d['model']=='rppd']
        assert len(resistors)==504 and all(d['parameters']['b']==d['parameters']['ps']==0 for d in resistors)
        r['native_rppd_spacing']=dict(devices=504,b=0,ps_um=0,geometry_preserved=True)
        loads=[d for d in native['devices']if d['model']=='rsil']
        assert len(loads)==2 and all(decimal(d['parameters']['w'])==Decimal(10)and decimal(d['parameters']['l'])==Decimal('70.215')and d['parameters']['ps']==d['parameters']['b']==0 and d['parameters']['m']==1 for d in loads)
        r['native_output_rsil']=dict(devices=2,w_um=10,l_um='70.215',ps_um=0,b=0,m=1,self_heating=True)

        bad=copy.deepcopy(resistors[0]);bad['parameters']['ps']=-1
        try:parameters(bad,tech)
        except AssertionError:r['negative_spacing_control']=dict(rejected=True)
        else:raise AssertionError('Accepted negative native resistor spacing')
        text,binding=build(native,tech);verify(text,native,tech)
        r['controls']=controls(text,native,tech)
        (OUT/'output8088-intrinsic.spice').write_text(text);(OUT/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
        r['model_sha256']=sha(OUT/'output8088-intrinsic.spice');r['binding_sha256']=sha(OUT/'binding.json');r['counts']=native['counts'];r['models']=dict(commit=driver.PDK,hashes=driver.PINS)
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)and all(sha(OUT/'pdk'/p)==v for p,v in driver.PINS.items())
        r.update(status='PASS_FULL8088_NATIVE_INTRINSIC_BINDING_65_BODY_NETS_AND19_CONTROLS_REQUIRES_WHOLE_WIRE_RC_AND_LOADED_WAVES',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
