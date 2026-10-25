#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Balance slave drive, device area and collector loading on disclosed frozen RC."""
import copy,json,subprocess
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v35_intrinsic_mutator as previous
from run_cloud_tx_layout_repair import sha
VARIANTS={'slave_drive15_load12':'1.2','slave_drive15_load10':'1.0'}
DIAG_SHA='27660d1d4c18160a5932f5ca5852d4272908a7fd673cd34c0fd971021d9fce26'
def mos_dimensions(params):
    # Explicit rectangular diffusion hypothesis for a single54um finger.
    # Original native36um card must obey the same0.34um diffusion depth.
    # This is not a new extraction and MUST be replaced by actual candidate
    # GDS/intrinsic extraction before any physical acceptance.
    p=copy.deepcopy(params);D=Decimal
    assert parser.number(p['w'])==D('36e-6') and parser.number(p['l'])==D('.3e-6')
    assert p['ng']==p['m']=='1' and p['rfmode']=='0'
    assert all(parser.number(p[k])==D('12.24e-12')for k in ['as','ad'])
    assert all(parser.number(p[k])==D('72.68e-6')for k in ['ps','pd'])
    p.update(w='54u',**{'as':'18.36p','ad':'18.36p','ps':'108.68u','pd':'108.68u'})
    return p
def controls():
    p=dict(w='36u',l='.3u',ng='1',m='1',rfmode='0',**{'as':'12.24p','ad':'12.24p','ps':'72.68u','pd':'72.68u'})
    q=mos_dimensions(p)
    assert parser.number(q['as'])/parser.number(q['w'])==Decimal('.34e-6')
    assert parser.number(q['ps'])==2*(parser.number(q['w'])+Decimal('.34e-6'))
    rejected=[]
    for key,value in [('w','32u'),('l','.2u'),('ng','2'),('m','2'),('as','1p'),('ad','1p'),('ps','72u'),('pd','72u'),('rfmode','1')]:
        bad=copy.deepcopy(p);bad[key]=value
        try:mos_dimensions(bad)
        except AssertionError:rejected.append(key)
        else:raise AssertionError('Inconsistent native MOS geometry accepted: '+key)
    assert p['w']=='36u'and p['as']=='12.24p'
    return dict(rejected=rejected,original_unchanged=True,declared_diffusion_hypothesis_only=True)
