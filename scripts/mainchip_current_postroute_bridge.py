#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact original geometry bridge; successful current producer must be separately bound."""
import ast,contextlib,hashlib,json,os
import mainchip_current_postroute_admission as admission
GEOMETRY='scripts/cloud_mainchip_route12_postroute_geometry.py'
POSTROUTE='scripts/cloud_mainchip_route12_postroute.py'
GEOMETRY_SHA='52de46aacf9b97ab17ac56560efef838d149a746a2dd09a6f1af87ed41be0c97'
POSTROUTE_SHA='c6335c535959286b7f77c3aaf6a5ab631640557c8453079a80dd97c97f58701f'
EDITS=json.loads("[[\"from cloud_mainchip_route12_drt_continuation import log_proof\\n\",\"from cloud_mainchip_route12_drt_continuation import log_proof\\nfrom mainchip_current_postroute_admission import consume\\n\"],[\"        selected=json.loads(os.environ['NSSOC_COMPLETED_DRT'])\\n        live=api('actions/runs/'+str(selected['run']))\\n        assert live['status']=='completed'and live['conclusion']=='success','Never consume unfinished route'\\n        names=['work/detailed-route.odb','work/detailed-route.drc','work/native.log','work/boots.log','work/before-guide-read.odb','work/drt-done']\\n        actual,aproof=reports.restore_report(selected['group'],selected['run'],selected['summary_sha256'],selected['parts_sha256'],OUT/'routed',names)\\n        portable=json.loads((ROOT/'docs/evidence/mainchip-portable-runtime-pass-20261020.json').read_text())\\n        validate(selected,live,actual,portable['report']['image_id'])\\n        controller='scripts/cloud_mainchip_route12_drt'+('_continuation'if 'continuation' in live['path']else'')+'.py'\\n        assert source_hash(controller,selected['source_head'])==selected['controller_sha256']==sha(ROOT/controller)\\n        native=log_proof((OUT/'routed/work/native.log').read_bytes(),(OUT/'routed/work/boots.log').read_bytes())\\n        assert native==actual['native_log']\\n        drc=OUT/'routed/work/detailed-route.drc'\\n        if native['completed_violation_counts'][-1]==0:\\n            assert not drc.read_text().strip(),'Zero native count but nonempty final DRC report'\\n        else:\\n            assert drc.read_text().strip(),'Nonzero native count but empty final DRC report'\\n        r['native_drc_report']=dict(sha256=sha(drc),bytes=drc.stat().st_size,\\n            final_native_count=native['completed_violation_counts'][-1],zero_count_and_empty_report_consistent=True)\\n        assert(OUT/'routed/work/drt-done').read_text().strip()\\n        assert sha(OUT/'routed/work/before-guide-read.odb')==sha(a)\\n        b=OUT/'routed/work/detailed-route.odb';assert sha(b)==actual['routed_odb_sha256']\\n        r.update(route_complete=True,completed_route_source=aproof,completed_route_descriptor=selected,\\n            global_source=bproof,handoff_source=hproof,candidate_netlist_path=str(nl),\\n            candidate_netlist_sha256=sha(nl),reported_native_drt_violation_counts=native['completed_violation_counts'])\\n\",\"        b,aproof=consume(ROOT,OUT)\\n        r['native_drc_report']=aproof['final_DRT']\\n        r.update(route_complete=True,completed_route_source=aproof,\\n            completed_route_descriptor=aproof['envelope'],global_source=bproof,handoff_source=hproof,\\n            candidate_netlist_path=str(nl),candidate_netlist_sha256=sha(nl),\\n            reported_native_drt_violation_counts=[aproof['final_original_class_DRT_markers']],\\n            repaired_original_class_admission=aproof)\\n\"]]")
def derive(old,postroute):
    assert hashlib.sha256(old).hexdigest()==GEOMETRY_SHA
    assert hashlib.sha256(postroute).hexdigest()==POSTROUTE_SHA
    original=old.decode();new=original
    for before,after in EDITS:
        assert new.count(before)==1;new=new.replace(before,after)
    inverse=new
    for before,after in reversed(EDITS):
        assert inverse.count(after)==1;inverse=inverse.replace(after,before)
    assert inverse==original
    old_ast=ast.parse(original);new_ast=ast.parse(new)
    old_functions={n.name:ast.dump(n,include_attributes=False)for n in old_ast.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    new_functions={n.name:ast.dump(n,include_attributes=False)for n in new_ast.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    assert old_functions.keys()==new_functions.keys()=={'main'}
    # The exact literal replacement, inverse and unchanged surrounding source bind the main body.
    return new.encode(),postroute,dict(geometry_old_sha256=GEOMETRY_SHA,
        geometry_derived_sha256=hashlib.sha256(new.encode()).hexdigest(),
        exact_reversible_edits=2,postroute_byte_exact_sha256=POSTROUTE_SHA,
        original_topology_1691_clock_antenna_disconnect_RC_STA_bytes_preserved=True)
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
