#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-bound sampler drive/load experiment; frozen wires are not fresh PEX."""
import copy,json,subprocess
from decimal import Decimal as D
from pathlib import Path
import build_pcie_local_vco_hybrid_v6 as parser
import cloud_cdr_v44_intrinsic_mutator as previous
from cdr_v46_clock_response import clock_response
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
VARIANTS=['sampler_drive125_load080']
DIAG_ASSET=669833963
DIAG_SHA='cbe2e04bebd90b7aa984940700aa754afe306ca94d1a1186d9a3ba2cba747c58'
PARENTS=[('nominal_early',669073404,'bec2ab47a567f0a6ff2f8a0e403c179e8eeb2952388dcef28906693b8846f82a'),('nominal_late',669064409,'95f13c2d46aaa09c59e5233e43d5bfc245e8986333df952ef1aff727cbcfdcb8')]
def fmt(x):return format(x.normalize(),'f')
def mos_dimensions(p):
    q=copy.deepcopy(p);w=parser.number(p['w'])/D('1e-6')
    assert w in (D(36),D(54)) and parser.number(p['l'])==D('.3e-6')
    assert p['ng']==p['m']=='1' and p['rfmode']=='0'
    assert all(parser.number(p[k])==w*D('.34e-12')for k in ('as','ad'))
    assert all(parser.number(p[k])==(2*w+D('.68'))*D('1e-6')for k in ('ps','pd'))
    new=w*D('1.25')
    q.update(w=fmt(new)+'u',**{k:fmt(new*D('.34'))+'p'for k in ('as','ad')},
      **{k:fmt(2*new+D('.68'))+'u'for k in ('ps','pd')})
    assert parser.number(q['w'])/parser.number(p['w'])==D('1.25')
    return q
def resistor_dimensions(p,role,latch,tag):
    q=copy.deepcopy(p);length=parser.number(p['l'])/D('1e-6')
    if role=='collector_load':
        assert parser.number(p['w'])==D('32e-6')
        expected=D('1.2')if latch=='slave'else D('3.9')if tag in ('c','d')else D('2.6')
    else:
        assert role in ('track_bleed','hold_bleed') and parser.number(p['w'])==D('1e-6')
        expected=D('6.4')if role=='track_bleed'else D('4.8')
        if latch=='slave':expected*=2
    assert length==expected,(role,latch,tag,length,expected)
    assert p['sw_et']=='1' and p['b']=='0' and p['m']=='1'
    q['l']=fmt(length*D('.8'))+'u'
    assert parser.number(q['l'])/parser.number(p['l'])==D('.8')
    assert {k:v for k,v in q.items()if k!='l'}=={k:v for k,v in p.items()if k!='l'}
    assert parser.number(q['l'])/D('5e-9')==int(parser.number(q['l'])/D('5e-9'))
    return q
def controls():
    p=dict(w='36u',l='.3u',ng='1',m='1',rfmode='0',**{'as':'12.24p','ad':'12.24p','ps':'72.68u','pd':'72.68u'})
    assert mos_dimensions(p)==dict(p,w='45u',**{'as':'15.3p','ad':'15.3p','ps':'90.68u','pd':'90.68u'})
    p54=dict(p,w='54u',**{'as':'18.36p','ad':'18.36p','ps':'108.68u','pd':'108.68u'})
    assert mos_dimensions(p54)['w']=='67.5u'
    rejected=[]
    for k,v in [('w','40u'),('l','.2u'),('ng','2'),('m','2'),('rfmode','1'),('as','1p'),('ad','1p'),('ps','1u'),('pd','1u')]:
        bad=dict(p);bad[k]=v
        try:mos_dimensions(bad)
        except AssertionError:rejected.append('mos-'+k)
        else:raise AssertionError('Undeclared MOS dimensions accepted')
    for tag in 'abcd':
        for latch in ('master','slave'):
            for role in ('collector_load','track_bleed','hold_bleed'):
                length=('1.2'if latch=='slave'else'3.9'if tag in 'cd'else'2.6')if role=='collector_load'else(('12.8'if latch=='slave'else'6.4')if role=='track_bleed'else('9.6'if latch=='slave'else'4.8'))
                r=dict(w='32u'if role=='collector_load'else'1u',l=length+'u',sw_et='1',b='0',m='1',ps='0u')
                q=resistor_dimensions(r,role,latch,tag)
                assert parser.number(q['l'])*D('1.25')==parser.number(r['l'])
                bad=dict(r,l='999u')
                try:resistor_dimensions(bad,role,latch,tag)
                except AssertionError:rejected.append(tag+'-'+latch+'-'+role)
                else:raise AssertionError('Unknown parent resistor accepted')
    return dict(rejected=rejected,geometry_width_times_length_ratio=D('1.25')*D('.8')==1,
      actual_current_or_swing_preservation_proven=False,
      scope='Nominal intrinsic dimension ratios only; all real currents, voltages and timing require the original full transient gates.')
