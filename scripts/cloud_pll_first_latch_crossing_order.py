#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact proven selected-cache replay plus one bounded observer; no new native trajectory."""
import ast, hashlib, inspect, json, os
from pathlib import Path
import cloud_pll_first_latch_cache_replay as frozen
import pll_first_latch_crossing_order as crossing
import check_pll_first_latch_crossing_order as checker

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"cloud-pll-first-latch-crossing-order"
METHOD="scripts/pll-first-latch-crossing-order-methods.json"
BASE_SHA="d4f6ce5fb143dfbcae19967893fd78bf767abcacd3e5ffa7565e20c9c61fe182"
QUALIFIED_RUN=40114471619
QUALIFIED_SOURCE="a4bf51c1219fe521f34bb477035cdfc2a5012335"
QUALIFIED_SUMMARY="57029d1ac6295c8310d687da3647297bd0c426237671ba649b6c3598be1c73a7"

def methods():
    old=frozen.methods()
    m=json.loads((ROOT/METHOD).read_text())
    for p,h in m["protected"].items():assert frozen.file_sha(ROOT/p)==h,p
    assert m["native_simulation_allowed"]is m["full_capture_reread_allowed"]is False
    return m

def qualified_replay():
    run=frozen.api("actions/runs/"+str(QUALIFIED_RUN))
    assert run["id"]==QUALIFIED_RUN and run["head_sha"]==QUALIFIED_SOURCE
    assert run["run_attempt"]==1 and run["status"]=="completed"and run["conclusion"]=="success"
    assert run["head_branch"]=="codex/pll-first-latch-cache-replay"
    assert run["path"]==".github/workflows/pll-first-latch-cache-replay-cloud.yml"
    b=frozen.small(672845958,QUALIFIED_SUMMARY,27813);r=json.loads(b)
    assert r["source_head"]==QUALIFIED_SOURCE and int(r["run_id"])==QUALIFIED_RUN
    assert r["status"]=="PASS_EXACT_FIRST_LATCH_CACHE_REPLAY_ORIGINAL_PLL_ACQUISITION_REMAINS_REJECTED"
    assert r["diagnosis_sha256"]==crossing.DIAG_SHA and r["original_reproduction"]==frozen.REPRODUCTION
    assert r["cache"]["rows"]==3201410 and r["cache"]["columns"]==131
    assert not any(r[k]for k in ("native_activation_performed","full_capture_reread","acquisition_accepted",
                                 "full_device_safety_accepted","full_phy_accepted","large_cache_republished"))
    return dict(run=QUALIFIED_RUN,source=QUALIFIED_SOURCE,summary_asset=672845958,
                summary_sha256=QUALIFIED_SUMMARY,diagnosis_sha256=crossing.DIAG_SHA)

def controls(s,m):
    return dict(original=frozen.controls(s,m),crossing_order=checker.controls(),
                native_simulation_started=False)

def observe(data,mapping,diagnosis,out):
    assert frozen.file_sha(out/"first-latch-diagnosis.json")==crossing.DIAG_SHA
    original=json.loads((out/"original-feedback-diagnosis.json").read_text())
    assert frozen.file_sha(out/"original-feedback-diagnosis.json")==frozen.events.DIAG_SHA
    result=crossing.analyze(data,mapping,diagnosis,original)
    frozen.write_json(out/"crossing-order.json",result)
    return dict(status=result["status"],sha256=frozen.file_sha(out/"crossing-order.json"),
      bytes=(out/"crossing-order.json").stat().st_size,
      original_complete_intervals=result["original_complete_intervals"],
      original_transition_histogram=result["original_transition_histogram"],
      anomalous_intervals=len(result["matched_controls"]),
      observed_intervals=len(result["observed_intervals"]),
      output_events_observed=result["output_events_observed"],comparison=result["comparison"],
      causal_hypothesis_proved=False,full_phy_accepted=False)

EDITS=[
 ("        r['method']=methods()","        r['method']=methods()\n        r['qualified_replay']=qualified_replay()"),
 ("            r['diagnosis_sha256']=file_sha(OUT/'first-latch-diagnosis.json')",
  "            r['diagnosis_sha256']=file_sha(OUT/'first-latch-diagnosis.json')\n            assert r['diagnosis_sha256']==crossing.DIAG_SHA\n            r['crossing_order']=observe(data,mapping,diagnosis,OUT)"),
 ("'PASS_FIRST_LATCH_CACHE_REPLAY_CONTROLS_NO_NATIVE_ANALYSIS'",
  "'PASS_FIRST_LATCH_CROSSING_ORDER_CONTROLS_NO_NATIVE_ANALYSIS'"),
 ("'PASS_EXACT_FIRST_LATCH_CACHE_REPLAY_ORIGINAL_PLL_ACQUISITION_REMAINS_REJECTED'",
  "'PASS_EXACT_FIRST_LATCH_CROSSING_ORDER_ORIGINAL_PLL_REJECTION_PRESERVED'"),
 ("'FAIL_FIRST_LATCH_CACHE_REPLAY'","'FAIL_FIRST_LATCH_CROSSING_ORDER'")]
def derive():
    assert frozen.file_sha(Path(frozen.__file__))==BASE_SHA
    original=inspect.getsource(frozen.main);source=original
    for before,after in EDITS:
        assert source.count(before)==1;source=source.replace(before,after,1)
    restored=source
    for before,after in reversed(EDITS):
        assert restored.count(after)==1;restored=restored.replace(after,before,1)
    assert restored==original
    ast.parse(source)
    return source

def main():
    assert os.environ.get("GITHUB_ACTIONS")=="true"and os.environ.get("RUNNER_ENVIRONMENT")=="github-hosted"
    assert os.environ.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc"
    namespace=dict(vars(frozen),OUT=OUT,methods=methods,controls=controls,
                   qualified_replay=qualified_replay,crossing=crossing,observe=observe)
    exec(compile(derive(),"<exact-cache-replay-plus-crossing-observer>","exec"),namespace)
    namespace["main"]()
if __name__=="__main__":main()
