#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind all actual PD476 devices/1382 terminals to pinned native PDK models."""
import argparse,copy,json,math,os,re,shutil,subprocess,tarfile
from collections import Counter
from decimal import Decimal
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_cdr_parallel_v3_native_models as models
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-follower-v31-binding'
TOP='nssoc_cdr_pd476_follower_v23';MODEL='nssoc_cdr_pd476_follower_sink_v31_compact'
CENSUS=dict(npn13G2=120,sg13_lv_nmos=46,rppd=98,cap_cmim=7,ptap1=205)

def native_export():
    import pya
    db=pya.LayoutVsSchematic();path=OUT/'inputs/parent/physical/lvs_flat/result.lvsdb';db.read(str(path));c=db.netlist().top_circuit()
    assert c.name==TOP and c.pin_count()==25
    devices=[]
    for d in c.each_device():
        dc=d.device_class();devices.append(dict(native_id=d.id(),model=dc.name,terminals={t.name:d.net_for_terminal(t.id()).name for t in dc.terminal_definitions()},parameters={p.name:d.parameter(p.id())for p in dc.parameter_definitions()}))
    assert Counter(x['model']for x in devices)==CENSUS
    (OUT/'native-devices.json').write_text(json.dumps(dict(devices=devices,inputs={str(path):sha(path)}),indent=2)+'\n')

def geometry_readback_matches(exact,observed):
    # Compare to the actual IEEE-754 value, not its rounded JSON spelling.
    # The bound remains exactly one binary ULP; native SPICE stays authoritative.
    return math.isfinite(observed) and abs(exact-Decimal.from_float(observed))<=Decimal.from_float(math.ulp(observed))

def geometry_readback_controls():
    accepted=[('4.8',4.8),('4.8',4.800000000000001),('23.04',23.040000000000003)]
    rejected=[('4.8',4.800000000000002),('4.8',4.80000001),('23.04',23.04000000000001)]
    assert all(geometry_readback_matches(Decimal(a),b)for a,b in accepted)
    assert all(not geometry_readback_matches(Decimal(a),b)for a,b in rejected)
    return dict(positive=accepted,rejected=rejected,bound='one actual binary ULP',canonical_geometry='exact native extracted SPICE')

def build(native_text,devices,geometry,tech,ports_expected):
    statements=models.statements(native_text)
    assert statements[0][:2]==['.SUBCKT',TOP]and statements[-1]==['.ENDS',TOP]
    ports=statements[0][2:];assert len(ports)==len(set(ports))==25 and set(ports)==set(ports_expected)
    native={}
    for row in statements[1:-1]:
        match=re.fullmatch(r'[QRCM]\$(\d+)',row[0]);assert match
        key=int(match[1]);assert key not in native;native[key]=row
    assert set(native)=={d['native_id']for d in devices}==set(range(1,477))
    assert Counter(d['model']for d in devices)==CENSUS
    geom={d['native_id']:d for d in geometry['devices']};assert set(geom)==set(native)
    node_map={n:n if n in ports else 'n_'+n.removeprefix('$')for d in devices for n in d['terminals'].values()}
    assert len(node_map)==len({n.lower()for n in node_map.values()})
    bindings=[];out=['* Native PD476 compact model; metal RC and substrate spreading not included.','.subckt '+MODEL+' '+' '.join(ports)]
    mos_widths=Counter();hbt_sizes=Counter()
    for d in devices:
        kind=d['model'];order=models.NATIVE_ORDER[kind];line=native[d['native_id']];g=geom[d['native_id']]
        assert g['model']==kind and g['parameters']==d['parameters']
        assert {t['name']:t['net']for t in g['terminals']}==d['terminals']
        assert set(d['terminals'])==set(order) and line[len(order)+1]==kind
        assert [n.removeprefix('\\')for n in line[1:len(order)+1]]==[d['terminals'][t]for t in order]
        fields=line[len(order)+2:];params=dict(x.split('=')for x in fields)
        assert len(params)==len(fields)and set(params)==set(d['parameters'])
        canonical={}
        for k,v in d['parameters'].items():
            exponent=-12 if k in ('A','AS','AD')else -6 if k in ('w','l','ps','we','le','P','L','W','PS','PD')else 0
            value=models.number(params[k])/Decimal(10)**exponent
            assert geometry_readback_matches(value,v),(d['native_id'],k,value,v)
            canonical[k]=value
        if kind=='sg13_lv_nmos':mos_widths[canonical['W']]+=1
        if kind=='npn13G2':hbt_sizes[canonical['Nx']]+=1
        model_device=dict(d,parameters=canonical)
        sim={k.lower():v for k,v in models.model_params(model_device,tech).items()}
        if kind=='npn13G2':assert canonical['Nx']==int(canonical['Nx'])and 1<=int(canonical['Nx'])<=10 and models.number(sim['we'])==Decimal('0.07e-6')and models.number(sim['le'])==Decimal('0.9e-6')
        nets=[node_map[d['terminals'][t]]for t in models.MODEL_ORDER[kind]]
        model='npn13g2'if kind=='npn13G2'else kind;name=f'XD{d["native_id"]:04d}'
        row=dict(instance=name,native_id=d['native_id'],model=model,native_model=kind,native_terminal_order=order,compact_model_order=models.MODEL_ORDER[kind],native_nodes=d['terminals'],compact_nodes=nets,parameters=sim,native_parameters={k:str(v)for k,v in canonical.items()})
        out.append(' '.join([name,*nets,model,*[k+'='+v for k,v in sim.items()]]));bindings.append(row)
    assert mos_widths=={Decimal(8):8,Decimal(32):2,Decimal(36):32,Decimal(64):4},mos_widths
    assert sum(len(d['native_nodes'])for d in bindings)==1382
    return '\n'.join(out+['.ends '+MODEL,'']),dict(native_ports=ports,devices=bindings,node_map=node_map,census=CENSUS,native_mos_width_census_um={format(w,'f'):n for w,n in mos_widths.items()})