def apply(model,contract,planes,variant,out):
    assert variant in VARIANTS
    checks=controls()
    raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/665725446','-H','Accept: application/octet-stream'])
    path=out/'v33-native-steering-diagnosis.json';path.write_bytes(raw);assert sha(path)==DIAG_SHA
    diag=json.loads(raw)
    assert diag['source_head']=='a63c0e9775bb1d671a82660db88ff31c2e0917ee'
    assert diag['original_devices_passed']and diag['original_rejection_preserved']and not diag['accepted']
    base_dir=out/'slave-load16-reference';base_dir.mkdir()
    base_model,base_contract,proof=previous.apply(model,contract,planes,'slave_load16',base_dir)
    assert len(proof['changes'])==16 and proof['all_master_collector_loads_unchanged']
    original={r['instance'].lower():r for r in contract['device_records']}
    records={r['instance'].lower():r for r in base_contract['device_records']}
    candidate=copy.deepcopy(base_contract);copies={r['instance'].lower():r for r in candidate['device_records']}
    logical={}
    for a in planes['anchors']:
        assert logical.setdefault(a['logical_net'],a['native_cluster'])==a['native_cluster']
    def term(n,t):
        r=records[n.removeprefix('xpd.')]
        return next(x['native_cluster']for x in r['terminals']if x['terminal']==t)
    edits={};roles={}
    for tag,stage in diag['stages'].items():
        g=stage['latches']['native_graph']['slave']
        for role,names,old,new in [('selector',g['track_selectors']+g['hold_selectors'],2,3),
              ('data_hold',[g['data_positive'],g['data_negative']]+g['hold_pair'],4,6)]:
            assert len(names)==len(set(names))==4
            for name in names:
                n=name.removeprefix('xpd.');r=records[n]
                assert n not in edits and r['model']=='npn13g2'
                assert parser.number(r['parameters']['nx'])==Decimal(old)
                edits[n]={'nx':str(new)};roles[n]=dict(stage=tag,latch='slave',role=role)
        tail={term(n,'E')for n in g['track_selectors']+g['hold_selectors']};assert len(tail)==1
        mos=[n for n,r in records.items()if r['model']=='sg13_lv_nmos'
             and term(n,'D')in tail and term(n,'G')==logical['ir'+tag]and term(n,'S')==logical['avss']]
        assert len(mos)==4
        for n in mos:
            assert n not in edits
            replacement=mos_dimensions(records[n]['parameters'])
            edits[n]={k:v for k,v in replacement.items()if v!=records[n]['parameters'][k]}
            assert set(edits[n])=={'w','as','ad','ps','pd'}
            roles[n]=dict(stage=tag,latch='slave',role='tail_mos')
    assert len(edits)==48 and sum(x['role']=='tail_mos'for x in roles.values())==16
    for c in proof['changes']:
        n=c['instance'];assert c['latch']=='slave'
        roles[n]={k:c[k]for k in ['stage','latch','role']}
        if c['role']=='collector_load':
            assert n not in edits and records[n]['parameters']['l']=='1.6u'
            edits[n]={'l':VARIANTS[variant]+'u'}
    assert len(edits)==56 and len(roles)==64
    rows=parser.statements(base_model.read_text())
    originals=parser.statements(model.read_text());oldcards={r[0].lower():r for r in originals}
    newrows=[];changes=[]
    for row in rows:
        n=row[0].lower();new=row.copy()
        if n in edits:
            for key,value in edits[n].items():
                positions=[i for i,x in enumerate(new)if x.startswith(key+'=')];assert len(positions)==1
                i=positions[0];assert new[i]==key+'='+records[n]['parameters'][key]
                new[i]=key+'='+value;copies[n]['parameters'][key]=value
        if new!=oldcards[n]:
            assert n in roles
            changes.append(dict(instance=n,**roles[n],original_parameters=original[n]['parameters'],
                candidate_parameters=copies[n]['parameters'],original_card=oldcards[n],candidate_card=new))
        newrows.append(new)
    assert len(changes)==64 and len(newrows)==476+17918+12850+2
    assert {c['instance']for c in changes}==set(roles)
    assert [r for r in originals if r[0].startswith(('R','C'))]==[r for r in newrows if r[0].startswith(('R','C'))]
    assert [r for r in originals if r[0].lower()not in roles]==[r for r in newrows if r[0].lower()not in roles]
    restored=copy.deepcopy(candidate)
    for r in restored['device_records']:
        if r['instance'].lower()in roles:r['parameters']=copy.deepcopy(original[r['instance'].lower()]['parameters'])
    assert restored==contract,'Unexpected topology, native references or unrelated primitive changed'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY: slave drive/area/load balance; frozen v32 RC and declared intrinsic diffusion hypothesis, not extracted candidate geometry.\n'+'\n'.join(' '.join(r)for r in newrows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),
        actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,
        all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,all_master_primitives_unchanged=True,
        unchanged_original_gates=True,changes=changes,controls=checks,
        diffusion_model_scope='Declared single-finger54um x0.34um rectangular diffusion; original36um native card verified. Not physical extraction; requires new GDS and fresh full RC.',
        scope='Only slave32HBT areas1.5x,16tailMOS widths36->54um with declared diffusion dimensions,8collector lengths1.2/1.0um and8bleed12 dimensions. All masters, external biases/clocks/data,150fF/50fF loads and full gates unchanged. Requires actual GDS/DRC/LVS/fresh RC and repeated full loaded/PVT/loop checks.')
