#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted real projection tests with explicit synthetic files; never native acquisition."""
import ast,copy,json,os,tempfile,traceback
from pathlib import Path
import cdr_via2_m3_canonical_view as v
ROOT=v.ROOT

def reject(fn):
    try:fn()
    except(AssertionError,FileNotFoundError,KeyError,ValueError):return
    raise AssertionError('Invalid projection accepted')

def fixture(root,c):
    reference=root/'reference';physical=root/'physical';reference.mkdir();physical.mkdir()
    prefix=c['reference']['prefix']
    for n in c['reference']['complete_members']:
        v.write_new(reference,n,('EXPLICIT_SYNTHETIC_REFERENCE_ONLY '+n+'\n').encode())
    meta=dict(source_plan='EXPLICIT_SYNTHETIC_REFERENCE_PLAN',placements=[dict(explicit_synthetic=i)for i in range(16)],primitive_census=c['invariant_observables']['native_primitive_census'],ports=['P'+str(i)for i in range(25)],outputs={})
    old=reference/(prefix+'parent/layout/result.json');old.write_bytes(v.encode(meta))
    for n in (v.TOP+'.gds',v.TOP+'.lef','schematic.cir'):
        v.write_new(physical,'native/layout/'+n,('EXPLICIT_SYNTHETIC_NOT_NATIVE '+n+'\n').encode())
    flat=[n.removeprefix(prefix+'parent/physical/lvs_flat/')for n in c['reference']['complete_members']if n.startswith(prefix+'parent/physical/lvs_flat/')]
    for n in flat:v.write_new(physical,'native/physical/lvs_flat/'+n,('EXPLICIT_SYNTHETIC_FLAT_ONLY '+n+'\n').encode())
    (physical/'native/physical/lvs_flat/audit.json').write_bytes(v.encode(dict(status='PASS within comparison scope',fixture_only=True)))
    nm=dict(ports=meta['ports'],inputs={'synthetic-only': '0'*64},outputs={n:v.fingerprint((physical/'native/layout'/n).read_bytes())['sha256']for n in (v.TOP+'.gds',v.TOP+'.lef','schematic.cir')},explicit_synthetic=True)
    v.write_new(physical,'native/layout/result.json',v.encode(nm))
    return reference,physical,v.inventory(reference),v.inventory(physical)

