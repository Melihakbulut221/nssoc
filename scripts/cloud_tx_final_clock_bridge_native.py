#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind actual bridge terminals and finite contact model; wire RC is still required."""
import argparse,copy,json,math,os,re,sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as compact
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
TOP='nssoc_tx_final_clock_bridge_layout_v1'
MODEL_TOP='nssoc_tx_final_clock_bridge_native2_intrinsic_v1'
OUT=ROOT/'hw/soc/out/cloud-tx-final-clock-bridge-native'
ORDER={'rppd':['rppd_1','rppd_2','rppd_sub'],'ptap1':['TIE','WELL']}
PORTS=['sp','sn','sub']
PDK='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
SOURCE=dict(run=39373038910,head='17854122112562d943548e4e0ce181c51755e954',
 summary='ce7690a1472b72dbe0ffa96b38a242386887edffd7906834468426006ad1bc30',
 parts='223d79fc1287e54ec576214fd2140799cabefa0cfe60483bd2c7eb2675472620',
 gds='e02f760468950f7e095a3db511081c166ffe931dde3281b1ed1ec6802182fca3')
SELECTED=('layout/result.json','layout/'+TOP+'.gds','layout/schematic.cir','check/lvs/result.lvsdb','check/lvs_flat/result.lvsdb')

def export(source,out):
    import pya
    geometry=json.loads((source/'layout/result.json').read_text())
    L=pya.Layout();L.read(str(source/'layout'/(TOP+'.gds')));top=L.cell(TOP);assert top is not None and L.dbu==.001
    conductor=pya.Region(top.begin_shapes_rec(L.layer(67,0))).merged()
    modes={}
    for mode in ['lvs','lvs_flat']:
        database=source/('check/'+mode+'/result.lvsdb');lvs=pya.LayoutVsSchematic();lvs.read(str(database));c=lvs.netlist().circuit_by_name(TOP)
        assert c is not None and c.pin_count()==3
        layers=[i for i in lvs.layer_indexes()if (lvs.layer_by_index(i)^conductor).is_empty()];assert len(layers)==1
        names={};probes=[]
        for name,rect in geometry['ports'].items():
            q=pya.DBox.from_s(rect).center();point=pya.Point(round(q.x/L.dbu),round(q.y/L.dbu))
            n=lvs.probe_net(lvs.layer_by_index(layers[0]),point);assert n is not None
            key=str(n.cluster_id);assert key not in names;names[key]=name;probes.append(dict(name=name,cluster=key,point_dbu=[point.x,point.y]))
        assert set(names.values())==set(PORTS)
        rows=[]
        for d in c.each_device():
            cls=d.device_class();assert cls.name in ORDER;terms={}
            for t in cls.terminal_definitions():
                n=d.net_for_terminal(t.id());assert n is not None
                shapes=lvs.shapes_of_terminal(d.terminal_ref(t.id()));assert shapes
                terms[t.name]=dict(cluster=str(n.cluster_id),native_name=n.name,shapes=[dict(layer=int(i),bbox_dbu=str(r.bbox()),area_dbu2=r.area(),polygons=[str(p)for p in r.each()])for i,r in shapes.items()])
            assert set(terms)==set(ORDER[cls.name])
            rows.append(dict(id=int(d.id()),model=cls.name,parameters={p.name:d.parameter(p.id())for p in cls.parameter_definitions()},terminals=terms))
        assert Counter(r['model']for r in rows)==Counter(rppd=1,ptap1=1)
        r=next(r for r in rows if r['model']=='rppd')
        cluster=r['terminals']['rppd_sub']['cluster']
        assert cluster not in names
        names[cluster]='BULK'
        used={t['cluster']for r in rows for t in r['terminals'].values()}
        assert set(names)==used and len(names)==4
        for r in rows:
            for t in r['terminals'].values():t['logical_net']=names[t['cluster']]
        modes[mode]=dict(devices=rows,probes=probes,net_map=names,database_sha256=sha(database))
    (out/'native.json').write_text(json.dumps(dict(status='EXPORTED_NATIVE_BRIDGE_TERMINALS_NOT_RC_ACCEPTANCE',gds_sha256=sha(source/'layout'/(TOP+'.gds')),dbu=L.dbu,modes=modes),indent=2)+'\n')

