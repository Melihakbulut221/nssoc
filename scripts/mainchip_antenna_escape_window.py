#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact read-only diagnostic input; a rejected trial is never a production candidate."""
import re
NET="$abc$1804206$new_n41321"
FOREIGN="net36953"
NEW="NSSOC_ANT_TRIAL_fanout36953"
WINDOW=(95000,501000,102000,512500)
INPUT=dict(bytes=213428829,sha256="72d382ab18e905d13fef8145b70944e681a7a50c16bad0848616652fa93fc0ee")
MEMBER="work/single-antenna-trial/inserted.odb"
RUN=41001185417
SOURCE="30c8f7412d439692f3445d9b41937a3ffc8a0e9f"
RELEASE=428643939
TAG="cloud-results-41001185417-1-mainchip-single-antenna-trial"
ASSETS={
 "candidate-outputs.json":dict(id=690925794,bytes=10394,sha256="fa06886f5819d4758735e2f5ddf77c5ecad75517111799e8180290914ceeea23"),
 "candidate-parts.json":dict(id=690925883,bytes=316,sha256="20ec5eeb939a0ac55b96753b9c4e88f3f3ded22f9da7b0710a972475f82e765f"),
 "candidate-native.tar.gz.part000":dict(id=690926007,bytes=367635548,sha256="5eaf970597f1c739c5ea36626f847b620c30c2e6a3c46f0a8fcaae1e7e75eb4f")}
JOBS={"source-controls":"success","preserve-job-log":"success","trial":"success",
 "preserve-antenna-job-logs":"success","ownership":"skipped","antenna-readback":"skipped","candidate":"skipped"}
def require(value,message):
    if not value:raise AssertionError(message)
def rect(b):
    require(isinstance(b,(list,tuple))and len(b)==4 and all(type(x)is int for x in b),"integer box")
    require(b[0]<b[2]and b[1]<b[3],"positive box")
    return b
def intersects(a,b):
    rect(a);rect(b)
    return a[0]<=b[2]and b[0]<=a[2]and a[1]<=b[3]and b[1]<=a[3]
def producer_binding(run,jobs,info,ref):
    require(run["id"]==RUN and run["head_sha"]==SOURCE and run["head_branch"]=="codex/mainchip-net459-diode-prune"
      and run["run_attempt"]==1 and run["status"]=="completed"and run["conclusion"]=="success"
      and run["event"]=="workflow_dispatch"and run["workflow_id"]==401215446,"actual trial run")
    rows=jobs["jobs"]
    require(jobs["total_count"]==len(rows)==len(JOBS)and len({r["name"]for r in rows})==len(rows),"complete unique trial jobs")
    require({j["name"]:j["conclusion"]for j in rows}==JOBS,"trial job conclusions")
    require(all(j["status"]=="completed"and j["head_sha"]==SOURCE and j["run_id"]==RUN for j in rows),"terminal trial source")
    require(info["id"]==RELEASE and info["tag_name"]==TAG and info["target_commitish"]==SOURCE
      and info["draft"]is False and info["prerelease"]is True,"trial release")
    require(ref["ref"]=="refs/tags/"+TAG and ref["object"]==dict(type="commit",sha=SOURCE,url=ref["object"]["url"]),"exact commit ref")
    assets=info["assets"]
    require(len(assets)==len(ASSETS)and {a["name"]for a in assets}==set(ASSETS),"complete asset names")
    require(len({a["id"]for a in assets})==len(assets),"unique asset ids")
    for a in assets:
        pin=ASSETS[a["name"]]
        require(a["id"]==pin["id"]and a["size"]==pin["bytes"]and a.get("digest")=="sha256:"+pin["sha256"],"asset integrity")
    return dict(run=RUN,source=SOURCE,release=RELEASE,diagnostic_input=INPUT,
      candidate_rejected=True,original_production_ODB_unchanged=True,native_input_is_inserted_before_branch=True,
      physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