def selection(records,planes,diag):
    logical={}
    for p in planes['anchors']:
        assert logical.setdefault(p['logical_net'],p['native_cluster'])==p['native_cluster']
    def term(n,t):
        return next(v['native_cluster']for v in records[n.removeprefix('xpd.')]['terminals']if v['terminal']==t)
    def between(a,b):
        found=[n for n,r in records.items()if r['model']=='rppd' and {a,b}<={t['native_cluster']for t in r['terminals']}]
        assert len(found)==1,(a,b,found)
        return found[0]
    edits={};roles={}
    for tag in 'abcd':
        for latch,g in diag['stages'][tag]['latches']['native_graph'].items():
            assert latch in ('master','slave')
            sels=g['track_selectors']+g['hold_selectors']
            assert len(sels)==len(set(sels))==4
            tail={term(n,'E')for n in sels};assert len(tail)==1
            found=[n for n,r in records.items()if r['model']=='sg13_lv_nmos' and term(n,'D')==next(iter(tail)) and term(n,'G')==logical['ir'+tag] and term(n,'S')==logical['avss']]
            assert len(found)==4
            for n in found:
                assert n not in edits
                assert parser.number(records[n]['parameters']['w'])==D('36e-6'if latch=='master'else'54e-6')
                edits[n]=mos_dimensions(records[n]['parameters']);roles[n]=dict(stage=tag,latch=latch,role='tail_mos')
            for polarity in ('positive','negative'):
                n=between(logical['avdd'],g[polarity+'_output_native']);assert n not in edits
                edits[n]=resistor_dimensions(records[n]['parameters'],'collector_load',latch,tag)
                roles[n]=dict(stage=tag,latch=latch,role='collector_load',polarity=polarity)
            for role,key in [('track_bleed','track_selectors'),('hold_bleed','hold_selectors')]:
                clusters={term(n,'C')for n in g[key]};assert len(clusters)==1
                n=between(logical['avss'],next(iter(clusters)));assert n not in edits
                edits[n]=resistor_dimensions(records[n]['parameters'],role,latch,tag)
                roles[n]=dict(stage=tag,latch=latch,role=role)
    assert len(edits)==64 and sum(r['role']=='tail_mos'for r in roles.values())==32
    return edits,roles
def graph_controls(records,planes,diag):
    edits,roles=selection(records,planes,diag)
    n=next(n for n,v in roles.items()if v['role']=='tail_mos');rn=next(n for n,v in roles.items()if v['role']=='collector_load')
    rejected=[]
    for fault in ['missing-tail','wrong-tail-bias','wrong-tail-size','missing-collector-load','wrong-load-dimension','wrong-output-cluster','duplicated-selector']:
        rs,ps,ds=copy.deepcopy((records,planes,diag))
        if fault=='missing-tail':del rs[n]
        elif fault=='wrong-tail-bias':
            next(t for t in rs[n]['terminals']if t['terminal']=='G')['native_cluster']=-999
        elif fault=='wrong-tail-size':rs[n]['parameters']['w']='999u'
        elif fault=='missing-collector-load':del rs[rn]
        elif fault=='wrong-load-dimension':rs[rn]['parameters']['l']='999u'
        elif fault=='wrong-output-cluster':ds['stages']['c']['latches']['native_graph']['master']['positive_output_native']=-999
        else:
            g=ds['stages']['a']['latches']['native_graph']['master'];g['track_selectors'][0]=g['hold_selectors'][0]
        try:selection(rs,ps,ds)
        except (AssertionError,KeyError,StopIteration):rejected.append(fault)
        else:raise AssertionError('Corrupted sampler graph accepted: '+fault)
    return rejected
def parent_headroom(out):
    result={}
    for phase,aid,h in PARENTS:
        raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])
        dest=out/('parent-'+phase+'.json');dest.write_bytes(raw);assert sha(dest)==h
        r=json.loads(raw)
        assert r['devices_passed']and r['sources_unchanged']and not r['data_passed']and not r['phase_passed']
        assert r['intrinsic_screen']['variant']=='cd_master_l39'
        peak=max(v['maximum_alltime_abs_ic_per_emitter_a']for v in r['device_checks'].values())
        assert peak*1.25<.003
        result[phase]=dict(asset=aid,sha256=h,parent_max_current_per_emitter_a=peak,
          conservative_nominal_scaled_current_per_emitter_a=peak*1.25,
          parent_minimum_active_vce_v=min(v['minimum_active_vce_v']for v in r['device_checks'].values()))
    return dict(phases=result,scope='Nominal current-density projection only; candidate MOS/nonlinear HBT currents and narrow VCE headroom require all original native bounds. No projected pass.')
