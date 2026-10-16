#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native clock intrinsic six devices with finite body contacts; no wire RC."""
import argparse,json,os,re
from decimal import Decimal
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pcie_local_vco_hybrid_v6 as compact
from cloud_tx_driver_localpins_intrinsic import resistance,PDK
from cloud_tx_clock_reference_binding import bind,ORDER
from run_cloud_tx_layout_repair import sha,fetch
ROOT=Path(__file__).resolve().parents[1]
PORTS=['avdd','cm','avss','sub']
SOURCES={
 'l6p2':dict(summary='874e119dc42f289a2bb343d06f59ec398bab4cf455e6e9e5c64f0b51011fea08',parts='b765fdd2b3d0f7bbfebfd5e8d17057ceb0ab8f3b89a08879a43e19c212302f6a'),
 'l6p5':dict(summary='de5ae2a9d88b63e7ab278938d9f6057667fd1faada57dfb652030d4db6dfd173',parts='c0ebc9188401a9c76c06688c3b9195cac37769eb4068e238ebf97da7a19346f4')}
def nodes(r):return [r['terminals'][t]['logical_net']for t in ORDER[r['model']]]
def build(rows,tech,top):
    lines=['* Actual native clock six-device intrinsic model; not wire RC or qualification.','.subckt '+top+' '+' '.join(PORTS)];bindings=[]
    for r in rows:
        model=r['model'];params={'R':str(resistance(r,tech))}if model=='ptap1'else compact.model_params(r,tech)
        name='XD'+str(r['id']);n=nodes(r);lines.append(' '.join([name,*n,model,*[k+'='+v for k,v in params.items()]]))
        bindings.append(dict(instance=name,native_id=r['id'],model=model,named_terminal_order=ORDER[model],nodes=n,native_parameters=r['parameters'],compact_parameters=params))
    return '\n'.join(lines+['.ends '+top,'']),bindings

def verify(text,rows,tech,top):
    lines=compact.statements(text);assert lines[0]==['.subckt',top,*PORTS]and lines[-1]==['.ends',top],'Clock wrapper changed'
    actual={l[0]:l for l in lines[1:-1]};expected={'XD'+str(r['id']):r for r in rows}
    assert len(actual)==len(lines)-2==len(expected)==6 and set(actual)==set(expected),'Clock device missing or duplicated'
    for name,r in expected.items():
        model=r['model'];p=r['parameters'];n=nodes(r);line=actual[name]
        assert line[1:len(n)+1]==n,'Named native clock terminal changed'
        assert line[len(n)+1]==model,'Native compact model changed'
        words=line[len(n)+2:];params={k:compact.number(v)for k,v in (w.split('=',1)for w in words)}
        assert len(params)==len(words),'Duplicate compact parameter'
        if model=='npn13G2':
            assert set(params)=={'Nx','we','le'}and p['m']==1,'HBT parameter or multiplicity changed'
            assert params['Nx']==p['Nx']==1,'HBT Nx changed'
            for k in ['we','le']:assert params[k]==Decimal(str(p[k]))*Decimal('1e-6'),'HBT physical geometry changed'
        elif model=='rppd':
            assert set(params)=={'w','l','ps','b','m','sw_et'},'Resistor parameter census changed'
            for k in ['w','l','ps']:assert abs(params[k]-Decimal(str(p[k]))*Decimal('1e-6'))<=Decimal('1e-20'),'Resistor native geometry changed'
            assert params['b']==p['b']==0 and params['m']==p['m']==params['sw_et']==1,'Resistor multiplier/body/self-heating changed'
        else:
            assert model=='ptap1'and set(params)=={'R'},'Finite body contact changed'
            g=Decimal(str(p['A']))*Decimal('1e-12')/compact.number(tech['ptap1_raspec'])+Decimal(str(p['P']))*Decimal('1e-6')/compact.number(tech['ptap1_rpspec'])
            assert abs(params['R']*g-1)<=Decimal('1e-26'),'Finite body contact conductance changed'
    return dict(devices=6,hbt=1,resistors=2,finite_contacts=3,ports=PORTS)

