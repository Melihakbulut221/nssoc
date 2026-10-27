#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact original geometry bridge; successful current producer must be separately bound."""
import ast,contextlib,hashlib,json,os
import mainchip_current_postroute_admission as admission
GEOMETRY='scripts/cloud_mainchip_route12_postroute_geometry.py'
POSTROUTE='scripts/cloud_mainchip_route12_postroute.py'
GEOMETRY_SHA='52de46aacf9b97ab17ac56560efef838d149a746a2dd09a6f1af87ed41be0c97'
POSTROUTE_SHA='c6335c535959286b7f77c3aaf6a5ab631640557c8453079a80dd97c97f58701f'
EDITS=json.loads("[[\"from cloud_mainchip_route12_drt_continuation import log_proof\\n\",\"from cloud_mainchip_route12_drt_continuation import log_proof\\nfrom mainchip_current_postroute_admission import consume\\n\"],[\"        selected=json.loads(os.environ['NSSOC_COMPLETED_DRT'])\\n        live=api('actions/runs/'+str(selected['run']))\\n        assert live['status']=='completed'and live['conclusion']=='success','Never consume unfinished route'\\n        names=['work/detailed-route.odb','work/detailed-route.drc','work/native.log','work/boots.log','work/before-guide-read.odb','work/drt-done']\\n        actual,aproof=reports.restore_report(selected['group'],selected['run'],selected['summary_sha256'],selected['parts_sha256'],OUT/'routed',names)\\n        portable=json.loads((ROOT/'docs/evidence/mainchip-portable-runtime-pass-20261020.json').read_text())\\n        validate(selected,live,actual,portable['report']['image_id'])\\n        controller='scripts/cloud_mainchip_route12_drt'+('_continuation'if 'continuation' in live['path']else'')+'.py'\\n        assert source_hash(controller,selected['source_head'])==selected['controller_sha256']==sha(ROOT/controller)\\n        native=log_proof((OUT/'routed/work/native.log').read_bytes(),(OUT/'routed/work/boots.log').read_bytes())\\n        assert native==actual['native_log']\\n        drc=OUT/'routed/work/detailed-route.drc'\\n        if native['completed_violation_counts'][-1]==0:\\n            assert not drc.read_text().strip(),'Zero native count but nonempty final DRC report'\\n        else:\\n            assert drc.read_text().strip(),'Nonzero native count but empty final DRC report'\\n        r['native_drc_report']=dict(sha256=sha(drc),bytes=drc.stat().st_size,\\n            final_native_count=native['completed_violation_counts'][-1],zero_count_and_empty_report_consistent=True)\\n        assert(OUT/'routed/work/drt-done').read_text().strip()\\n        assert sha(OUT/'routed/work/before-guide-read.odb')==sha(a)\\n        b=OUT/'routed/work/detailed-route.odb';assert sha(b)==actual['routed_odb_sha256']\\n        r.update(route_complete=True,completed_route_source=aproof,completed_route_descriptor=selected,\\n            global_source=bproof,handoff_source=hproof,candidate_netlist_path=str(nl),\\n            candidate_netlist_sha256=sha(nl),reported_native_drt_violation_counts=native['completed_violation_counts'])\\n\",\"        b,aproof=consume(ROOT,OUT)\\n        r['native_drc_report']=aproof['final_DRT']\\n        r.update(route_complete=True,completed_route_source=aproof,\\n            completed_route_descriptor=aproof['envelope'],global_source=bproof,handoff_source=hproof,\\n            candidate_netlist_path=str(nl),candidate_netlist_sha256=sha(nl),\\n            reported_native_drt_violation_counts=[aproof['final_original_class_DRT_markers']],\\n            repaired_original_class_admission=aproof)\\n\"],[\"from pathlib import Path\\n\",\"from pathlib import Path\\nimport mainchip_current_postroute_terminal as terminal\\n\"],[\"    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\\\\n')\\n\",\"    def save():terminal.write(OUT/'result.json',r)\\n\"],[\"        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()\\n\",\"        terminal.finalize_worker(OUT,r,save)\\n\"]]")
POST_EDITS=json.loads("[[\"from pathlib import Path\\n\",\"from pathlib import Path\\nimport mainchip_current_postroute_terminal as terminal\\n\"],[\"    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\\\\n')\\n\",\"    def save():terminal.write(OUT/'result.json',r)\\n\"],[\"        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()\\n\",\"        terminal.finalize_worker(OUT,r,save)\\n\"]]")
def replace_exact(raw,edits):
    original=raw.decode();current=original
    for before,after in edits:
        assert current.count(before)==1;current=current.replace(before,after)
    inverse=current
    for before,after in reversed(edits):
        assert inverse.count(after)==1;inverse=inverse.replace(after,before)
    assert inverse==original
    ast.parse(current)
    return current.encode()
def derive(old,postroute):
    assert hashlib.sha256(old).hexdigest()==GEOMETRY_SHA
    assert hashlib.sha256(postroute).hexdigest()==POSTROUTE_SHA
    geometry=replace_exact(old,EDITS);numerical=replace_exact(postroute,POST_EDITS)
    before=ast.parse(postroute);after=ast.parse(numerical)
    defs=lambda tree:{n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    a,z=defs(before),defs(after);assert set(a)==set(z)
    for name in a:
        if name!='main':assert ast.dump(a[name],include_attributes=False)==ast.dump(z[name],include_attributes=False)
    previous=next(n for n in a['main'].body if isinstance(n,ast.Try))
    current=next(n for n in z['main'].body if isinstance(n,ast.Try))
    for field in ('body','handlers','orelse'):
        assert ast.dump(ast.Module(body=getattr(previous,field),type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=getattr(current,field),type_ignores=[]),include_attributes=False)
    return geometry,numerical,dict(geometry_old_sha256=GEOMETRY_SHA,
        geometry_derived_sha256=hashlib.sha256(geometry).hexdigest(),
        geometry_exact_reversible_edits=5,geometry_acquisition_edits=2,
        geometry_terminal_orchestration_edits=3,postroute_original_sha256=POSTROUTE_SHA,
        postroute_derived_sha256=hashlib.sha256(numerical).hexdigest(),
        postroute_exact_reversible_edits=3,postroute_successful_body_and_handlers_AST_exact=True,
        numerical_non_main_functions_AST_exact=True,
        original_topology_1691_clock_antenna_disconnect_RC_STA_predicates_preserved=True,
        orchestration_scope='Atomic result writer and independent terminal evidence only; no numerical predicate changed')
@contextlib.contextmanager
def original_input_context():
    values={'NSSOC_INPUT_PACKAGE':json.dumps(admission.INPUT_PACKAGE),
        'NSSOC_COMPLETED_DRT':json.dumps(admission.require_terminal_binding(admission.methods())['source'])}
    prior={k:os.environ.get(k)for k in values}
    # Refuse a preexisting old/different package rather than silently replacing it.
    for key,value in prior.items():
        if value is not None:assert admission.json_value(value)==admission.json_value(values[key])
    try:
        os.environ.update(values);yield
    finally:
        for key,value in prior.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