def bind(record):
    assert set(record['modes'])=={'lvs','lvs_flat'},'Native extraction modes changed'
    assert record['gds_sha256']==SOURCE['gds'] and record['dbu']==.001,'Native geometry identity changed'
    bound={}
    for mode,data in record['modes'].items():
        rows=data['devices']
        assert len(rows)==2 and len({r['id'] for r in rows})==2,'Native device census changed'
        assert Counter(r['model'] for r in rows)==Counter(rppd=1,ptap1=1),'Native model census changed'
        names=data['net_map']
        assert len(names)==4 and set(names.values())==set(PORTS)|{'BULK'},'Physical net census changed'
        probes=data['probes']
        assert len(probes)==3 and {p['name'] for p in probes}==set(PORTS),'Public port probes changed'
        assert len({p['cluster'] for p in probes})==3,'Public port short'
        assert all(names[p['cluster']]==p['name'] for p in probes),'Public native cluster changed'
        for r in rows:
            p=r['parameters'];terms=r['terminals']
            assert set(terms)==set(ORDER[r['model']]),'Named native terminal changed'
            assert all(math.isfinite(v) for v in p.values()),'Nonfinite native parameter'
            for t in terms.values():
                assert t['cluster'] in names and t['logical_net']==names[t['cluster']],'Native terminal cluster changed'
                assert t['shapes'] and all(s['area_dbu2']>0 and s['polygons'] for s in t['shapes']),'Missing physical terminal geometry'
            n=[terms[t]['logical_net'] for t in ORDER[r['model']]]
            if r['model']=='rppd':
                assert set(p)=={'w','l','ps','b','m'},'Resistor parameter census changed'
                assert abs(p['w']-6)<1e-9 and abs(p['l']-1.2)<1e-9 and p['ps']==p['b']==0 and p['m']==1,'Bridge physical geometry changed'
                assert set(n[:2])=={'sp','sn'} and n[2]=='BULK','Bridge terminal mapping changed'
            else:
                assert n==['sub','BULK'],'Finite contact terminal mapping changed'
                assert set(p)=={'A','P'} and abs(p['A']-4)<1e-9 and abs(p['P']-8)<1e-9,'Finite contact geometry changed'
        assert sum(len(r['terminals']) for r in rows)==5
        bound[mode]=rows
    # Native IDs differ between deep and flat modes; compare actual semantic devices.
    def semantic(rows):
        return sorted((r['model'],json.dumps(r['parameters'],sort_keys=True),
                       tuple(sorted(nodes(r)[:2])) if r['model']=='rppd' else tuple(nodes(r)))
                      for r in rows)
    assert semantic(bound['lvs'])==semantic(bound['lvs_flat']),'Native deep/flat disagreement'
    return bound

def binding_controls(native,out):
    result=[]
    faults=['missing_contact','wrong_width','wrong_length','body_short','signal_short',
            'tap_area','missing_terminal_geometry','wrong_cluster','missing_mode','wrong_gds']
    for mode in ['lvs','lvs_flat']:
        for fault in faults:
            bad=copy.deepcopy(native);data=bad['modes'][mode];rows=data['devices']
            r=next(x for x in rows if x['model']=='rppd');tap=next(x for x in rows if x['model']=='ptap1')
            if fault=='missing_contact':rows.remove(tap)
            elif fault=='wrong_width':r['parameters']['w']=7
            elif fault=='wrong_length':r['parameters']['l']=1.6
            elif fault=='tap_area':tap['parameters']['A']=5
            elif fault in ['body_short','signal_short']:
                key='rppd_sub' if fault=='body_short' else 'rppd_1'
                dest='sub' if fault=='body_short' else r['terminals']['rppd_2']['logical_net']
                t=r['terminals'][key];t['logical_net']=dest
                t['cluster']=next(k for k,v in data['net_map'].items() if v==dest)
            elif fault=='missing_terminal_geometry':r['terminals']['rppd_1']['shapes']=[]
            elif fault=='wrong_cluster':r['terminals']['rppd_1']['cluster']=tap['terminals']['WELL']['cluster']
            elif fault=='missing_mode':del bad['modes'][mode]
            else:bad['gds_sha256']='0'*64
            (out/(mode+'-'+fault+'.json')).write_text(json.dumps(bad,indent=2)+'\n')
            try:bind(bad)
            except AssertionError as error:result.append(dict(mode=mode,fault=fault,rejected=True,reason=str(error)))
            else:raise AssertionError('Accepted actual bridge binding corruption '+mode+':'+fault)
    assert len(result)==20
    return result