def controls(text,rows,tech,top,out):
    result=[]
    for fault in ['missing_hbt','wrong_Nx','swap_emitter_base','body_short','missing_contact','changed_contact_R','wrong_offset_length','missing_resistor_ps']:
        lines=text.splitlines();q=next(i for i,l in enumerate(lines)if ' npn13G2 'in l);tap=next(i for i,l in enumerate(lines)if ' ptap1 'in l);offset=next(i for i,l in enumerate(lines)if ' rppd 'in l and 'er'in l.split())
        if fault=='missing_hbt':del lines[q]
        elif fault=='wrong_Nx':lines[q]=re.sub(r'Nx=\S+','Nx=2',lines[q])
        elif fault=='missing_contact':del lines[tap]
        elif fault=='changed_contact_R':lines[tap]=re.sub(r'R=\S+','R=1',lines[tap])
        elif fault=='wrong_offset_length':lines[offset]=re.sub(r'l=\S+','l=7u',lines[offset])
        elif fault=='missing_resistor_ps':lines[offset]=re.sub(r' ps=\S+','',lines[offset])
        else:
            words=lines[q].split()
            if fault=='swap_emitter_base':words[2],words[3]=words[3],words[2]
            else:words[4]='avss'
            lines[q]=' '.join(words)
        bad='\n'.join(lines)+'\n';(out/(fault+'.spice')).write_text(bad)
        try:verify(bad,rows,tech,top)
        except AssertionError as error:result.append(dict(fault=fault,rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted actual clock model corruption '+fault)
    return result

SOURCES['l5p7']=dict(run=38961605786,head='9f940898df74a063c5f703acb67f6927182ab6c4',summary='8a9ca2d7c21d438d7c8a3b8510c8fe94fd69c086daf8a5ec527498e82477b2ea',parts='28016180d088bf15715a3d96c4f7eab29eb5822b748a31d558d39cfa9d9ee427')

def main():
    p=argparse.ArgumentParser();p.add_argument('--variant',choices=sorted(SOURCES),required=True);a=p.parse_args();assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('hw/soc/out/cloud-tx-clock-reference-intrinsic-'+a.variant);out.mkdir(parents=True,exist_ok=False);reports.OUT=out
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=a.variant,wire_parasitics_included=False,simulator_checked=False,qualified_pex=False,qualified_substrate=False,serial_phy_complete=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        spec=SOURCES[a.variant];source=out/'source';prior,proof=reports.restore_report('tx-clock-reference-binding-'+a.variant,spec.get('run',38945593141),spec['summary'],spec['parts'],source,('native.json',));result['source']=proof
        assert prior['status']=='PASS_NATIVE_CLOCK6_TERMINAL_GEOMETRY_AND_SIX_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE'and prior['source_unchanged']and prior['variant']==a.variant
        assert prior['source_head']==spec.get('head','fbbf09c8079f8104ecb2d1ff9a158fcc236a86f0')and len(prior['controls'])==6 and all(c['rejected']for c in prior['controls'])
        native=json.loads((source/'native.json').read_text());assert bind(native,a.variant)==prior['bindings']and sha(source/'native.json')==prior['native_sha256']
        rows=native['modes']['lvs_flat']['devices'];models=out/'pdk'
        pins={p:h for p,h in compact.MODEL_PINS.items()if p.endswith(('resistors_mod.lib','sg13g2_hbt_mod.lib','sg13g2_tech.json','utility_functions.py'))}
        for path,digest in pins.items():
            target=models/path;target.parent.mkdir(parents=True,exist_ok=True);fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+PDK+'/ihp-sg13g2/'+path,digest,target)
        hbt=(models/'libs.tech/ngspice/models/sg13g2_hbt_mod.lib').read_text(encoding='latin-1');res=(models/'libs.tech/ngspice/models/resistors_mod.lib').read_text()
        assert len(re.findall(r'^\.subckt\s+npn13G2\s+c\s+b\s+e\s+bn\s*$',hbt,re.M|re.I))==1
        assert len(re.findall(r'^\.subckt\s+rppd\s+1\s+2\s+bn\s*$',res,re.M|re.I))==1
        tap=re.search(r'^\.subckt\s+ptap1\s+1\s+2\s*\n(.*?)^\.ends\s+ptap1',res,re.M|re.S|re.I);assert tap
        assert [line.strip() for line in re.findall(r'^R\S+\s+1\s+2\s+R=R\s*$',tap[1],re.M)]==['R1 1 2 R=R'],'Native finite contact law changed'
        tech=json.loads((models/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams'];top='nssoc_clock_reference_'+a.variant+'_native6_intrinsic_v1'
        text,bindings=build(rows,tech,top);model=out/'clock6.spice';model.write_text(text)
        result.update(positive=verify(model.read_text(),rows,tech,top),bindings=bindings,controls=controls(text,rows,tech,top,out))
        assert len(result['controls'])==8 and all(c['rejected']for c in result['controls'])
        assert sha(source/'native.json')==prior['outputs']['native.json']and all(sha(models/p)==h for p,h in pins.items())
        result.update(status='PASS_NATIVE_CLOCK6_INTRINSIC_FINITE_CONTACTS_AND_EIGHT_FAULTS_NOT_RC_OR_ELECTRICAL_ACCEPTANCE',model_sha256=sha(model),models=dict(commit=PDK,hashes=pins),gds_sha256=native['gds_sha256'],native_database_sha256=native['modes']['lvs_flat']['database_sha256'],source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