def verify(text,binding):
    rows=models.statements(text);assert rows[0]==['.subckt',MODEL,*binding['native_ports']]and rows[-1]==['.ends',MODEL]
    seen={}
    for row in rows[1:-1]:
        assert row[0]not in seen;seen[row[0]]=row
    assert set(seen)=={x['instance']for x in binding['devices']}
    for device in binding['devices']:
        row=seen[device['instance']];n=len(device['compact_model_order'])
        assert row[1:n+1]==device['compact_nodes'] and row[n+1]==device['model']
        params=dict(x.split('=')for x in row[n+2:]);assert len(params)==len(row[n+2:])and set(params)==set(device['parameters'])
        assert all(models.number(params[k])==models.number(v)for k,v in device['parameters'].items())
    return True

def controls(text,binding):
    verify(text,binding);original=models.statements(text);out=[]
    for name in ('missing_mim','wrong_mim_width','swapped_mim_plates','wrong_hbt_size','swapped_hbt_base_emitter','wrong_resistor_width','missing_contact','short_sub_to_avss'):
        rows=copy.deepcopy(original)
        kind='cap_cmim'if name in ('missing_mim','wrong_mim_width','swapped_mim_plates')else'npn13g2'if'hbt'in name else'rppd'if name=='wrong_resistor_width'else'ptap1'
        device=next(d for d in binding['devices']if d['model']==kind);i=next(i for i,r in enumerate(rows)if r[0]==device['instance'])
        if name.startswith('missing_'):del rows[i]
        elif name in ('wrong_mim_width','wrong_resistor_width','wrong_hbt_size'):
            key='nx'if name=='wrong_hbt_size'else'w';j=next(j for j,x in enumerate(rows[i])if x.startswith(key+'='));rows[i][j]=key+'=999'
        elif name=='swapped_mim_plates':rows[i][1],rows[i][2]=rows[i][2],rows[i][1];assert rows[i][1]!=rows[i][2]
        elif name=='swapped_hbt_base_emitter':rows[i][2],rows[i][3]=rows[i][3],rows[i][2];assert rows[i][2]!=rows[i][3]
        else:
            assert rows[i][1]=='sub';rows[i][1]='avss'
        mutated='\n'.join(' '.join(r)for r in rows)+'\n'
        try:verify(mutated,binding)
        except (AssertionError,ValueError):out.append(dict(name=name,rejected=True))
        else:raise AssertionError('Accepted '+name)
    assert len(out)==8
    for name in ('missing_mos','wrong_mos_width','swapped_mos_gate_source','mos_body_short'):
        rows=copy.deepcopy(original);device=next(d for d in binding['devices']if d['model']=='sg13_lv_nmos')
        i=next(i for i,r in enumerate(rows)if r[0]==device['instance'])
        if name=='missing_mos':del rows[i]
        elif name=='wrong_mos_width':
            j=next(j for j,v in enumerate(rows[i])if v.startswith('w='));rows[i][j]='w=999u'
        elif name=='swapped_mos_gate_source':
            assert rows[i][2]!=rows[i][3];rows[i][2],rows[i][3]=rows[i][3],rows[i][2]
        else:
            assert rows[i][4]!=rows[i][3];rows[i][4]=rows[i][3]
        mutated='\n'.join(' '.join(r)for r in rows)+'\n'
        try:verify(mutated,binding)
        except (AssertionError,ValueError):out.append(dict(name=name,rejected=True))
        else:raise AssertionError('Accepted '+name)
    assert len(out)==12;return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--native-export',action='store_true');a=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    if a.native_export:native_export();return
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT;r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_simulation_passed=False,qualified_pex=False,wire_rc_included=False,full_phy_accepted=False,closed_loop=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def restore(receipt,dest):
        packed=OUT/'restore.tar.gz';fetch(receipt['url'],receipt['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(dest,filter='data')
        packed.unlink()
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-follower-v31-wire-inputs-pass-20261022.json').read_text())
        selected=['wire/device-locations01.json','parent/layout/result.json','parent/layout/schematic.cir',*['parent/physical/lvs_flat/'+n for n in ('extracted.cir','audit.json','result.lvsdb')]]
        prior,proof=reports.restore_report('cdr-follower-v31-wire-inputs',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'inputs',selected)
        assert prior['status']==pin['status']and prior['source_head']==pin['source_head']and prior['sources_unchanged'];r['physical_source']=proof
        layout=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());restore(layout['receipt'],ROOT)
        lm=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in lm['files'].items())
        electrical=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-input-20261013.json').read_text());m=OUT/'model-inputs';m.mkdir();restore(electrical['receipt'],m)
        mm=json.loads((m/'manifest.json').read_text());assert all(sha(m/n)==v['sha256']for n,v in mm['files'].items())
        target=ROOT/'pdk/libs.tech/ngspice/models';target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(m/'models',target)
        for rel,digest in models.MODEL_PINS.items():assert sha(ROOT/'pdk'/rel)==digest
        r['model_source_hashes']=models.MODEL_PINS;r['converter_sha256']=sha(Path(models.__file__));r['base_converter_sha256']=sha(Path(models.base.__file__))
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==layout['runtime_sha256'];r['runtime_sha256']=sha(app)
        with(OUT/'native-export.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native-export'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r['native_export_returncode']=rc
        if rc:print((OUT/'native-export.log').read_text()[-12000:],flush=True)
        assert rc==0
        raw=(OUT/'inputs/parent/physical/lvs_flat/extracted.cir').read_text();devices=json.loads((OUT/'native-devices.json').read_text())['devices'];geometry=json.loads((OUT/'inputs/wire/device-locations01.json').read_text())
        ports=json.loads((OUT/'inputs/parent/layout/result.json').read_text())['source_plan']['ports'];tech=json.loads((ROOT/'pdk/libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        r['geometry_readback_controls']=geometry_readback_controls()
        text,binding=build(raw,devices,geometry,tech,ports);verify(text,binding);r['controls']=controls(text,binding)
        reference=(OUT/'inputs/parent/layout/schematic.cir').read_text()
        reference_hbt=Counter()
        for row in models.statements(reference):
            if row[0].startswith('Q'):
                assert row[5]=='npn13G2' and len(row)>=7
                params=dict(field.split('=') for field in row[6:])
                reference_hbt[models.number(params['Nx'])]+=1
        actual_hbt=Counter(models.number(d['native_parameters']['Nx']) for d in binding['devices'] if d['native_model']=='npn13G2')
        assert sum(reference_hbt.values())==120 and actual_hbt==reference_hbt
        r['hbt_size_census']={str(k):v for k,v in actual_hbt.items()}

        (OUT/'pd476-compact.spice').write_text(text);(OUT/'binding.json').write_text(json.dumps(binding,indent=2)+'\n');r['binding']=binding
        assert all(sha(OUT/'inputs'/n)==prior['outputs'][n]for n in selected)
        assert all(sha(ROOT/n)==v['sha256']for n,v in lm['files'].items())and all(sha(m/n)==v['sha256']for n,v in mm['files'].items())
        r.update(status='PASS_PD476_NATIVE_MODEL_BINDING_AND12_CONTROLS_REQUIRES_WIRE_COMPOSITION_AND_WAVES',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
