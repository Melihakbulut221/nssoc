#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from collections import Counter
from decimal import Decimal
import re
import build_pcie_local_vco_hybrid_v6 as compact
from cloud_tx_driver_localpins_intrinsic import resistance
PORTS='inp inn outp outn avdd avss sub iref'.split()
ORDER={'npn13G2':['C','B','E','S'],'rsil':['rsil_1','rsil_2','rsil_sub'],'ptap1':['TIE','WELL']}

def validate_native(native):
    import math
    counts=[]
    for mode,data in native['modes'].items():
        rows=data['devices'];assert len(rows)==14 and len({r['id']for r in rows})==14
        assert Counter(r['model']for r in rows)==dict(npn13G2=4,rsil=2,ptap1=8)
        assert len(data['net_map'])==10 and set(data['net_map'].values())==set(PORTS+['TAIL','BULK'])
        assert len(data['probes'])==8 and {p['name']for p in data['probes']}==set(PORTS)
        for p in data['probes']:assert data['net_map'][p['cluster']]==p['name']
        actual=Counter();terminal_count=0
        for r in rows:
            p=r['parameters'];assert all(math.isfinite(v)for v in p.values())
            assert set(r['terminals'])==set(ORDER[r['model']])
            for t in r['terminals'].values():assert t['logical_net']==data['net_map'][t['cluster']]and t['shapes']
            n=tuple(t['logical_net']for t in (r['terminals'][k]for k in ORDER[r['model']]))
            terminal_count+=len(n)
            if r['model']=='npn13G2':
                assert set(p)=={'Nx','we','le','m'}and p['m']==1
                assert abs(p['we']-.07)<1e-12 and abs(p['le']-.9)<1e-12
                actual[('npn13G2',n,p['Nx'])]+=1
            elif r['model']=='rsil':
                assert set(p)=={'w','l','ps','b','m'}and p['ps']==p['b']==0 and p['m']==1
                assert abs(p['w']-10)<1e-9 and abs(p['l']-70.215)<1e-9
                assert n[-1]=='BULK'
                actual[('rsil',tuple(sorted(n[:2])),n[2])]+=1
            else:
                assert set(p)=={'A','P'}and abs(p['A']-4)<1e-9 and abs(p['P']-8)<1e-9
                actual[('ptap1',n)]+=1
        expected=Counter({
            ('npn13G2',('iref','iref','avss','BULK'),1):1,
            ('npn13G2',('TAIL','iref','avss','BULK'),8):1,
            ('npn13G2',('outn','inp','TAIL','BULK'),8):1,
            ('npn13G2',('outp','inn','TAIL','BULK'),8):1,
            ('rsil',('avdd','outp'),'BULK'):1,('rsil',('avdd','outn'),'BULK'):1,
            ('ptap1',('sub','BULK')):8})
        assert actual==expected and terminal_count==38,'Actual native output topology/geometry differs'
        counts.append(actual)
    assert set(native['modes'])=={'lvs','lvs_flat'}and counts[0]==counts[1]
    return dict(devices=14,hbt=4,resistors=2,contacts=8,terminals=38,ports=PORTS,internal_body_separate=True)

def native_controls(native):
    import copy
    controls=[]
    for name in ['missing_contact','wrong_Nx','swapped_base_emitter','body_short','wrong_load_length','wrong_load_endpoint','duplicate_device','wrong_public_binding']:
        bad=copy.deepcopy(native);data=bad['modes']['lvs_flat'];rows=data['devices']
        q=next(r for r in rows if r['model']=='npn13G2')
        resistor=next(r for r in rows if r['model']=='rsil')
        if name=='missing_contact':rows.remove(next(r for r in rows if r['model']=='ptap1'))
        elif name=='wrong_Nx':q['parameters']['Nx']=2
        elif name=='swapped_base_emitter':q['terminals']['B'],q['terminals']['E']=q['terminals']['E'],q['terminals']['B']
        elif name=='body_short':q['terminals']['S']['logical_net']='avss'
        elif name=='wrong_load_length':resistor['parameters']['l']=71
        elif name=='wrong_load_endpoint':resistor['terminals']['rsil_1']['logical_net']='avss'
        elif name=='duplicate_device':rows[-1]['id']=rows[0]['id']
        else:data['probes'][0]['name']='wrong'
        try:validate_native(bad)
        except (AssertionError,KeyError):controls.append(dict(name=name,rejected=True))
        else:raise AssertionError('Accepted '+name)
    assert len(controls)==8
    return controls

