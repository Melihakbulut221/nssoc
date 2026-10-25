#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Authenticated existing-capture AVSS ledger; no simulator, extraction, or circuit edit."""
import ast,copy,hashlib,json,os
from pathlib import Path
import tx_phase_reset334_return_ledger as ledger
import check_tx_phase_reset334_return_ledger as checks
import tx_phase_reset334_saved_diagnosis as original
import cloud_tx_normal_saved_capture as transport
ROOT=Path(__file__).resolve().parents[1]
METHOD='scripts/tx-phase-reset334-return-ledger-methods.json'
DERIVATION='scripts/tx-phase-reset334-return-ledger-derivation.json'

def methods():
    m=json.loads((ROOT/METHOD).read_bytes())
    for group in ('protected_files','inherited_protected_files'):
        for path,h in m[group].items():assert transport.sha(ROOT/path)==h,path
    assert transport.sha(ROOT/m['original_method_path'])==m['original_method_sha256']
    assert not m['native_simulation_authorized'] and not m['native_extraction_authorized']
    return m

def apply_edits(raw,edits):
    text=raw.decode()
    for e in edits:
        assert text.count(e['old'])==e['count']
        text=text.replace(e['old'],e['new'])
    reverse=text
    for e in reversed(edits):
        assert reverse.count(e['new'])==e['count']
        reverse=reverse.replace(e['new'],e['old'])
    assert reverse.encode()==raw
    return text

def derive_observer():
    p=json.loads((ROOT/DERIVATION).read_bytes())['observer']
    raw=(ROOT/p['path']).read_bytes();assert ledger.digest(raw)==p['source_sha256']
    module=ast.parse(raw)
    node=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='observe_restored')
    body=ast.get_source_segment(raw.decode(),node)
    assert ledger.digest(body)==p['function_sha256']
    changed=apply_edits(body.encode(),p['edits'])
    assert ledger.digest(changed)==p['derived_sha256']
    assert len(ast.parse(changed).body)==1
    namespace=dict(vars(original))
    exec(compile(changed,p['path']+'::exact-ledger-adapter','exec'),namespace)
    return namespace['observe_for_ledger'],dict(original_sha256=p['function_sha256'],
        derived_sha256=p['derived_sha256'],edits=len(p['edits']),reversible=True,
        frozen_review_call_count=1,old_analysis_not_repeated=True)

def derived_controller():
    p=json.loads((ROOT/DERIVATION).read_bytes())['controller']
    raw=(ROOT/p['path']).read_bytes();assert ledger.digest(raw)==p['source_sha256']
    changed=apply_edits(raw,p['edits'])
    assert ledger.digest(changed)==p['derived_sha256']
    assert changed.encode()==(ROOT/p['destination']).read_bytes()
    return dict(edits=len(p['edits']),reversible=True,source_sha256=p['source_sha256'],
        derived_sha256=p['derived_sha256'])

def rc_metadata(m,recorded):
    spec=m['rc_source']
    parts=json.loads((ROOT/m['rc_parts_path']).read_bytes())
    identity=transport.source_identity(recorded['run'],recorded['release'],recorded['ref'],spec)
    assets=transport.asset_plan(recorded['release'],spec,parts)
    assert len(assets)==1 and parts['bytes']==34039324
    assert parts['sha256']=='1840d7545cfb0d72c5cddec7d0ea0ce280a3cb8d442d4e64724e73d9000560b8'
    return dict(identity=identity,parts=len(assets),all_archive_bytes=parts['bytes'])

def row_selection(time,planned):
    assert len(planned)==42 and len({x['row'] for x in planned})==42
    rows=[]
    for x in planned:
        row=x['row'];assert isinstance(row,int) and 0<=row<len(time)
        assert float(time[row])==x['time_s'],'Previously authenticated native row/time changed'
        rows.append(row)
    return rows