def controls(c):
    cases=[]
    with tempfile.TemporaryDirectory(prefix='explicit-synthetic-canonical-view-')as temporary:
        base=Path(temporary).resolve();reference,physical,rm,pm=fixture(base,c);prefix=c['reference']['prefix'];candidate=pm['native/layout/'+v.TOP+'.gds'];workers=c['wire_workers']
        def project(out,reference_map=rm,physical_map=pm,pin=candidate):
            return v.project_view(reference,physical,out,ROOT,reference_map,physical_map,prefix,pin,workers)
        result=project(base/'positive')
        v.require(result['native_executed']is result['rc_extracted']is result['full_phy_accepted']is False,'source-only result scope')
        for n in (v.TOP+'.gds',v.TOP+'.lef','schematic.cir'):
            v.require((base/'positive/parent/layout'/n).read_bytes()==(physical/'native/layout'/n).read_bytes(),'actual candidate copy')
        v.require((base/'positive/provenance/original-candidate-layout-result.json').read_bytes()==(physical/'native/layout/result.json').read_bytes(),'original candidate result preserved byte-identically')
        v.require((base/'positive/provenance/original-reference-layout-result.json').read_bytes()==(reference/(prefix+'parent/layout/result.json')).read_bytes(),'original reference metadata preserved byte-identically')
        parents=[n for n in rm if n.startswith(prefix+'parent/')and not n.startswith(prefix+'parent/layout/')and not n.startswith(prefix+'parent/physical/lvs_flat/')]
        for n in parents:v.require((base/'positive'/n.removeprefix(prefix)).read_bytes()==(reference/n).read_bytes(),'all original child references')
        for n in v.WORKERS:v.require((base/'positive/wire'/n).read_bytes()==(ROOT/v.WIRE_SOURCE/n).read_bytes(),'unchanged numerical source')
        v.require(not any(n.startswith('wire/rc')or n.startswith('wire/native05')for n in result['outputs']),'old graph or RC not misrepresented as new')
        cases.append('complete330_reference_projection_all_children_new_layout_new_flat_and_frozen_four_workers')
        cases.append('original_candidate_and_reference_result_bytes_retained_separate_from_derived_metadata')
        cases.append('old_native_graph_and_RC_results_not_copied_as_fresh')
        for label,map_kind,mutate in[
          ('reference-missing-member','reference',lambda d:d.pop(next(iter(d)))),
          ('reference-extra-member','reference',lambda d:d.update({'invented':dict(bytes=0,sha256='0'*64)})),
          ('reference-wrong-hash','reference',lambda d:d[next(iter(d))].update(sha256='0'*64)),
          ('physical-missing-member','physical',lambda d:d.pop(next(iter(d)))),
          ('physical-wrong-byte-count','physical',lambda d:d[next(iter(d))].update(bytes=999))]:
            bad=copy.deepcopy(rm if map_kind=='reference'else pm);mutate(bad)
            reject(lambda:project(base/label,reference_map=bad)if map_kind=='reference'else project(base/label,physical_map=bad));cases.append(label)
        reject(lambda:project(base/'wrong-candidate',pin=dict(candidate,sha256='0'*64)));cases.append('wrong-generated-candidate')
        reject(lambda:project(base/'positive'));cases.append('existing-output-refused')
        reject(lambda:project(reference/'within-input'));cases.append('output-inside-immutable-input-refused')
        flat=physical/'native/physical/lvs_flat/audit.json';original=flat.read_bytes();flat.write_bytes(v.encode(dict(status='FAIL',fixture_only=True)))
        reject(lambda:project(base/'failed-flat',physical_map=v.inventory(physical)));flat.write_bytes(original);cases.append('failed-flat-LVS-record-refused')
        layout=physical/'native/layout/result.json';original=layout.read_bytes();bad=json.loads(original);bad['ports'][0]='OTHER';layout.write_bytes(v.encode(bad))
        reject(lambda:project(base/'changed-port',physical_map=v.inventory(physical)));layout.write_bytes(original);cases.append('changed-public-port-refused')
        bad=json.loads(original);bad['outputs'][v.TOP+'.gds']='0'*64;layout.write_bytes(v.encode(bad))
        reject(lambda:project(base/'changed-output',physical_map=v.inventory(physical)));layout.write_bytes(original);cases.append('layout-output-pin-mismatch-refused')
        missing=physical/'native/physical/lvs_flat/deck.log';saved=missing.read_bytes();missing.unlink()
        reject(lambda:project(base/'partial-flat',physical_map=v.inventory(physical)));missing.write_bytes(saved);cases.append('partial-native-flat-LVS-set-refused')
        extra=reference/'extra-link';extra.symlink_to(physical/'native/layout'/(v.TOP+'.gds'))
        reject(lambda:project(base/'input-link'));extra.unlink();cases.append('input-symlink-refused')
        v.exact_inputs(reference,rm);v.exact_inputs(physical,pm)
        v.require(c['physical_binding']is None,'no fabricated pending physical identity')
        reject(lambda:v.authorize_native(c));cases.append('native-entry-unconditionally-disabled')
        enabled=copy.deepcopy(c);enabled['view_execution_authorized']=True;enabled['physical_binding']=dict(explicit_synthetic=True)
        reject(lambda:v.authorize_native(enabled));cases.append('cannot-enable-native-through-config-flip')
        return dict(cases=cases,synthetic_reference_members=len(rm),synthetic_physical_members=len(pm),copied_original_parent_members=len(parents),source_coverage=v.wire_coverage(ROOT,workers),all_inputs_unchanged=True)

def main():
    c=v.source_guard();out=ROOT/'canonical-view-source-controls';v.require(not out.exists(),'new source controls output');out.mkdir();primary=None
    try:
        for n in c['wire_workers']:ast.parse(v.regular(ROOT,n).read_text())
        result=controls(c)
        result.update(status='PASS_CANONICAL_VIEW_SOURCE_CONTROLS_WITH_SYNTHETIC_BYTES_ONLY',source=os.environ['GITHUB_SHA'],run_id=int(os.environ['GITHUB_RUN_ID']),attempt=1,test_count=len(result['cases']),passed=True,no_actual_candidate_or_model_acquired=True,physical_binding_absent=True,**v.FLAGS)
        v.source_guard()
    except BaseException as error:
        primary=error;result=dict(status='FAIL_CANONICAL_VIEW_SOURCE_CONTROLS',passed=False,error=repr(error),traceback=traceback.format_exc(),**v.FLAGS)
    raw=v.encode(result);(out/'result.json').write_bytes(raw);print(raw.decode(),flush=True)
    if primary is not None:raise primary
if __name__=='__main__':main()