def apply(model,contract,planes,variant,out):
    assert variant in VARIANTS
    checks=controls();checks['parent_headroom']=parent_headroom(out)
    raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(DIAG_ASSET),'-H','Accept: application/octet-stream'])
    path=out/'v44-l39-early-native-diagnosis.json';path.write_bytes(raw);assert sha(path)==DIAG_SHA
    diag=json.loads(raw)
    assert diag['all120original_hbt_checks_reproduced']and diag['all4original_sampler_checks_reproduced']
    assert diag['original_rejection_preserved']and not diag['accepted']and diag['original_devices_passed']
    evidence=json.loads((ROOT/'docs/evidence/cdr-v46-transfer-observation-pass-20261023.json').read_text())
    assert evidence['run']==40008988737 and len(evidence['cases'])==4
    assert all(c['all_original_results_reproduced']and c['original_failure_preserved']for c in evidence['cases'].values())
    parent=out/'v44-l39-reference';parent.mkdir()
    parent_model,parent_contract,proof=previous.apply(model,contract,planes,'cd_master_l39',parent)
    assert len(proof['changes'])==84 and proof['all_wire_cards_unchanged']
    assert proof['candidate_model_sha256']=='b75950141d51db8d013bf06a5124f13a6fbe4448fe0fa92b9fc3925670f93a99'
    originals={r['instance'].lower():r for r in contract['device_records']}
    records={r['instance'].lower():r for r in parent_contract['device_records']}
    edits,added_roles=selection(records,planes,diag);checks['graph_faults']=graph_controls(records,planes,diag)
    candidate=copy.deepcopy(parent_contract);copies={r['instance'].lower():r for r in candidate['device_records']}
    omitted={'instance','original_parameters','candidate_parameters','original_card','candidate_card'}
    roles={c['instance']:{k:v for k,v in c.items()if k not in omitted}for c in proof['changes']};roles.update(added_roles)
    assert len(roles)==112
    original_rows=parser.statements(model.read_text());parent_rows=parser.statements(parent_model.read_text())
    original_cards={r[0].lower():r for r in original_rows};rows=[];changes=[];parent_changes=[]
    for row in parent_rows:
        n=row[0].lower();new=row.copy()
        if n in edits:
            for key,value in edits[n].items():
                if value==records[n]['parameters'][key]:continue
                positions=[i for i,x in enumerate(row)if x.startswith(key+'=')];assert len(positions)==1
                i=positions[0];assert row[i]==key+'='+records[n]['parameters'][key];new[i]=key+'='+value
            copies[n]['parameters']=copy.deepcopy(edits[n])
            parent_changes.append(dict(instance=n,**added_roles[n],parent_parameters=records[n]['parameters'],candidate_parameters=edits[n],parent_card=row,candidate_card=new))
        if new!=original_cards[n]:
            assert n in roles
            changes.append(dict(instance=n,**roles[n],original_parameters=originals[n]['parameters'],candidate_parameters=copies[n]['parameters'],original_card=original_cards[n],candidate_card=new))
        rows.append(new)
    assert len(parent_changes)==64 and len(changes)==len({c['instance']for c in changes})==112
    assert len(rows)==476+17918+12850+2
    assert [r for r in parent_rows if r[0].lower()not in edits]==[r for r in rows if r[0].lower()not in edits]
    assert [r for r in original_rows if r[0].startswith(('R','C'))]==[r for r in rows if r[0].startswith(('R','C'))]
    restored=copy.deepcopy(candidate)
    for r in restored['device_records']:
        if r['instance'].lower()in roles:r['parameters']=copy.deepcopy(originals[r['instance'].lower()]['parameters'])
    assert restored==contract,'Undeclared native topology, references, primitive or parameter change'
    output=out/('exploratory-'+variant+'.spice')
    output.write_text('* EXPLORATORY sampler tail widths1.25x and intrinsic load/bleed lengths0.8x; frozen v32 metal RC, no physical acceptance.\n'+'\n'.join(' '.join(r)for r in rows)+'\n')
    (out/'exploratory-composition.json').write_text(json.dumps(candidate,indent=2)+'\n')
    return output,candidate,dict(variant=variant,parent_variant='v44_cd_master_l39',
      baseline_model_sha256=sha(model),candidate_model_sha256=sha(output),actual_candidate_layout_verified=False,fresh_candidate_rc=False,
      wire_R=17918,wire_C=12850,all_wire_cards_unchanged=True,all_other_native_cards_unchanged=True,unchanged_original_gates=True,
      changes=changes,parent_changes=parent_changes,controls=checks,source_diagnosis_sha256=DIAG_SHA,
      diffusion_model_scope='Same declared single-finger0.34um diffusion hypothesis: recomputed area/perimeter for45um/67.5um widths. Not extracted geometry.',
      scope='Only32 actual sampler tail MOS widths and32 actual collector/bleed resistor lengths change from v44l39. All HBT sizes, dividers, followers, other devices, sourcebits, clocks, external biases,150fF/50fF loads, full34.25ns and every original bound remain. Nominal current/resistance compensation is a hypothesis, not a verified swing or speed improvement. Candidate requires real GDS/DRC/LVS/fresh RC/PVT/loop qualification.')
