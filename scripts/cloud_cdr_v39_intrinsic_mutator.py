#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Test actual retimer pull-down dimensions against measured v37 current loss."""
import copy,json
from decimal import Decimal
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v37_intrinsic_mutator as previous
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
VARIANTS={'follower_l18':'1.8','follower_l15':'1.5'}

def resized(params,length):
    assert length in VARIANTS.values()
    assert parser.number(params['w'])==Decimal('4e-6')
    assert parser.number(params['l'])==Decimal('2.25e-6')
    result=copy.deepcopy(params);result['l']=length+'u'
    assert {k:v for k,v in result.items()if k!='l'}=={k:v for k,v in params.items()if k!='l'}
    return result

def sink(records,emitter,avss):
    assert emitter!=avss
    found=[r for r in records.values()if r['model']=='rppd'
           and {t['native_cluster']for t in r['terminals']if t['terminal']in ('rppd_1','rppd_2')}=={emitter,avss}]
    assert len(found)==1,'Exactly one native resistor between emitter and AVSS'
    return found[0]

def controls():
    p=dict(w='4u',l='2.25u',b='0',m='1')
    for length in VARIANTS.values():assert resized(p,length)['l']==length+'u'
    rejected=[]
    for key,value,length in [('w','6u','1.8'),('l','4.5u','1.8'),('w','4u','1.125')]:
        q=copy.deepcopy(p);q[key]=value
        try:resized(q,length)
        except AssertionError:rejected.append((key,value,length))
        else:raise AssertionError('Undeclared pull-down geometry accepted')
    r=dict(model='rppd',terminals=[dict(terminal='rppd_1',native_cluster=1),dict(terminal='rppd_2',native_cluster=2),dict(terminal='rppd_sub',native_cluster=3)])
    assert sink({'r':r},1,2)==r
    for label,records,a,b in [('missing',{},1,2),('duplicate',{'a':r,'b':r},1,2),('wrong_net',{'r':r},1,3),('same_net',{'r':r},1,1),('wrong_model',{'r':dict(r,model='npn13g2')},1,2)]:
        try:sink(records,a,b)
        except AssertionError:rejected.append(label)
        else:raise AssertionError('Invalid native sink binding accepted')
    return dict(rejected=rejected,only_four_native_pull_down_lengths_changed=True)

def apply(model,contract,planes,variant,out):
    assert variant in VARIANTS
    checks=controls()
    receipt_path=ROOT/'docs/evidence/cdr-v36-v37-loading-results-20261023.json'
    receipt=json.loads(receipt_path.read_text())
    assert receipt['run']==39867076460 and receipt['all_original_checks_reproduced']
    assert not receipt['full_phy_accepted']
    selection=receipt['selected_followers'];assert set(selection)=={'ac','bd'}
    base_dir=out/'v37-cdbias15-reference';base_dir.mkdir()
    base_model,base_contract,proof=previous.apply(model,contract,planes,'cdbias15',base_dir)
    assert len(proof['changes'])==72 and proof['all_wire_cards_unchanged']
    originals={r['instance'].lower():r for r in contract['device_records']}
    records={r['instance'].lower():r for r in base_contract['device_records']}
    candidate=copy.deepcopy(base_contract);copies={r['instance'].lower():r for r in candidate['device_records']}
    avss={a['native_cluster']for a in planes['anchors']if a['logical_net'].lower()=='avss'}
    assert len(avss)==1;avss=next(iter(avss))
    edits={};roles={}
    for stage,polarities in selection.items():
        assert set(polarities)=={'positive','negative'}
        for polarity,identity in polarities.items():
            name=identity['name'].removeprefix('xpd.')
            hbt=records[name];assert hbt==originals[name] and hbt['native_id']==identity['native_id']
            assert hbt['model']=='npn13g2'and parser.number(hbt['parameters']['nx'])==4
            terms={t['terminal']:t['native_cluster']for t in hbt['terminals']}
            assert set(terms)=={'C','B','E','S'}
            rec=sink(records,terms['E'],avss);n=rec['instance'].lower()
            assert n not in edits and rec==originals[n]
            edits[n]=resized(rec['parameters'],VARIANTS[variant])
            roles[n]=dict(stage=stage,latch='retimer',role='emitter_pull_down',polarity=polarity,
                          native_follower=name,emitter_native=terms['E'],avss_native=avss)
    assert len(edits)==4 and not set(edits)&{c['instance']for c in proof['changes']}
    rows=parser.statements(base_model.read_text());original_rows=parser.statements(model.read_text())
    oldcards={r[0].lower():r for r in original_rows};newrows=[];added=[]
    for row in rows:
        n=row[0].lower();new=row.copy()
        if n in edits:
            positions=[i for i,s in enumerate(new)if s.startswith('l=')];assert len(positions)==1
            i=positions[0];assert new[i]=='l='+originals[n]['parameters']['l']
            new[i]='l='+edits[n]['l'];copies[n]['parameters']=copy.deepcopy(edits[n])
            added.append(dict(instance=n,**roles[n],original_parameters=originals[n]['parameters'],
                              candidate_parameters=copies[n]['parameters'],original_card=oldcards[n],candidate_card=new))
        newrows.append(new)
    changes=proof['changes']+added;changed={c['instance']for c in changes}
    assert len(added)==4 and len(changes)==len(changed)==76 and len(newrows)==476+17918+12850+2
    assert [r for r in original_rows if r[0].startswith(('R','C'))]==[r for r in newrows if r[0].startswith(('R','C'))]
    assert [r for r in original_rows if r[0].lower()not in changed]==[r for r in newrows if r[0].lower()not in changed]
    restored=copy.deepcopy(candidate)
    for rec in restored['device_records']:
        if rec['instance'].lower()in changed:rec['parameters']=copy.deepcopy(originals[rec['instance'].lower()]['parameters'])
    assert restored==contract,'Undeclared native topology or parameter edit'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY: only four stronger native retimer pull-downs relative to v37 cdbias15; frozen wire RC.\n'+'\n'.join(' '.join(r)for r in newrows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,parent_variant='v37_cdbias15',baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),
        actual_candidate_layout_verified=False,fresh_candidate_rc=False,wire_R=17918,wire_C=12850,
        all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,unchanged_original_gates=True,
        all_sampler_primitives_unchanged_relative_to_v37=True,changes=changes,controls=checks,
        source_diagnosis_sha256=sha(receipt_path),diffusion_model_scope=proof['diffusion_model_scope'],
        scope='Only four existing ac/bd emitter pull-down lengths2.25->1.8 or1.5um on v37 cdbias15. No extra ideal source, load reduction, clock shift or regenerated data. All original full native device/phase/current/data gates retained. Requires actual new layout/fresh RC/full-loop/PVT qualification.')
