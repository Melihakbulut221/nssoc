#!/usr/bin/env python3
"""Cloud-only12-divider-width trial. No acceptance thresholds changed."""
import argparse,json,os,platform,shutil,subprocess,traceback,types
from pathlib import Path
import cloud_cdr_sampler_load as original
import cdr_divider_width_candidate as candidate
ROOT=original.ROOT
OUT=original.OUT
DERIVED=original.DERIVED
MANIFEST="scripts/cdr-divider-width-host-pins.json"
ARCHIVED="docs/evidence/cdr-divider-drive-inputs/original-workflow.txt"
WORKFLOW=".github/workflows/cloud-evidence-summary.yml"
require=original.require
def source_gate():
    import numpy
    require(os.environ.get("GITHUB_ACTIONS")=="true" and os.environ["GITHUB_RUN_ATTEMPT"]=="1","hosted first attempt only")
    require(os.environ["GITHUB_REPOSITORY"]==original.REPO and os.environ["GITHUB_EVENT_NAME"]=="workflow_dispatch","exact repository and explicit dispatch")
    require(platform.python_version_tuple()[:2]==("3","12") and numpy.__version__=="2.3.3","qualified interpreter and numpy")
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    require(head==os.environ["GITHUB_SHA"],"exact checkout")
    prior=json.loads((ROOT/"scripts/cdr-sampler-load-host-pins.json").read_bytes())
    pins=json.loads((ROOT/MANIFEST).read_bytes())
    require(pins["baseline_source"]=="d638e0e3cd15a0ee930212c27ab1f238b5085237","exact prior source")
    for path,pin in prior["files"].items():
        actual=ARCHIVED if path==WORKFLOW else path
        require(original.core.file_pin(ROOT/actual)==pin,"immutable original source "+path)
    divider=json.loads((ROOT/"scripts/cdr-divider-drive-host-pins.json").read_bytes())
    require(pins["divider_source"]=="3a6f1f9e3b30f97ffae87f43cf0f7f00e2d2ab43","exact divider parent")
    for path,pin in divider["files"].items():
        actual="docs/evidence/cdr-divider-width-inputs/divider-workflow.txt" if path==WORKFLOW else path
        require(original.core.file_pin(ROOT/actual)==pin,"immutable divider source "+path)
    for path,pin in pins["files"].items():
        require(original.core.file_pin(ROOT/path)==pin,"exact supplemental source "+path)
    return dict(source=head,run_id=int(os.environ["GITHUB_RUN_ID"]),attempt=1)
NS=dict(original.__dict__)
for key,value in original.__dict__.items():
    if isinstance(value,types.FunctionType) and value.__globals__ is original.__dict__:
        NS[key]=candidate.cloned(value,NS)
BASE_ADMIT=NS["admit"]
BASE_PUBLISH=NS["publish"]
def admit(ctx):
    ident=os.environ.get("QUALIFIED_CONTROLS","")
    require(ident.isdigit() and int(ident)!=ctx["run_id"],"independent controls run required")
    run=original.api("actions/runs/"+ident)
    jobs=original.api("actions/runs/"+ident+"/jobs?per_page=100")
    require(run["head_sha"]==ctx["source"] and run["status"]=="completed" and run["conclusion"]=="success" and run["run_attempt"]==1 and run["event"]=="workflow_dispatch","qualified separate exact-source controls")
    require(run["head_branch"]=="codex/cdr-divider-width4" and run["path"]==WORKFLOW,"exact controls branch and workflow")
    controls=[j for j in jobs["jobs"]if j["name"]=="source-controls"]
    require(len(controls)==1 and controls[0]["conclusion"]=="success" and all(s["conclusion"]in("success","skipped")for s in controls[0]["steps"]),"complete separate controls")
    require(all(j["conclusion"]=="skipped" for j in jobs["jobs"]if j["name"]=="simulate"),"separate qualification did not simulate")
    original.save(DERIVED/"independent-controls.json",dict(run=run,jobs=jobs))
    BASE_ADMIT(ctx)
def publish():
    source_gate()
    pins=json.loads((ROOT/MANIFEST).read_bytes())
    out=DERIVED/"supplemental-source";out.mkdir(exist_ok=False)
    for name in [*pins["files"],MANIFEST]:
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    original.save(DERIVED/"source-mapping.json",dict(unchanged_prior_source="d638e0e3cd15a0ee930212c27ab1f238b5085237",archived_original_workflow=ARCHIVED,actual_workflow=WORKFLOW,supplemental_manifest=MANIFEST,original_gates_retained=True))
    BASE_PUBLISH()
NS.update(source_gate=source_gate,admit=admit,candidate=candidate)
if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--publish",action="store_true");args=parser.parse_args()
    try:
        if args.publish:publish()
        else:NS["simulate"]()
    except BaseException:
        DERIVED.mkdir(parents=True,exist_ok=True)
        (DERIVED/("publication-failure.txt"if args.publish else"failure.txt")).write_text(traceback.format_exc())
        raise