def resistance(r,tech):
    p=r['parameters']
    return 1/(Decimal(str(p['A']))*Decimal('1e-12')/compact.number(tech['ptap1_raspec'])+
              Decimal(str(p['P']))*Decimal('1e-6')/compact.number(tech['ptap1_rpspec']))

def nodes(r):return [r['terminals'][t]['logical_net']for t in ORDER[r['model']]]
def build(rows,tech,top):
    lines=['* Actual native clock bridge two-device intrinsic model; not wire RC or qualification.','.subckt '+top+' '+' '.join(PORTS)];bindings=[]
    for r in rows:
        model=r['model'];params={'R':str(resistance(r,tech))}if model=='ptap1'else compact.model_params(r,tech)
        name='XD'+str(r['id']);n=nodes(r);lines.append(' '.join([name,*n,model,*[k+'='+v for k,v in params.items()]]))
        bindings.append(dict(instance=name,native_id=r['id'],model=model,named_terminal_order=ORDER[model],nodes=n,native_parameters=r['parameters'],compact_parameters=params))
    return '\n'.join(lines+['.ends '+top,'']),bindings

def verify(text,rows,tech,top):
    lines=compact.statements(text);assert lines[0]==['.subckt',top,*PORTS]and lines[-1]==['.ends',top],'Clock wrapper changed'
    actual={l[0]:l for l in lines[1:-1]};expected={'XD'+str(r['id']):r for r in rows}
    assert len(actual)==len(lines)-2==len(expected)==2 and set(actual)==set(expected),'Clock device missing or duplicated'
    for name,r in expected.items():
        model=r['model'];p=r['parameters'];n=nodes(r);line=actual[name]
        assert line[1:len(n)+1]==n,'Named native clock terminal changed'
        assert line[len(n)+1]==model,'Native compact model changed'
        words=line[len(n)+2:];params={k:compact.number(v)for k,v in (w.split('=',1)for w in words)}
        assert len(params)==len(words),'Duplicate compact parameter'
        if model=='rppd':
            assert set(params)=={'w','l','ps','b','m','sw_et'},'Resistor parameter census changed'
            for k in ['w','l','ps']:assert abs(params[k]-Decimal(str(p[k]))*Decimal('1e-6'))<=Decimal('1e-20'),'Resistor native geometry changed'
            assert params['b']==p['b']==0 and params['m']==p['m']==params['sw_et']==1,'Resistor multiplier/body/self-heating changed'
        else:
            assert model=='ptap1'and set(params)=={'R'},'Finite body contact changed'
            g=Decimal(str(p['A']))*Decimal('1e-12')/compact.number(tech['ptap1_raspec'])+Decimal(str(p['P']))*Decimal('1e-6')/compact.number(tech['ptap1_rpspec'])
            assert abs(params['R']*g-1)<=Decimal('1e-26'),'Finite body contact conductance changed'
    return dict(devices=2,resistors=1,finite_contacts=1,ports=PORTS)

