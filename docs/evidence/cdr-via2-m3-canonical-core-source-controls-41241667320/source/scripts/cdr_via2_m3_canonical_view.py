#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Candidate-bound canonical view projection; native execution deliberately disabled."""
import ast,hashlib,json,os,re,subprocess
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-via2-m3-fresh-rc-source-v1'
CONFIG='scripts/cdr-via2-m3-canonical-view-inputs.json'
MANIFEST='scripts/cdr-via2-m3-canonical-view-pins.json'
TOP='nssoc_cdr_pd500_resistor_v59'
WORKERS=('probe01.py','locate01.py','anchors01.py','dedup01.py')
WIRE_SOURCE='docs/evidence/cdr-v59-tail-exact-wire-methods-20261026/'
FLAGS=dict(native_executed=False,rc_extracted=False,electrical_accepted=False,physical_accepted=False,full_phy_accepted=False)
def require(ok,message):
    if not ok:raise AssertionError(message)
def encode(v):return (json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def fingerprint(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def name(value):
    require(type(value)is str and value and '\\'not in value,'relative member text')
    p=PurePosixPath(value)
    require(not p.is_absolute()and str(p)==value and '..'not in p.parts and '.'not in p.parts,'canonical relative member')
    return value
def regular(root,relative):
    root=Path(root);p=root/name(relative)
    require(root.is_absolute()and root.resolve()==root and not root.is_symlink(),'canonical owned root')
    require(p.resolve()==p and p.is_file()and not p.is_symlink(),'regular exact member: '+relative)
    return p
def inventory(root):
    require(root.is_dir()and root.resolve()==root and not root.is_symlink(),'new owned input directory')
    result={}
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink()and(p.is_dir()or p.is_file()),'no links/specials')
        if p.is_file():result[name(p.relative_to(root).as_posix())]=fingerprint(p.read_bytes())
    return result
def exact_inputs(root,expected):
    require(expected and all(set(p)=={'bytes','sha256'}and type(p['bytes'])is int and p['bytes']>=0 and re.fullmatch('[0-9a-f]{64}',p['sha256'])for p in expected.values()),'complete typed member pins')
    require(inventory(root)==expected,'all input members/bytes exactly authenticated')
def write_new(root,relative,raw):
    p=root/name(relative);p.parent.mkdir(parents=True,exist_ok=True)
    require(p.resolve()==p and not p.exists()and not p.is_symlink(),'new exact output path')
    with p.open('xb')as f:f.write(raw)
    require(p.read_bytes()==raw,'copy changed bytes')
def source_guard():
    e=os.environ
    require(e.get('GITHUB_ACTIONS')=='true'and e.get('RUNNER_ENVIRONMENT')=='github-hosted'and e.get('RUNNER_OS')=='Linux','hosted source controls only')
    require(e.get('GITHUB_REPOSITORY')=='Melihakbulut221/nssoc'and e.get('GITHUB_EVENT_NAME')=='workflow_dispatch','manual repository')
    require(e.get('GITHUB_REF')=='refs/heads/'+BRANCH and e.get('GITHUB_JOB')=='source-controls'and e.get('GITHUB_RUN_ATTEMPT')=='1','exact isolated source job')
    require(e.get('GITHUB_WORKFLOW_REF')=='Melihakbulut221/nssoc/.github/workflows/cloud-evidence-summary.yml@refs/heads/'+BRANCH and Path.cwd()==ROOT,'exact registered workflow and actual cwd')
    head=e.get('GITHUB_SHA','');require(re.fullmatch('[0-9a-f]{40}',head)and e.get('APPROVED_SOURCE')==head,'explicit exact source')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==head,'actual checkout')
    raw=regular(ROOT,MANIFEST).read_bytes();require(raw==subprocess.check_output(['git','show',head+':'+MANIFEST],cwd=ROOT),'immutable source manifest')
    m=json.loads(raw)
    for n,pin in m['files'].items():require(fingerprint(regular(ROOT,n).read_bytes())==pin,'source pin '+n)
    c=json.loads(regular(ROOT,CONFIG).read_bytes())
    require(c['schema']=='cdr-via2-m3-canonical-view-source-v1'and c['branch']==BRANCH and c['source_controls_authorized']is True,'source-only contract')
    require(c['physical_binding']is None and all(c[k]is False for k in ('native_acquisition_authorized','view_execution_authorized','rc_extraction_authorized','electrical_simulation_authorized','electrical_accepted','physical_accepted','full_phy_accepted')),'no pending physical identity or native authority')
    require(c['candidate']['gds']==dict(bytes=998644,sha256='42ed5bcd567518786b718248947771172e9f5cc419d0aaa8fc8c49d8cfa4e876'),'actual generated candidate pin')
    return c

def wire_coverage(source_root,workers):
    require(set(workers)=={WIRE_SOURCE+n for n in WORKERS},'all four frozen wire workers')
    for n,pin in workers.items():require(fingerprint(regular(source_root,n).read_bytes())==pin,'unchanged wire worker')
    text=regular(source_root,WIRE_SOURCE+'probe01.py').read_text();tree=ast.parse(text);constants={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name)and target.id in ('METALS','VIAS'):constants[target.id]=ast.literal_eval(node.value)
    require(constants==dict(METALS=[8,10,30,50,67,126,134],VIAS=[19,29,49,66,125,133]),'whole seven-metal/six-via stack')
    require('for layer in METALS+VIAS:'in text and 'for a,v,b in zip(METALS,VIAS,METALS[1:]):'in text,'complete conductor export/connectivity source')
    require('e.connect(regions[a],regions[v]);e.connect(regions[v],regions[b])'in text,'via connects both adjacent metals')
    require("assert(piece-cache[key]).is_empty()"in text and "'Native metal net split'"in text,'whole-partition ownership/split gates retained')
    return dict(via2_layer=29,metal3_layer=30,adjacent_metals=[10,30],all_conductor_layers=constants,workers=workers,source_coverage_only=True,**FLAGS)

