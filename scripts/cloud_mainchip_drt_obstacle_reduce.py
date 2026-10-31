#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-bound hosted reducer entry. This first revision never acquires inputs."""
import argparse,os,re,subprocess
from pathlib import Path
import mainchip_terminal_readback as q
ROOT=Path(__file__).resolve().parents[1]
BRANCH="codex/mainchip-drt-obstacle-reduction-v1"
GROUP="mainchip-drt-obstacle-reduction"
MANIFEST="scripts/mainchip-drt-obstacle-reduce-source.json"
CONFIG="scripts/mainchip-drt-obstacle-reduce-inputs.json"
def source_gate(mode):
    e=os.environ
    q.require(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted","GitHub hosted only")
    q.require(e.get("GITHUB_REPOSITORY")==q.REPO and e.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and e.get("GITHUB_REF")=="refs/heads/"+BRANCH,"exact actual manual source branch")
    q.require(mode in("controls","analysis")and e.get("MODE")==mode and e.get("GITHUB_JOB")==("source-controls"if mode=="controls"else"analysis"),"exact job/mode")
    head=e["GITHUB_SHA"];q.require(re.fullmatch("[0-9a-f]{40}",head)is not None and e.get("APPROVED_SOURCE")==head and e.get("GITHUB_RUN_ATTEMPT")=="1","exact approved source and first attempt")
    q.require(subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==head,"actual checkout")
    raw=(ROOT/MANIFEST).read_bytes()
    q.require(raw==subprocess.check_output(["git","show",head+":"+MANIFEST],cwd=ROOT),"exact committed manifest bytes")
    m=q.decode(raw);q.require(m["schema"]=="mainchip-obstacle-reduction-source-v1"and m["native_execution_authorized"]is False and m["routing_authorized"]is False,"derived-only source scope")
    for name,p in m["files"].items():
        q.valid_name(name);q.filepin(p);path=ROOT/name
        q.require(path.is_file()and not path.is_symlink()and q.pin(path)==p,"complete protected source "+name)
    c=q.decode((ROOT/CONFIG).read_bytes())
    q.require(c["schema"]=="mainchip-obstacle-reduction-inputs-v1"and c["native_execution_authorized"]is False and c["routing_authorized"]is False,"derived-only input scope")
    q.require(c["analysis_authorized"]is m["analysis_authorized"]is False,"this revision is source-only")
    return head
def actual_context():
    source_gate("analysis")
    raise ValueError("Actual report acquisition is disabled until the complete hosted adapter is reviewed")
def main():
    p=argparse.ArgumentParser();p.add_argument("--controls",action="store_true");args=p.parse_args()
    if args.controls:print(source_gate("controls"))
    else:actual_context()
if __name__=="__main__":main()