def model_controls(text,rows,tech,top,out):
    result=[]
    faults=['missing_resistor','wrong_width','wrong_length','body_short','signal_short',
            'missing_contact','changed_contact_R','missing_resistor_ps','disabled_self_heating','duplicate_resistor']
    for fault in faults:
        lines=text.splitlines()
        r=next(i for i,l in enumerate(lines) if ' rppd ' in l)
        tap=next(i for i,l in enumerate(lines) if ' ptap1 ' in l)
        if fault=='missing_resistor':del lines[r]
        elif fault=='wrong_width':lines[r]=re.sub(r'w=\S+','w=7u',lines[r])
        elif fault=='wrong_length':lines[r]=re.sub(r'l=\S+','l=1.6u',lines[r])
        elif fault=='missing_contact':del lines[tap]
        elif fault=='changed_contact_R':lines[tap]=re.sub(r'R=\S+','R=1',lines[tap])
        elif fault=='missing_resistor_ps':lines[r]=re.sub(r' ps=\S+','',lines[r])
        elif fault=='disabled_self_heating':lines[r]=lines[r].replace('sw_et=1','sw_et=0')
        elif fault=='duplicate_resistor':lines.insert(r,lines[r])
        else:
            words=lines[r].split()
            if fault=='body_short':words[3]='sub'
            else:words[1]=words[2]
            lines[r]=' '.join(words)
        bad='\n'.join(lines)+'\n';(out/(fault+'.spice')).write_text(bad)
        try:verify(bad,rows,tech,top)
        except AssertionError as error:result.append(dict(fault=fault,rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted actual bridge model corruption '+fault)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--export',action='store_true');a=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    source=OUT/'source'
    if a.export:export(source,OUT);return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
                qualified_pex=False,qualified_substrate=False,wire_rc_extracted=False,
                electrically_validated=False,serial_phy_complete=False,mainchip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        protected=json.loads((ROOT/'scripts/tx-final-clock-bridge-native-sources.json').read_text())
        assert all(sha(ROOT/p)==h for p,h in protected.items()),'Native helper source changed'
        prior,proof=reports.restore_report('tx-final-clock-bridge',SOURCE['run'],SOURCE['summary'],SOURCE['parts'],source,SELECTED)
        result['source']=proof
        assert prior['source_head']==SOURCE['head'] and prior['source_unchanged']
        assert prior['status']=='PASS_NATIVE_CLOCK_BRIDGE_PHYSICAL_GATES_NOT_ELECTRICAL_OR_PHY_ACCEPTANCE'
        steps=prior['physical_checks']['steps']
        assert set(steps)=={'drc','lvs','lvs_flat','wrong_width','wrong_length','missing_resistor','signal_open','signal_short','offgrid'}
        assert all(s['status']==('PASS' if n in ['drc','lvs','lvs_flat'] else 'REJECTED_EXPECTED_FAULT') for n,s in steps.items())
        assert steps['drc']['measurement']['markers']==0 and steps['drc']['measurement']['category_count']==560
        assert sha(source/'layout'/(TOP+'.gds'))==SOURCE['gds']
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256']
        sys.path.insert(0,str(ROOT/'hw/soc/flow'));from check_pcie_rx_cell import execute
        result['export']=execute([app,'python',Path(__file__).resolve(),'--export'],OUT,'export');save()
        assert result['export']['returncode']==0,(OUT/'export.log').read_text()[-10000:]
        native=json.loads((OUT/'native.json').read_text());result['bindings']=bind(native)
        result['binding_controls']=binding_controls(native,OUT)
        models=OUT/'pdk'
        pins={p:h for p,h in compact.MODEL_PINS.items() if p.endswith(('resistors_mod.lib','sg13g2_tech.json','utility_functions.py'))}
        assert len(pins)==3
        for path,digest in pins.items():
            target=models/path;target.parent.mkdir(parents=True,exist_ok=True)
            fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+PDK+'/ihp-sg13g2/'+path,digest,target)
        res=(models/'libs.tech/ngspice/models/resistors_mod.lib').read_text()
        assert len(re.findall(r'^\.subckt\s+rppd\s+1\s+2\s+bn\s*$',res,re.M|re.I))==1
        tap=re.search(r'^\.subckt\s+ptap1\s+1\s+2\s*\n(.*?)^\.ends\s+ptap1',res,re.M|re.S|re.I);assert tap
        assert [line.strip() for line in re.findall(r'^R\S+\s+1\s+2\s+R=R\s*$',tap[1],re.M)]==['R1 1 2 R=R']
        tech=json.loads((models/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        rows=native['modes']['lvs_flat']['devices']
        text,bindings=build(rows,tech,MODEL_TOP);model=OUT/'bridge2.spice';model.write_text(text)
        result.update(intrinsic=verify(model.read_text(),rows,tech,MODEL_TOP),
                      model_bindings=bindings,model_controls=model_controls(text,rows,tech,MODEL_TOP,OUT))
        assert len(result['model_controls'])==10 and all(c['rejected'] for c in result['model_controls'])
        assert all(sha(source/p)==prior['outputs'][p] for p in SELECTED)
        assert all(sha(models/p)==h for p,h in pins.items()) and all(sha(ROOT/p)==h for p,h in protected.items())
        result.update(status='PASS_NATIVE_BRIDGE2_TERMINALS_FINITE_CONTACT_MODEL_AND_30_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE',
                      gds_sha256=SOURCE['gds'],native_sha256=sha(OUT/'native.json'),model_sha256=sha(model),
                      models=dict(commit=PDK,hashes=pins),source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
