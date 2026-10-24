#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve each raw MOS finger, its named D/S junctions, and finite contacts.

The combined native database has three net-oriented junction disagreements.
It is never used as an electrical parameter source here. This is an intrinsic
model pending actual wire RC, simulator checks, substrate and RF qualification.
"""
import json,os,re,sys
from decimal import Decimal
from pathlib import Path
import cloud_tx_input_driver_power as physical
import build_pcie_local_vco_hybrid_v6 as helper
from run_cloud_tx_layout_repair import fetch,sha
ROOT=physical.ROOT;OUT=ROOT/'hw/soc/out/cloud-tx-driver-power-intrinsic'
SOURCE={'run': 38898250502, 'group': 'tx-driver-power-junctions', 'root': 'cloud-tx-driver-power-junctions', 'bytes': 1319944, 'sha': '19c172279ff35065a4f24c7865070089a619c900da42e25c53c1b294dd7c9838', 'summary': '33d5d1f794e9f830e6ec391cec579084c2303f73486bbf2d787af389c27fa4f1'}
PDK='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
PINS=helper.MODEL_PINS|{'libs.tech/ngspice/models/sg13g2_moslv_mod.lib':'124c48af28aee8f4788170b50dbb4d798e7d830c6bb37516f749e16f676fa9db'}
TOP='nssoc_tx_driver_native100_intrinsic_v1';PORTS=['din','dout','avdd','dvdd','avss','sub']
ORDER={'rppd':['rppd_1','rppd_2','rppd_sub'],'ptap1':['TIE','WELL'],'ntap1':['TIE','WELL']}
NODE={'xbuf.net1':'buf_stage1'}
def decimal(x):return Decimal(str(x))
def node(t):return NODE.get(t['logical_net'],t['logical_net'])
def order(r):return ['D','G','S','B'] if r['model'].startswith('sg13_') else ORDER[r['model']]
def resistance(r,tech):
    p=r['parameters'];assert set(p)=={'A','P'} and p['A']>0 and p['P']>0
    return 1/(decimal(p['A'])*Decimal('1e-12')/helper.number(tech[r['model']+'_raspec'])+decimal(p['P'])*Decimal('1e-6')/helper.number(tech[r['model']+'_rpspec']))
def build(rows,tech):
    text=['* Native100 intrinsic development model; no wire RC or qualification.',
          '* MOS order is D G S B, derived from native terminal identities.',
          '* Native combined MOS parameters are intentionally not consumed.',
          '.subckt '+TOP+' '+' '.join(PORTS)]
    bindings=[]
    for r in rows:
        model=r['model'];p=r['parameters'];terms=order(r);assert set(terms)==set(r['terminals'])
        if model.startswith('sg13_'):
            assert set(p)=={'L','W','AS','AD','PS','PD','rfmode'}
            params={k.lower():str(v)+('p' if k in ('AS','AD') else 'u' if k in ('L','W','PS','PD') else '') for k,v in p.items()}|{'ng':'1','m':'1'}
        elif model=='rppd':params=helper.model_params(r,tech)
        else:params={'R':str(resistance(r,tech))}
        name='XD'+str(r['id']);nets=[node(r['terminals'][t]) for t in terms]
        text.append(' '.join([name,*nets,model,*[k+'='+v for k,v in params.items()]]))
        bindings.append(dict(instance=name,native_id=r['id'],model=model,native_parameters=p,named_terminal_order=terms,nodes=nets,compact_parameters=params))
    text+=['.ends '+TOP,''];return '\n'.join(text),bindings

def verify(text,rows,tech):
    lines=helper.statements(text)
    assert lines[0]==['.subckt',TOP,*PORTS] and lines[-1]==['.ends',TOP],'Wrapper changed'
    native={'XD'+str(r['id']):r for r in rows};actual={line[0]:line for line in lines[1:-1]}
    assert len(actual)==len(lines)-2==len(native)==100 and set(actual)==set(native),'Device missing or duplicated'
    for name,r in native.items():
        line=actual[name];terms=order(r);nets=[node(r['terminals'][t]) for t in terms];model=r['model'];p=r['parameters']
        assert line[1:len(terms)+1]==nets,'Named terminal binding changed'
        assert line[len(terms)+1]==model,'Compact model changed'
        words=line[len(terms)+2:];params={k:helper.number(v) for k,v in (w.split('=',1) for w in words)}
        assert len(params)==len(words),'Duplicate parameter'
        if model.startswith('sg13_'):
            assert set(params)=={k.lower() for k in p}|{'ng','m'},'MOS parameter missing'
            for k,v in p.items():
                scale=Decimal('1e-12') if k in ('AD','AS') else Decimal('1e-6') if k in ('W','L','PD','PS') else Decimal(1)
                assert params[k.lower()]==decimal(v)*scale,'MOS parameter or junction orientation changed'
            assert params['ng']==params['m']==1,'Raw finger multiplicity changed'
        elif model=='rppd':
            assert set(params)=={'w','l','ps','b','m','sw_et'},'Resistor parameter census changed'
            for k in ('w','l','ps'):assert params[k]==decimal(p[k])*Decimal('1e-6'),'Resistor geometry changed'
            assert params['b']==p['b']==0 and params['m']==p['m']==params['sw_et']==1
        else:
            assert set(params)=={'R'},'Finite contact parameters changed'
            conductance=decimal(p['A'])*Decimal('1e-12')/helper.number(tech[model+'_raspec'])+decimal(p['P'])*Decimal('1e-6')/helper.number(tech[model+'_rpspec'])
            assert abs(params['R']*conductance-1)<=Decimal('1e-26'),'Finite contact conductance changed'
    return dict(devices=len(native),mos_fingers=84,physical_resistors=4,finite_contacts=12,ports=PORTS)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source=SOURCE,qualified_pex=False,qualified_substrate=False,qualified_timing=False,serial_phy_complete=False,mainchip_integrated=False,wire_parasitics_included=False,simulator_checked=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        physical.OUT=OUT;source,prior=physical.restore(SOURCE)
        assert prior['status']=='PASS_NATIVE_FINGER_BINDING_AND_FAULTS_JUNCTION_COMPARISON_MEASURED_NOT_ELECTRICAL_ACCEPTANCE'
        audit=prior['audit'];assert not audit['aggregate_junction_reproduction_passed'] and sum(not r['equal'] for r in audit['aggregate_comparison'])==3
        result['retained_combined_disagreements']=audit['aggregate_comparison']
        native=json.loads((source/'native.json').read_text());assert sha(source/'native.json')==audit['native_source_sha256']
        rows=native['native']['raw_flat_lvs']['devices'];assert len(rows)==100
        models=OUT/'pdk'
        for path,digest in PINS.items():
            target=models/path;target.parent.mkdir(parents=True,exist_ok=True)
            fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+PDK+'/ihp-sg13g2/'+path,digest,target)
        result['models']=dict(commit=PDK,hashes=PINS)
        tech=json.loads((models/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        # Pin the unmodified model declarations, including MOS order and contact R law.
        for path,model in [('sg13g2_moslv_mod.lib','sg13_lv_nmos'),('sg13g2_moslv_mod.lib','sg13_lv_pmos'),('sg13g2_moshv_mod.lib','sg13_hv_nmos')]:
            lib=(models/'libs.tech/ngspice/models'/path).read_text()
            assert len(re.findall(r'^\.subckt\s+'+model+r'\s+d\s+g\s+s\s+b\s*$',lib,re.M|re.I))==1
        lib=(models/'libs.tech/ngspice/models/resistors_mod.lib').read_text()
        for model in ('ptap1','ntap1'):
            match=re.search(r'^\.subckt\s+'+model+r'\s+1\s+2\s*\n(.*?)^\.ends\s+'+model,lib,re.M|re.S|re.I);assert match
            assert [line.strip() for line in re.findall(r'^R\S+\s+1\s+2\s+R=R\s*$',match[1],re.M)]==['R1 1 2 R=R']
        text,bindings=build(rows,tech);model=OUT/'driver100.spice';model.write_text(text)
        result['positive']=verify(model.read_text(),rows,tech);result['bindings']=bindings
        controls=[]
        for fault in ['missing_MOS','wrong_junction','swap_drain_source','body_short','missing_contact','changed_contact_R','missing_rfmode']:
            lines=text.splitlines();mos=next(i for i,s in enumerate(lines) if ' sg13_lv_nmos ' in s);contact=next(i for i,s in enumerate(lines) if ' ptap1 ' in s)
            if fault=='missing_MOS':del lines[mos]
            elif fault=='missing_contact':del lines[contact]
            elif fault=='changed_contact_R':lines[contact]=re.sub(r'R=\S+','R=1',lines[contact])
            elif fault=='wrong_junction':lines[mos]=re.sub(r'ad=\S+','ad=99p',lines[mos])
            elif fault=='missing_rfmode':lines[mos]=re.sub(r' rfmode=\S+','',lines[mos])
            else:
                words=lines[mos].split()
                if fault=='body_short':words[4]=words[3]
                else:words[1],words[3]=words[3],words[1]
                lines[mos]=' '.join(words)
            bad='\n'.join(lines)+'\n';(OUT/(fault+'.spice')).write_text(bad)
            try:verify(bad,rows,tech)
            except AssertionError as error:controls.append(dict(fault=fault,rejected=True,reason=str(error)))
            else:raise AssertionError('Accepted actual model corruption '+fault)
        result['controls']=controls;result['model_sha256']=sha(model)
        assert all(sha(source/p)==v for p,v in prior['outputs'].items()) and all(sha(models/p)==v for p,v in PINS.items())
        result['status']='PASS_RAW100_NAMED_MOS_JUNCTIONS_AND_FINITE_CONTACT_MODEL_WITH_SEVEN_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