def project_view(reference,physical,out,source_root,reference_members,physical_members,prefix,candidate_pin,workers):
    """Pure projection primitive. Production admission is separate and remains disabled.

    Callers must supply authenticated complete immutable input maps. Hosted tests
    use explicit synthetic files; no source-only result is a native qualification.
    """
    reference=Path(reference);physical=Path(physical);out=Path(out);source_root=Path(source_root)
    require(reference!=physical and not reference.is_relative_to(physical)and not physical.is_relative_to(reference),'disjoint immutable input roots')
    require(out.is_absolute()and out.resolve()==out and not out.exists()and not out.is_symlink(),'new canonical view output')
    require(not out.is_relative_to(reference)and not out.is_relative_to(physical)and not reference.is_relative_to(out)and not physical.is_relative_to(out),'output outside both inputs')
    exact_inputs(reference,reference_members);exact_inputs(physical,physical_members);coverage=wire_coverage(source_root,workers)
    name(prefix.rstrip('/'));require(prefix.endswith('/'),'exact reference namespace')
    parent={n:p for n,p in reference_members.items()if n.startswith(prefix+'parent/')}
    require(parent and any('/parent/inputs/'in n for n in parent),'complete original reference children retained')
    oldmeta=json.loads(regular(reference,prefix+'parent/layout/result.json').read_bytes())
    newmeta=json.loads(regular(physical,'native/layout/result.json').read_bytes())
    require(len(oldmeta['placements'])==16 and sum(oldmeta['primitive_census'].values())==500,'complete original primitive placement metadata')
    require(len(oldmeta['ports'])==25 and oldmeta['ports']==newmeta['ports'],'all25 exact public ports')
    layout_names=(TOP+'.gds',TOP+'.lef','schematic.cir')
    require(physical_members['native/layout/'+TOP+'.gds']==candidate_pin,'exact generated candidate GDS')
    require(newmeta['outputs']=={n:physical_members['native/layout/'+n]['sha256']for n in layout_names},'actual layout result binds all three outputs')
    old_flat={n.removeprefix(prefix+'parent/physical/lvs_flat/')for n in parent if n.startswith(prefix+'parent/physical/lvs_flat/')}
    new_flat={n.removeprefix('native/physical/lvs_flat/')for n in physical_members if n.startswith('native/physical/lvs_flat/')}
    require(old_flat==new_flat and {'audit.json','result.lvsdb','extracted.cir'}<=new_flat,'complete actual flat LVS member set')
    audit=json.loads(regular(physical,'native/physical/lvs_flat/audit.json').read_bytes())
    require(audit['status']=='PASS within comparison scope','actual flat LVS audit status')
    out.mkdir(parents=True)
    for n in parent:
        target=n.removeprefix(prefix)
        if target.startswith('parent/physical/lvs_flat/')or target.startswith('parent/layout/'):continue
        write_new(out,target,regular(reference,n).read_bytes())
    for n in layout_names:write_new(out,'parent/layout/'+n,regular(physical,'native/layout/'+n).read_bytes())
    for n in sorted(new_flat):write_new(out,'parent/physical/lvs_flat/'+n,regular(physical,'native/physical/lvs_flat/'+n).read_bytes())
    write_new(out,'provenance/original-reference-layout-result.json',regular(reference,prefix+'parent/layout/result.json').read_bytes())
    write_new(out,'provenance/original-candidate-layout-result.json',regular(physical,'native/layout/result.json').read_bytes())
    meta={k:oldmeta[k]for k in ('source_plan','placements','primitive_census','ports')}
    meta.update(status='DERIVED_VIA2_M3_CANONICAL_VIEW_METADATA_NO_NATIVE_QUALIFICATION',inputs={str(reference/(prefix+'parent/layout/result.json')):reference_members[prefix+'parent/layout/result.json']['sha256'],str(physical/'native/layout/result.json'):physical_members['native/layout/result.json']['sha256']},outputs={n:physical_members['native/layout/'+n]['sha256']for n in layout_names},original_metadata_retained=True,**FLAGS)
    write_new(out,'parent/layout/result.json',encode(meta))
    for n in WORKERS:write_new(out,'wire/'+n,regular(source_root,WIRE_SOURCE+n).read_bytes())
    exact_inputs(reference,reference_members);exact_inputs(physical,physical_members)
    result=dict(status='PROJECTED_CANDIDATE_VIEW_NOT_EXECUTED_OR_QUALIFIED',candidate=candidate_pin,reference_member_count=len(reference_members),physical_member_count=len(physical_members),all_reference_children_copied=True,original_candidate_result_rewritten=False,derived_metadata_separate=True,wire_coverage=coverage,outputs=inventory(out),**FLAGS)
    write_new(out,'projection.json',encode(result));return result

def authorize_native(*args,**kwargs):
    raise AssertionError('NATIVE_DISABLED: real physical binding and a separately reviewed execution adapter are required')
if __name__=='__main__':authorize_native()