def bridge_controls(m):
    methods();math=checks.synthetic_controls()
    observer,derivation=derive_observer();controller=derived_controller()
    recorded=json.loads((ROOT/m['rc_metadata_path']).read_bytes())
    positive=rc_metadata(m,recorded);bad=[]
    trials=[('run_id',lambda x:x['run'].__setitem__('id',0)),
        ('attempt',lambda x:x['run'].__setitem__('run_attempt',2)),
        ('status',lambda x:x['run'].__setitem__('status','in_progress')),
        ('conclusion',lambda x:x['run'].__setitem__('conclusion','failure')),
        ('source',lambda x:x['run'].__setitem__('head_sha','0'*40)),
        ('branch',lambda x:x['run'].__setitem__('head_branch','main')),
        ('workflow',lambda x:x['run'].__setitem__('path','other.yml')),
        ('release',lambda x:x['release'].__setitem__('id',0)),
        ('target',lambda x:x['release'].__setitem__('target_commitish','main')),
        ('draft',lambda x:x['release'].__setitem__('draft',True)),
        ('tag_source',lambda x:x['ref']['object'].__setitem__('sha','0'*40))]
    for field,value in [('id',0),('size',0),('digest','sha256:'+'0'*64),('name','missing')]:
        def mutate(x,field=field,value=value):
            next(a for a in x['release']['assets'] if a['id']==673109129)[field]=value
        trials.append(('part_'+field,mutate))
    for label,mutate in trials:
        x=copy.deepcopy(recorded);mutate(x);assert x!=recorded
        checks.refused('RC_'+label,lambda x=x:rc_metadata(m,x),bad)
    assert len(bad)==15
    # Real immutable prescribed row/time list, without inventing any waveform value.
    planned=methods()['native_rows_for_first_ledger']
    time=[None]*(max(x['row']for x in planned)+1)
    for x in planned:time[x['row']]=x['time_s']
    assert row_selection(time,planned)==[x['row']for x in planned]
    row_bad=[]
    for label,mutate in [('duplicate',lambda x:x.__setitem__(0,dict(x[1]))),
        ('missing',lambda x:x.pop()),('wrong_time',lambda x:x[0].__setitem__('time_s',x[0]['time_s']+1e-15)),
        ('out_of_range',lambda x:x[0].__setitem__('row',len(time)))]:
        q=copy.deepcopy(planned);mutate(q);assert q!=planned
        checks.refused('row_'+label,lambda q=q:row_selection(time,q),row_bad)
    proof=json.loads((ROOT/DERIVATION).read_bytes())['observer'];raw=(ROOT/proof['path']).read_bytes()
    fn=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='observe_restored')
    body=ast.get_source_segment(raw.decode(),fn).encode();edit_bad=[]
    for label,change in [('missing_old',lambda e:e[0].__setitem__('old','never-present')),
        ('wrong_count',lambda e:e[0].__setitem__('count',2))]:
        q=copy.deepcopy(proof['edits']);change(q)
        checks.refused('derivation_'+label,lambda q=q:apply_edits(body,q),edit_bad)
    assert len(row_bad)==4 and len(edit_bad)==2
    return dict(status='PASS_LEDGER_SOURCE_CONTROLS_ONLY',synthetic=math,RC_positive=positive,
        RC_metadata_rejected=bad,row_rejected=row_bad,derivation_rejected=edit_bad,
        observer_derivation=derivation,controller_derivation=controller,
        actual_graph_or_waveform_executed=False)