def nodes(r):return [r['terminals'][t]['logical_net']for t in ORDER[r['model']]]

def build(rows,tech,top):
    lines=['* Actual native TX output fourteen-device intrinsic model; not wire RC or qualification.','.subckt '+top+' '+' '.join(PORTS)];bindings=[]
    for r in rows:
        model=r['model'];params={'R':str(resistance(r,tech))}if model=='ptap1'else compact.model_params(r,tech)
        name='XD'+str(r['id']);n=nodes(r);lines.append(' '.join([name,*n,model,*[k+'='+v for k,v in params.items()]]))
        bindings.append(dict(instance=name,native_id=r['id'],model=model,named_terminal_order=ORDER[model],nodes=n,native_parameters=r['parameters'],compact_parameters=params))
    return '\n'.join(lines+['.ends '+top,'']),bindings

def verify(text,rows,tech,top):
    lines=compact.statements(text);assert lines[0]==['.subckt',top,*PORTS]and lines[-1]==['.ends',top],'Clock wrapper changed'
    actual={l[0]:l for l in lines[1:-1]};expected={'XD'+str(r['id']):r for r in rows}
    assert len(actual)==len(lines)-2==len(expected)==14 and set(actual)==set(expected),'Clock device missing or duplicated'
    for name,r in expected.items():
        model=r['model'];p=r['parameters'];n=nodes(r);line=actual[name]
        assert line[1:len(n)+1]==n,'Named native clock terminal changed'
        assert line[len(n)+1]==model,'Native compact model changed'
        words=line[len(n)+2:];params={k:compact.number(v)for k,v in (w.split('=',1)for w in words)}
        assert len(params)==len(words),'Duplicate compact parameter'
        if model=='npn13G2':
            assert set(params)=={'Nx','we','le'}and p['m']==1,'HBT parameter or multiplicity changed'
            assert params['Nx']==p['Nx'] and p['Nx'] in (1,8),'HBT Nx changed'
            for k in ['we','le']:assert params[k]==Decimal(str(p[k]))*Decimal('1e-6'),'HBT physical geometry changed'
        elif model=='rsil':
            assert set(params)=={'w','l','ps','b','m','sw_et'},'Resistor parameter census changed'
            for k in ['w','l','ps']:assert abs(params[k]-Decimal(str(p[k]))*Decimal('1e-6'))<=Decimal('1e-20'),'Resistor native geometry changed'
            assert params['b']==p['b']==0 and params['m']==p['m']==params['sw_et']==1,'Resistor multiplier/body/self-heating changed'
        else:
            assert model=='ptap1'and set(params)=={'R'},'Finite body contact changed'
            g=Decimal(str(p['A']))*Decimal('1e-12')/compact.number(tech['ptap1_raspec'])+Decimal(str(p['P']))*Decimal('1e-6')/compact.number(tech['ptap1_rpspec'])
            assert abs(params['R']*g-1)<=Decimal('1e-26'),'Finite body contact conductance changed'
    return dict(devices=14,hbt=4,resistors=2,finite_contacts=8,ports=PORTS)

def controls(text,rows,tech,top,out):
    result=[]
    for fault in ['missing_hbt','wrong_Nx','swap_emitter_base','body_short','missing_contact','changed_contact_R','wrong_load_length','missing_resistor_ps']:
        lines=text.splitlines();q=next(i for i,l in enumerate(lines)if ' npn13G2 'in l);tap=next(i for i,l in enumerate(lines)if ' ptap1 'in l);offset=next(i for i,l in enumerate(lines)if ' rsil 'in l and 'outp'in l.split())
        if fault=='missing_hbt':del lines[q]
        elif fault=='wrong_Nx':lines[q]=re.sub(r'Nx=\S+','Nx=2',lines[q])
        elif fault=='missing_contact':del lines[tap]
        elif fault=='changed_contact_R':lines[tap]=re.sub(r'R=\S+','R=1',lines[tap])
        elif fault=='wrong_load_length':lines[offset]=re.sub(r'l=\S+','l=7u',lines[offset])
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
