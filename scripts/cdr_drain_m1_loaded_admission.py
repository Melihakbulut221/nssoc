#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact new two-rail RC input admission; execution is separately disabled.
No old partition, reduced resistor identifier, or resistance value is authority.
"""
import copy,hashlib,json,os,re
from pathlib import Path
import cdr_v59_tail_loaded_admission as old
from wait_cloud_tested_source_release import wait

ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-drain-m1-loaded-electrical'
METHOD='scripts/cdr-drain-m1-loaded-methods.json'
CONFIG='scripts/cdr-drain-m1-loaded-inputs.json'
CONFIG_SHA='e5d14f9e182480cb6ff5cc78ba9f12870777f19a3ff755fc31c01bcefcdad2b2'
PRIOR='scripts/cdr-drain-m1-fresh-rc-methods.json'
PRIOR_SHA='b84c987866ba84f2e67de967b82a15269558a19fb9760816fbefd71604c487a1'
PRIOR_COUNT=1502
ELECTRICAL_PRIOR='scripts/cdr-width-loaded-execution-methods.json'
ELECTRICAL_PRIOR_SHA='119b7a2d35abb1163570d01b8af16d18c6d9401e839a38904863d8b42eecef67'
PREFIX='docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/'
RECEIPT='docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/receipt.json'
RECEIPT_SHA='b8d62dc571089f55db76e1729297bcb6d6115638a2da1ef4759cefc04c025040'
RUN=41007572323
HEAD='593c0c056d3eedc69a90269cc7fbc376227a4983'
RELEASE=428678026
TAG='cloud-results-41007572323-1-cdr-drain-m1-fresh-rc'
MODEL_MEMBER='mim/composition/pd500-mim-wire.spice'
MODEL_SHA='5d4de0f4c9fcd6d6aa18d6e1f007a8dab68f1c72efc925d9c4064ca1e4209fed'
PLANES_MEMBER='mim/precise/source/native-planes.json'
PLANES_SHA='f32720bd478ef3f97b8a68fc16d60c07cc804d0ec04f05c32a0e48e2abbc340e'
RAW_SHA='5595b9551a089d44ba451cf2bbf01efdb71849c466a7fdae2d26c0f5c4ac7f19'
SUMMARY_SHA='8f03d88186919d434793cd3bafcfefa713311d2fe1314e4f227bfa0497d0edd3'
PASS='PASS_FRESH_WIDTH500_BINDING_WIRE_RC_SEVEN_MIM_TWO_ORDERS_REQUIRES_ORIGINAL_ELECTRICAL_MATRIX'
REQUIRED={'direct/binding-result.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.binding-result.json', 'bytes': 501144, 'sha256': '898da739f79dbd46d542ebe5d8fd71e794fb480254eb089bd8c2f1198f015a17', 'object_sha256': 'fbf046ac008480e813d62d5b558aedc8aed4d5d65076fe58e2e8171cc52351ba'}, 'direct/binding.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.binding.json', 'bytes': 351751, 'sha256': 'eec8d5f065b6da3d57c83c53c63d62b3fd3b1765c5c53b2d02a7b76a5ee4556a', 'object_sha256': 'a8d8e8c982ae599c321b2b160168012c69f36c7efcfb2f82aed95986626eb479'}, 'direct/canonical-candidate.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.canonical-candidate.json', 'bytes': 9186, 'sha256': '0c4e5625ec489736573c39067b3830695d5c59e2fb8de19d46d87263c7ccde5c', 'object_sha256': '0c4e5625ec489736573c39067b3830695d5c59e2fb8de19d46d87263c7ccde5c'}, 'direct/composition.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.composition.json', 'bytes': 969974, 'sha256': 'c8c2f8f3def3746abd57be49a830c34306bffeb44a2cd7d7bee64fb2fd2725dd', 'object_sha256': '8443695a78b2910e506ef160c2697ced666b0f0cfe01df8b2a9697b1aef42563'}, 'direct/direct-publication-plan.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.direct-publication-plan.json', 'bytes': 4043, 'sha256': '1a0bbefd134a4710ebc601f59133fda7cb78986d6904030833d216adaa2fe158', 'object_sha256': '1a0bbefd134a4710ebc601f59133fda7cb78986d6904030833d216adaa2fe158'}, 'direct/graph-restore.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.graph-restore.json', 'bytes': 58749, 'sha256': '3c96093b5ec9938abb8f41fa9f9a351a288cc89a2f3949bf4edd325ab0533170', 'object_sha256': '3c96093b5ec9938abb8f41fa9f9a351a288cc89a2f3949bf4edd325ab0533170'}, 'direct/joint-admission.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.joint-admission.json', 'bytes': 33887, 'sha256': '15f4420e7835a9e0c3f73696448c1ddeddbdc1d7d29b77b6a78b828c93801ab6', 'object_sha256': '15f4420e7835a9e0c3f73696448c1ddeddbdc1d7d29b77b6a78b828c93801ab6'}, 'direct/live-graph-and-physical.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.live-graph-and-physical.json', 'bytes': 200, 'sha256': '77b024853da6f9778d7a0c4dc3aafa0c07ff1737b6f2bcbde5bcc09419305736', 'object_sha256': '77b024853da6f9778d7a0c4dc3aafa0c07ff1737b6f2bcbde5bcc09419305736'}, 'direct/MIM-precision-result.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.MIM-precision-result.json', 'bytes': 6140403, 'sha256': 'f1acfac67dbe9675dfe61288cc58ed905335f5709182648ac9bcb16bb511b3b7', 'object_sha256': 'da3a609aa303bdefc0a9b12758627f02f22bbdf52e61cf8c564f67966709d221'}, 'direct/parts.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.parts.json', 'bytes': 849, 'sha256': '558e90e0ed576181bcd4d5f4c1939f20558647b69605268bed1498aa114f6590', 'object_sha256': 'd379917b4bfec9fc798c307a4b317a0a372e073b57ceb1f82f711730950f6ee2'}, 'direct/precise-audit.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.precise-audit.json', 'bytes': 258919, 'sha256': 'e9bcaa473501af5978a8ae4d5651c392bb2c7697d8973c6a7848b00b2bd15ae4', 'object_sha256': '3aee6890d377a1b35afae898ecee6c3a4cf40ea03646bcdf79d5f95a4de25d53'}, 'direct/precise-capture.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.precise-capture.json', 'bytes': 169365, 'sha256': '7f7f456e77fafe692e33b87d997ce2187c51a0dce6d765b69df3c640a9d32d3a', 'object_sha256': '43d3a5f8aaebe4c13f7fdc5e99cd1eef349bd28481a0fcb7d46b474739323655'}, 'direct/reversed-audit.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.reversed-audit.json', 'bytes': 259017, 'sha256': 'd58422888490e169c12dc127f97028c2f11370fdbf49dace82dfbd2d6233d7b4', 'object_sha256': 'dce2e2d3188f68dc549e98b6107087cfa66ad5483d13f76e9b915bda386da748'}, 'direct/reversed-capture.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.reversed-capture.json', 'bytes': 170594, 'sha256': '8349f9dcc1e2833dddf8275295346badec97a77ee6841743ac9155e06eb84735', 'object_sha256': 'bc38548d066480df3d894f524edf20ab9113c8b414ff588c4fb925c32d87f4c2'}, 'direct/runtime-smoke.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.runtime-smoke.json', 'bytes': 3557, 'sha256': '281731990c6093cbad8814cef4ad3f874a1d0c7e7308f4e6b574f84f8295a17d', 'object_sha256': '3aea90c0c3ae5251c97950d1efde7b17dfde8b3c4fd6ac45fe27c0f07b082f88'}, 'direct/summary.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.summary.json', 'bytes': 427668, 'sha256': '8f03d88186919d434793cd3bafcfefa713311d2fe1314e4f227bfa0497d0edd3', 'object_sha256': '8f03d88186919d434793cd3bafcfefa713311d2fe1314e4f227bfa0497d0edd3'}, 'direct/wire-RC-result.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.wire-RC-result.json', 'bytes': 2421610, 'sha256': 'd7fa4f384f1ab7174d7c1f3a053325bd9b572bb4bed6bddb315900b66c5b7966', 'object_sha256': 'f4fb92970f010751208de8b7223dd6e488cc98598983d9546cbe27ab527fe3e7'}, 'run.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/run.json', 'bytes': 14416, 'sha256': '65c6e4080205f23588b854e78252952ffd27f901114ab50e6915ce3cfa2dce66', 'object_sha256': '65c6e4080205f23588b854e78252952ffd27f901114ab50e6915ce3cfa2dce66'}, 'jobs.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/jobs.json', 'bytes': 14701, 'sha256': '05f6ce6afba79d4d565b6dae6c43746da06ad5cbf5c336234e8bb9fe5ba81eb0', 'object_sha256': '05f6ce6afba79d4d565b6dae6c43746da06ad5cbf5c336234e8bb9fe5ba81eb0'}, 'release.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/release.json', 'bytes': 41895, 'sha256': 'ebc8f61541d563b74197568a87ae9a93cae87e5abb1671512079abde9bb421da', 'object_sha256': 'ebc8f61541d563b74197568a87ae9a93cae87e5abb1671512079abde9bb421da'}, 'tag-ref.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/tag-ref.json', 'bytes': 528, 'sha256': 'b4f3b86af8a8ed86e18b3e1bb5e9cdc13727dc014de43eacec52a79f14cafc05', 'object_sha256': 'b4f3b86af8a8ed86e18b3e1bb5e9cdc13727dc014de43eacec52a79f14cafc05'}, 'complete-native-members.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/complete-native-members.json', 'bytes': 387475, 'sha256': '1b6bb754923c07e29bee0f363b50c3cf95e3314b510e06c8e41184c6f9e26526', 'object_sha256': '1b6bb754923c07e29bee0f363b50c3cf95e3314b510e06c8e41184c6f9e26526'}, 'raw-result.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/readback/hw/soc/out/cloud-cdr-drain-m1-fresh-rc/result.json', 'bytes': 427570, 'sha256': '5595b9551a089d44ba451cf2bbf01efdb71849c466a7fdae2d26c0f5c4ac7f19', 'object_sha256': '5595b9551a089d44ba451cf2bbf01efdb71849c466a7fdae2d26c0f5c4ac7f19'}, 'publication.json': {'path': 'docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/readback/hw/soc/out/cloud-cdr-drain-m1-fresh-rc-publication/publication.json', 'bytes': 8042, 'sha256': 'af183b1047ee75405d2a23b8530d0a36e8e54e89d93adc626db5bf6d0ce18b01', 'object_sha256': 'af183b1047ee75405d2a23b8530d0a36e8e54e89d93adc626db5bf6d0ce18b01'}}
SUMMARY='docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.summary.json'
STAGE='docs/evidence/cdr-drain-m1-fresh-rc-terminal-41007572323/direct/cdr-drain-m1-fresh-rc-41007572323-1.MIM-precision-result.json'
POLICY={'groups': ['cdr-drain-m1-loaded-nominal_early', 'cdr-drain-m1-loaded-nominal_late', 'cdr-drain-m1-loaded-hot_early', 'cdr-drain-m1-loaded-hot_late', 'cdr-drain-m1-loaded-cold_early', 'cdr-drain-m1-loaded-cold_late', 'cdr-drain-m1-loaded-constant_zero', 'cdr-drain-m1-loaded-constant_one', 'cdr-drain-m1-loaded-clock_stopped', 'cdr-drain-m1-loaded-vi_bias_off', 'cdr-drain-m1-loaded-preparation'], 'reserve_all_eleven_before_any_native_dependencies': True, 'create_preparation_reservation_last': True, 'preparation_seconds': 1200, 'each_loaded_case_seconds': 7200, 'max_parallel': 2, 'fail_fast': False, 'automatic_retry': False}
NEW_REQUIRED=('scripts/cdr_drain_m1_loaded_admission.py', 'scripts/cloud_cdr_drain_m1_loaded.py', 'scripts/cdr_drain_m1_loaded_result.py', 'scripts/cloud_cdr_drain_m1_loaded_stage.py', 'scripts/check_cdr_drain_m1_loaded.py', 'scripts/cdr-drain-m1-loaded-inputs.json', 'docs/evidence/cdr-drain-m1-loaded-source-review-20261030.json')
PHASES=('restore-complete-graph138-and-current75', 'fresh-current500-binding', 'fresh-current500-wire-RC', 'fresh-seven-MIM-both-native-orders')
MODEL=old.MODEL
CASES=old.CASES
AUTH=old.AUTH
ALWAYS_FALSE=old.ALWAYS_FALSE
require=old.require
sha=old.sha
regular=old.regular
relative=old.relative
write=old.write
fetch=old.fetch
release=old.release
verify_exact_files=old.verify_exact_files

def exact(a,b,why):
    require(json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False),why)

def encoded(value):
    return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n").encode()

def descriptor():
    raw=regular(ROOT,CONFIG).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==CONFIG_SHA,"New RC input configuration changed")
    return json.loads(raw)

def validate_method(m,prior,electrical):
    require(m["schema"]=="cdr-drain-m1-loaded-execution-v1"and m["branch"]==BRANCH,"Drain loaded method identity")
    old.validate_authorizations(m)
    require(m["controller_readiness"]is(m["preparation_authorized"]or m["simulation_authorized"]),"Controller authority mismatch")
    require(not m["workflow_dispatch_authorized"]or m["source_controls_authorized"],"Dispatch requires source controls")
    require(type(m["producer_run"])is int and m["producer_run"]==RUN and m["producer_source"]==HEAD,"New RC producer identity")
    exact(m["execution_policy"],POLICY,"Original ten-case policy changed")
    require(m["original_executed_source"]=="e191424507e67331b2e79800caece4a3f03a1cc0"
      and m["original_execution_method_sha256"]==ELECTRICAL_PRIOR_SHA
      and m["current_RC_receipt_sha256"]==RECEIPT_SHA,"Original electrical/new RC authority binding")
    require(len(prior["protected_sha256"])==PRIOR_COUNT,"Inherited RC source count")
    for parent in (prior,electrical):
        require(all(m["protected_sha256"].get(n)==h for n,h in parent["protected_sha256"].items()),"Inherited source protection removed")
    require(m["protected_sha256"].get(PRIOR)==PRIOR_SHA and m["protected_sha256"].get(ELECTRICAL_PRIOR)==ELECTRICAL_PRIOR_SHA,"Historical method source omitted")
    require(all(n in m["protected_sha256"]for n in NEW_REQUIRED),"New loaded source protection omitted")
    require(m["protected_sha256"].get(RECEIPT)==RECEIPT_SHA,"Fresh RC receipt protection omitted")
    return m

def methods():
    require(sha(regular(ROOT,PRIOR))==PRIOR_SHA and sha(regular(ROOT,ELECTRICAL_PRIOR))==ELECTRICAL_PRIOR_SHA,"Historical method changed")
    m=validate_method(json.loads(regular(ROOT,METHOD).read_bytes()),
      json.loads(regular(ROOT,PRIOR).read_bytes()),json.loads(regular(ROOT,ELECTRICAL_PRIOR).read_bytes()))
    for n,h in m["protected_sha256"].items():
        require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h)and sha(regular(ROOT,n))==h,"Protected execution source changed: "+n)
    descriptor()
    return m

def context(env=None):
    e=os.environ if env is None else env
    require(e.get("GITHUB_ACTIONS")=="true"and e.get("RUNNER_ENVIRONMENT")=="github-hosted"
      and e.get("RUNNER_OS")=="Linux"and e.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc",
      "Current width hosted Linux context required")
    require(e.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and e.get("GITHUB_RUN_ATTEMPT")=="1",
      "Current width manual first attempt required")
    require(e.get("GITHUB_REF")=="refs/heads/"+BRANCH,"Current width execution branch required")
    require(re.fullmatch("[0-9a-f]{40}",e.get("GITHUB_SHA",""))
      and re.fullmatch("[1-9][0-9]*",e.get("GITHUB_RUN_ID","")),"Current width source/run invalid")
    return {"source":e["GITHUB_SHA"],"run_id":int(e["GITHUB_RUN_ID"]),"attempt":1}

def reservation_gate():
    ctx=context();receipts={}
    for group in POLICY["groups"]:
        proof=wait(group,os.environ)
        tag,head=release.context(group,os.environ)
        require(proof["tag"]==tag and proof["tested_source"]==head==ctx["source"]
          and type(proof["release_id"])is int and proof["release_id"]>0
          and proof["externally_reserved"]is True and proof["creation_attempted"]is False
          and proof["target_verified"]is True and proof["assets_overwritten"]is False,
          "Current execution reservation changed")
        receipts[group]=proof
    require(len({p["release_id"]for p in receipts.values()})==11,"Execution reservation release collision")
    return {"current_context":ctx,"groups":receipts,"all_eleven_reserved_before_acquisition":True,
      "historical_source_proof_is_not_execution_authority":True}

def source_guard():
    m=methods();raw=regular(ROOT,RECEIPT).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==RECEIPT_SHA,"Fresh RC terminal receipt changed")
    receipt=json.loads(raw)
    require(receipt["run_id"]==RUN and receipt["source"]==HEAD and receipt["attempt"]==1
      and receipt["release_id"]==RELEASE and receipt["complete_native_members"]==2680,"Fresh RC receipt identity")
    for name,spec in receipt["records"].items():
        path=PREFIX+name
        require(m["protected_sha256"].get(path)==spec["sha256"],"Complete producer proof unprotected: "+path)
        b=regular(ROOT,path).read_bytes()
        require(len(b)==spec["bytes"]and hashlib.sha256(b).hexdigest()==spec["sha256"],"Complete producer proof changed: "+path)
    d={}
    for name,spec in REQUIRED.items():
        b=regular(ROOT,spec["path"]).read_bytes()
        require(len(b)==spec["bytes"]and hashlib.sha256(b).hexdigest()==spec["sha256"],"Required producer report changed: "+name)
        d[name]=json.loads(b)
    validate_reports(d)
    return d

def full_map(d):
    return d["complete-native-members.json"]["sha256"]

def submap(full,prefix):
    return {n[len(prefix):]:h for n,h in full.items()if n.startswith(prefix)}

def validate_targets(composition,config):
    found={}
    for anchor,target in config["target_terminals"].items():
        identities={tuple(x)for x in target["graph_full_partition"]["terminals"]}
        require(len(identities)==8 and target["graph_full_partition"]["ports"]==[],"Target complete terminal partition")
        rows=[]
        for dev in composition["device_records"]:
            for term in dev["terminals"]:
                if any(dev["native_id"]==i and dev["model"].lower()==model.lower()and term["terminal"]==t for i,model,t in identities):
                    rows.append(dict(native_id=dev["native_id"],instance=dev["instance"],model=dev["model"],parameters=dev["parameters"],**term))
        exact(rows,target["terminals"],"Fresh target terminal/node mapping changed: "+anchor)
        require(len(rows)==8 and all(r["native_cluster"]==target["native_cluster"]and r["native_net"]==target["native_net"]for r in rows),"Target full partition disagrees")
        all_terms={(dev["native_id"],dev["model"].lower(),t["terminal"])for dev in composition["device_records"]for t in dev["terminals"]if(t["native_cluster"],t["native_net"])==(target["native_cluster"],target["native_net"])}
        require(all_terms=={(i,model.lower(),t)for i,model,t in identities},"Target gained or lost terminals")
        require(sum(r["anchor"]==anchor and r["node"]=="w_"+anchor for r in rows)==1,"Fresh requested drain anchor missing")
        found[anchor]={"component":target["component"],"native_cluster":target["native_cluster"],"native_net":target["native_net"],"terminals":rows,"reduced_resistor_identity_assumed":False}
    return found

def validate_reports(d):
    require(set(d)==set(REQUIRED),"Required producer report set changed")
    for name,spec in REQUIRED.items():
        require(hashlib.sha256(encoded(d[name])).hexdigest()==spec["object_sha256"],"Authenticated producer report contents changed: "+name)
    s=d["direct/summary.json"];raw=d["raw-result.json"];full=full_map(d);cfg=descriptor()
    require(len(full)==2680 and len(s["outputs"])==2679 and len(raw["outputs"])==2678,"Complete new RC inventory changed")
    exact(full,{**s["outputs"],"result.json":RAW_SHA},"Raw result substituted by direct summary")
    exact(s["outputs"],{**raw["outputs"],**cfg["publication"]["only_output_addition"]},"Publication-only log delta")
    exact({k:v for k,v in s.items()if k!="outputs"},{k:v for k,v in raw.items()if k!="outputs"},"Raw/publication semantics differ")
    for n,h in full.items():relative(n);require(type(h)is str and re.fullmatch("[0-9a-f]{64}",h),"Invalid native member")
    require(s["status"]==PASS and s["source_head"]==HEAD and s["run_id"]==RUN and s["run_attempt"]==1,"New RC producer identity")
    require(all(s[k]is True for k in ("binding_executed","extraction_executed","fresh_RC_pipeline_complete","terminal_finalization_complete")),"Incomplete fresh RC")
    require(all(s[k]is False for k in ("automatic_retry","physical_geometry_regenerated","simulation_executed","physical_accepted","electrical_accepted","qualified_pex","full_phy_accepted","original_electrical_rejection_overridden","historical_authority_reused")),"RC acceptance scope changed")
    require((s["graph_run"],s["graph_source"])==(cfg["graph"]["run"],cfg["graph"]["source"])
      and(s["physical_run"],s["physical_source"])==(cfg["physical"]["run"],cfg["physical"]["source"])
      and(s["complete_graph_members"],s["current_members"])==(138,75),"New physical/graph lineage changed")
    require([r["label"]for r in s["commands"]]==list(PHASES),"Four original phases changed")
    for r in s["commands"]:
        require(r["returncode"]==0 and r["supervision_failure"]is None and r["memory_read_error"]is None
          and not r["process_group_cleanup"]["remaining_live"]and not r["process_group_cleanup"]["signals"],"Fresh RC phase failed")
    require(all(x["completed"]is True for x in s["terminal_actions"])and not s.get("terminal_errors"),"Producer finalization failed")
    b=d["direct/binding-result.json"];binding=d["direct/binding.json"];wire=d["direct/wire-RC-result.json"];mim=d["direct/MIM-precision-result.json"];co=d["direct/composition.json"]
    for prefix,name,report,count in (("binding/","binding-result.json",b,53),("wire-stage/","wire-RC-result.json",wire,5),("mim/","MIM-precision-result.json",mim,1963)):
        exact(submap(full,prefix),{**report["outputs"],"result.json":REQUIRED["direct/"+name]["sha256"]},"Nested complete output inventory differs")
        require(len(submap(full,prefix))==count and report["source_head"]==HEAD and report["sources_unchanged"]is True,"Nested source/census differs")
    exact(b["binding"],binding,"Binding bytes/report differ")
    exact(binding["census"],{"npn13G2":124,"sg13_lv_nmos":50,"rppd":98,"cap_cmim":7,"ptap1":221},"Original 500-device census changed")
    exact(mim["composition"]["contract"],co,"Fresh composition report differs")
    exact(co["counts"],{"devices":500,"R":24356,"C":15566},"Actual new composition census differs")
    require(co["interface"]==binding["native_ports"]+["wire_cref"]and len(set(co["interface"]))==26,"Current interface order")
    require(len(co["device_records"])==500 and {x["native_id"]for x in co["device_records"]}=={x["native_id"]for x in binding["devices"]},"Device identities differ")
    old.frozen_pipeline_validator(HEAD)(mim,0)
    canonical=d["direct/canonical-candidate.json"]
    require(canonical["complete_members"]==75 and canonical["current_root_result_fabricated"]is False and "result.json"not in canonical["files"],"Original current75 identity changed")
    handoff=mim["current_input_restoration"]
    require(handoff["source_head"]==HEAD and handoff["run"]==RUN and handoff["historical763_1136_1127_counts_reused"]is False,"Fresh MIM handoff context")
    exact(handoff["binding"]["report"],b,"MIM binding handoff");exact(handoff["rc"]["report"],wire,"MIM RC handoff")
    for key,prefix,count in (("complete_binding_files","binding/",53),("complete_RC_stage_files","wire-stage/",5),("complete_current_view_files","canonical-current-view/",496)):
        require(len(handoff[key])==count,"Fresh handoff count");exact(handoff[key],submap(full,prefix),"Full handoff inventory differs")
    require(all(handoff["complete_current_view_files"].get(n)==h for n,h in canonical["files"].items()),"Original75 changed in496 RC view")
    require(canonical["files"]["parent/layout/nssoc_cdr_pd500_resistor_v59.gds"]==cfg["physical"]["gds_sha256"],"New rail GDS missing")
    for order in ("precise","precise_reversed"):
        exact(submap(full,"mim/"+order+"/source/"),handoff["complete_current_view_files"],"Full native order source projection differs")
        exact(submap(full,"mim/"+order+"/model-binding/"),handoff["complete_binding_files"],"Full native order binding differs")
    targets=validate_targets(co,cfg);selected_members(full)
    return {"complete_members":2680,"canonical_members":496,"original_current_members":75,"graph_members":138,
      "target_terminals":targets,"raw_result_sha256":RAW_SHA,"publication_summary_sha256":SUMMARY_SHA,
      "electrical_accepted":False,"new_electrical_execution_performed":False}

def selected_members(full):
    require(full[MODEL_MEMBER]==MODEL_SHA and full[PLANES_MEMBER]==PLANES_SHA and full["canonical-current-view/native-planes.json"]==PLANES_SHA and full["mim/precise_reversed/source/native-planes.json"]==PLANES_SHA,"Current model/plane exact path changed")
    return {n:full[n]for n in (MODEL_MEMBER,PLANES_MEMBER,"mim/composition/composition.json","binding/binding.json","mim/precise/source/parent/layout/result.json")}

def verify_bundle(bundle,d):
    full=full_map(d)
    proof=old.verify_exact_files(bundle,full)
    require(regular(bundle,"result.json").read_bytes()==regular(ROOT,REQUIRED["raw-result.json"]["path"]).read_bytes(),"Restored raw terminal differs")
    for row in d["direct/direct-publication-plan.json"]["files"]:
        name="direct/"+row["suffix"]
        if name in REQUIRED:require(regular(bundle,row["member"]).read_bytes()==regular(ROOT,REQUIRED[name]["path"]).read_bytes(),"Restored direct report differs")
    planes=json.loads(regular(bundle,PLANES_MEMBER).read_bytes())
    require(sha(regular(bundle,PLANES_MEMBER))==PLANES_SHA and sha(regular(bundle,MODEL_MEMBER))==MODEL_SHA,"Current exact model/planes missing")
    require(planes["status"]=="PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS"and len(planes["anchors"])==160 and len({a["logical_net"]for a in planes["anchors"]})==51,"Current native plane qualification changed")
    layouts=[h for n,h in planes["inputs"].items()if n.endswith("/layout/result.json")]
    require(layouts==[full["mim/precise/source/parent/layout/result.json"]],"Current planes/layout join changed")
    require(regular(bundle,"mim/precise/model-binding/binding.json").read_bytes()==regular(bundle,"binding/binding.json").read_bytes(),"Current plane binding differs")
    for order in ("precise","precise_reversed"):
        require(regular(bundle,"mim/"+order+"/source/native-planes.json").read_bytes()==regular(bundle,PLANES_MEMBER).read_bytes(),"Two-order native planes differ")
    return planes,proof

def validate_live(run,jobs,info,ref,docs=None):
    d=source_guard()if docs is None else docs
    expected=d["run.json"]
    keys=("id","run_attempt","head_sha","head_branch","event","status","conclusion","workflow_id")
    exact({k:run[k]for k in keys},{k:expected[k]for k in keys},"Live RC run changed")
    require(run["id"]==RUN and run["head_sha"]==HEAD and run["status"]=="completed"and run["conclusion"]=="success"and type(run["run_attempt"])is int and run["run_attempt"]==1,"RC run did not succeed")
    ej={j["id"]:j for j in d["jobs.json"]["jobs"]}
    require(jobs["total_count"]==len(jobs["jobs"])==len(ej)==4 and len({j["id"]for j in jobs["jobs"]})==4,"RC job census changed")
    for j in jobs["jobs"]:
        require(j["id"]in ej,"Unexpected RC job")
        keys=("id","name","head_sha","run_id","run_attempt","status","conclusion")
        exact({k:j[k]for k in keys},{k:ej[j["id"]][k]for k in keys},"RC job identity changed")
        require(j["status"]=="completed"and j["conclusion"]=="success","RC job failed")
        sk=("number","name","status","conclusion")
        exact([{k:s[k]for k in sk}for s in j["steps"]],[{k:s[k]for k in sk}for s in ej[j["id"]]["steps"]],"RC job steps changed")
    require(type(info["id"])is int and info["id"]==RELEASE,"RC release changed")
    proof=release.validate_release(info,ref,TAG,HEAD)
    keys=("id","name","size","digest","state")
    rows=lambda value:sorted([{k:a[k]for k in keys}for a in value["assets"]],key=lambda a:a["id"])
    require(len(info["assets"])==19 and all(type(a["id"])is int and type(a["size"])is int and a["size"]>0 and a["state"]=="uploaded"for a in info["assets"]),"RC asset census/state changed")
    exact(rows(info),rows(d["release.json"]),"Complete live RC assets changed")
    parts=d["direct/parts.json"];byname={a["name"]:a for a in info["assets"]}
    require(parts["format"]=="ordered-tar-gzip-parts-v1"and parts["source_directory"]=="cloud-cdr-drain-m1-fresh-rc"and parts["bytes"]==59924645 and parts["sha256"]=="c35e126127cd9217b5448f6dba0362079310a3ca4ae48ba8c145fc6921735aa3","Current RC archive identity changed")
    require([p["index"]for p in parts["parts"]]==[0]and sum(p["bytes"]for p in parts["parts"])==parts["bytes"],"Ordered archive parts changed")
    for p in parts["parts"]:
        a=byname[p["name"]];require((a["size"],a["digest"])==(p["bytes"],"sha256:"+p["sha256"]),"Archive part/release join changed")
    for name,spec in REQUIRED.items():
        if not name.startswith("direct/"):continue
        suffix=name.split("/",1)[1];matches=[a for a in info["assets"]if a["name"]==parts["stem"]+"."+suffix]
        require(len(matches)==1 and(matches[0]["size"],matches[0]["digest"])==(spec["bytes"],"sha256:"+spec["sha256"]),"Direct asset/proof bytes differ")
    return {"run":RUN,"source_head":HEAD,"reservation":proof,"assets":19,"terminal_success":True,"native_acquisition_performed":False}

def acquire_and_extract(out,d,info):
    transport=Path(out)/"current-mim-transport";transport.mkdir(exist_ok=False)
    for a in info["assets"]:
        relative(a["name"]);require("/"not in a["name"],"Invalid producer asset basename")
        target=transport/a["name"];digest=a["digest"].removeprefix("sha256:")
        fetch(a["browser_download_url"],digest,target)
        require(target.stat().st_size==a["size"]and sha(target)==digest,"Downloaded current RC asset changed")
    for name,spec in REQUIRED.items():
        if name.startswith("direct/"):
            p=transport/(d["direct/parts.json"]["stem"]+"."+name.split("/",1)[1])
            require(p.read_bytes()==regular(ROOT,spec["path"]).read_bytes(),"Direct snapshot transport changed")
    bundle=Path(out)/"current-mim-bundle"
    return old.saved.exact_extract(d["direct/parts.json"],transport,bundle,full_map(d))

def expected_files():
    return full_map(source_guard())

def verify_restored(root):
    return verify_exact_files(Path(root)/"current-mim-bundle",expected_files())

def composition_proof(d,archive,remote):
    return {"run":RUN,"source_head":HEAD,"reservation":remote["reservation"],"live_producer":remote,"full_archive":archive,
      "summary_sha256":SUMMARY_SHA,"raw_result_sha256":RAW_SHA,"stage_sha256":REQUIRED["direct/MIM-precision-result.json"]["sha256"],
      "current_graph_run":41003747027,"current_physical_run":41000358737,"complete_graph_members":138,"current_members":75,"canonical_members":496,
      "historical_failed_geometry_and_electrical_reports_retained":True,"geometry_regenerated":False,"extraction_rerun":False,"simulation_preaccepted":False,
      "fresh_target_terminal_bindings":validate_targets(d["direct/composition.json"],descriptor())}

def plane_proof(d):
    return {"current_mim_source":REQUIRED["direct/MIM-precision-result.json"]["sha256"],"native_planes_sha256":PLANES_SHA,
      "fresh_layout_sha256":full_map(d)["mim/precise/source/parent/layout/result.json"],"native_binding_sha256":REQUIRED["direct/binding.json"]["sha256"]}

def loaded_view(bundle,d,archive,remote,planes):
    require(archive["regular_members"]==2680 and archive["full_inventory_verified"]is True,"Complete new restored archive missing")
    exact({n:r["sha256"]for n,r in archive["complete_member_hashes"].items()},full_map(d),"Restored full2680 inventory differs")
    return d["direct/MIM-precision-result.json"],composition_proof(d,archive,remote),Path(bundle)/MODEL_MEMBER,d["direct/composition.json"],planes,plane_proof(d)

def authorize(prepare_only):
    require(type(prepare_only)is bool,"Preparation mode must be boolean")
    m=methods();context()
    require(m["preparation_authorized"if prepare_only else"simulation_authorized"]is True and m["controller_readiness"]is True,"New drain loaded execution disabled")
    return m

def restore(out,prepare_only):
    authorize(prepare_only);d=source_guard();out=Path(out)
    require(out.is_dir()and not out.is_symlink(),"Invalid loaded output root")
    require(all(not(out/n).exists()and not(out/n).is_symlink()for n in ("current-mim-transport","current-mim-bundle")),"Loaded restore destination occupied")
    reservations=reservation_gate()
    write(out/"current-execution-admission.json",reservations)
    run=release.api("actions/runs/"+str(RUN));jobs=release.api("actions/runs/"+str(RUN)+"/attempts/1/jobs?per_page=100")
    info=release.api("releases/"+str(RELEASE));ref=release.api("git/ref/tags/"+TAG)
    remote=validate_live(run,jobs,info,ref,d)
    archive=acquire_and_extract(out,d,info)
    planes,_=verify_bundle(out/"current-mim-bundle",d)
    methods()
    return loaded_view(out/"current-mim-bundle",d,archive,remote,planes)