def prepare_inventory(m,work,inputs,contract_raw):
    methods();rc_raw=(ROOT/m['rc_summary_path']).read_bytes()
    physical_raw=(ROOT/m['physical_summary_path']).read_bytes()
    assert ledger.digest(rc_raw)==ledger.RC_SHA and ledger.digest(physical_raw)==ledger.PHYSICAL_SHA
    rc=json.loads(rc_raw);parts=json.loads((ROOT/m['rc_parts_path']).read_bytes())
    assert len(rc['outputs'])==2044
    identity=transport.restore_parts(m['rc_source'],parts,work/'rc-parts')
    expected=dict(rc['outputs']);expected['result.json']=ledger.RC_SHA
    selected=set(methods()['additional_RC_members'])
    assert len(selected)==4
    assert all(expected[p]==h for p,h in methods()['additional_RC_members'].items())
    archive=transport.audit_complete(parts,work/'rc-parts',work/'rc',expected,selected)
    raw_inputs={s:dict(res_ext=(work/'rc'/s/'precise/rc01/phase_reset334_wires.res.ext').read_bytes(),
        anchors=(work/'rc'/s/'precise/anchors03.json').read_bytes())for s in ('p','n')}
    supplied=dict(binding_summary_raw=inputs['binding_summary'],payload_raw=inputs['payloads'],
        models=inputs['models'],rc_raw=rc_raw,physical_raw=physical_raw,raw_inputs=raw_inputs)
    catalog=ledger.inventory(**supplied)
    c=json.loads(contract_raw)
    _,probes=ledger.probe_inventory(catalog,contract_raw,{v:None for v in c['vectors']})
    return catalog,supplied,dict(source_identity=identity,archive=archive,
        contract_sha256=ledger.digest(contract_raw),probes_before_frozen_review=probes,
        selected_member_hashes={p:expected[p]for p in sorted(selected)},
        physical_summary_sha256=ledger.digest(physical_raw),RC_summary_sha256=ledger.digest(rc_raw))

def observe(case,method,emit,catalog,inputs):
    fn,proof=derive_observer();contract_raw=(case/'contract.json').read_bytes()
    def finish(time,values,contract,replay):
        assert original.canonical(contract)==original.canonical(json.loads(contract_raw))
        rows=row_selection(time,methods()['native_rows_for_first_ledger'])
        actual_catalog,controls=checks.actual_controls(inputs,contract_raw,time,values,rows)
        assert ledger.digest(json.dumps(actual_catalog,sort_keys=True,allow_nan=False))==ledger.digest(json.dumps(catalog,sort_keys=True,allow_nan=False))
        assert len(controls['rejected'])==36
        emit('actual-ledger-input-controls.json',controls)
        report=ledger.row_ledger(catalog,contract_raw,time,values,rows)
        assert len(report['frames'])==42
        report.update(original_frozen_review_canonical_sha256=ledger.digest(original.canonical(replay)),
            original_electrical_rejection_reproduced=True,original_electrical_review_replays=1,
            observer_derivation=proof,actual_ledger_controls=controls,
            row_selection_basis=methods()['row_selection'],scope='Only42 predetermined native rows; no full-wave R extrema')
        return report
    return fn(case,method,emit,finish)

def compact(report,witness,catalog_proof):
    ranked=[]
    for frame in report['frames']:
        for instance,data in frame['instances'].items():
            edges=sorted(data['every_AVSS_edge'],key=lambda x:(-abs(x['drop_a_minus_b_V']),x['edge']))
            terminals=sorted(data['every_compact_AVSS_terminal'],key=lambda x:(-abs(x['voltage_minus_public_AVSS_V']),x['reference']))
            ranked.append(dict(row=frame['row'],time_s=frame['time_s'],instance=instance,
                edge_count=len(edges),terminal_count=len(terminals),
                largest_absolute_drop_edges=edges[:5],largest_absolute_terminal_offsets=terminals[:5]))
    return dict(status=report['status'],full_witness=witness,full_native_graph=catalog_proof,rows=42,
        summaries=ranked,original_rejection_reproduced=True,original_frozen_review_replays=1,
        actual_ledger_control_count=len(report['actual_ledger_controls']['rejected']),
        entire_wave_extrema_claimed=False,only_fixed42_rows=True,**ledger.FLAGS)
