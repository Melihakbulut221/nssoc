#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One-shot cloud handoff for the selected banked candidate; never restart a job."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from cloud_corrpre_banked_postcts import BOOT_RUN, BOOT_HEAD, PROTOCOL_RUN, require_candidate

ROOT = Path(__file__).resolve().parents[1]
REPO = "repos/Melihakbulut221/nssoc/"
BRANCH = "codex/complete-open-work"
BOOT_WORKFLOW = ".github/workflows/corrpre-pcie-mbist-native-boot-cloud.yml"
PLACE_WORKFLOW = ".github/workflows/corrpre-banked-placement-cloud.yml"


def placement_title():
    return f"corrpre-banked-placement-cloud / boot {BOOT_RUN}"


def repair_title(run):
    return f"corrpre-banked-postcts-cloud / placement {run}"


def api(path, payload=None):
    command = ["gh", "api", REPO + path]
    if payload is not None:
        command += ["--input", "-"]
    raw = subprocess.check_output(command, input=json.dumps(payload).encode() if payload is not None else None)
    return json.loads(raw) if raw.strip() else None


def get_asset(asset):
    raw = subprocess.check_output(["gh", "api", REPO + "releases/assets/" + str(asset["id"]),
                                   "-H", "Accept: application/octet-stream"])
    assert len(raw) == asset["size"]
    digest = hashlib.sha256(raw).hexdigest()
    if asset.get("digest"):
        assert asset["digest"] == "sha256:" + digest
    return raw, digest


def wait_success(number, workflow, deadline, report, save):
    previous = None
    while True:
        run = api("actions/runs/" + str(number))
        assert run["path"] == workflow and run["head_branch"] == BRANCH
        if workflow == BOOT_WORKFLOW:
            assert run["id"] == BOOT_RUN and run["head_sha"] == BOOT_HEAD
        snapshot = {k: run[k] for k in ("id", "head_sha", "status", "conclusion", "run_attempt")}
        report["observed_source"] = snapshot
        save()
        if snapshot != previous:
            print(json.dumps(snapshot), flush=True)
            previous = snapshot
        if run["status"] == "completed":
            assert run["conclusion"] == "success", "Source is terminal unsuccessful; no successor launched"
            return run
        assert time.monotonic() < deadline, "Observation budget reached; source not cancelled or restarted"
        time.sleep(60)


def existing(workflow, title):
    found = []
    for page in range(1, 11):
        batch = api("actions/workflows/" + workflow + "/runs?branch=" + BRANCH +
                    "&event=workflow_dispatch&per_page=100&page=" + str(page))["workflow_runs"]
        found.extend(r for r in batch if r["display_title"] == title)
        if len(batch) < 100:
            break
    else:
        raise AssertionError("Could not exhaust run history; refuse duplicate dispatch")
    assert len(found) <= 1, "Multiple candidate runs already exist; require review"
    return found[0] if found else None


def launch(workflow, title, inputs, report, save):
    run = existing(workflow, title)
    if run is None:
        # Save intent before the only dispatch. An uncertain API response is not
        # retried: inspect the authoritative run list before resuming this job.
        report["dispatch_intent"] = dict(workflow=workflow, title=title, inputs=inputs)
        save()
        api("actions/workflows/" + workflow + "/dispatches", dict(ref=BRANCH, inputs=inputs))
        report["dispatch_acknowledged"] = True
        save()
        for _ in range(12):
            run = existing(workflow, title)
            if run is not None:
                break
            time.sleep(10)
        assert run is not None, "Dispatch acknowledged; run not visible yet. Do not redispatch blindly."
    assert not (run["status"] == "completed" and run["conclusion"] != "success"), (
        "Existing successor failed; preserving it without restart")
    report["successor"] = {k: run[k] for k in ("id", "head_sha", "status", "conclusion", "html_url")}
    save()
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write("next_run=" + str(run["id"]) + "\n")
    return run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("boot", "placement"), required=True)
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--wait-seconds", type=int, default=18000)
    args = parser.parse_args()
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    assert 60 <= args.wait_seconds <= 18000 and args.run > 0
    out = ROOT / ("cloud-corrpre-banked-handoff-" + args.stage)
    out.mkdir(exist_ok=False)
    report = dict(status="WAITING_FOR_NATIVE_SOURCE", stage=args.stage,
                  source_head=os.environ["GITHUB_SHA"], source_run=args.run,
                  accepted=False, full_phy_accepted=False, final_timing_complete=False)
    def save():
        (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    save()
    try:
        if args.stage == "boot":
            assert args.run == BOOT_RUN
        workflow = BOOT_WORKFLOW if args.stage == "boot" else PLACE_WORKFLOW
        run = wait_success(args.run, workflow, time.monotonic() + args.wait_seconds, report, save)
        if args.stage == "boot":
            candidates = api("actions/runs/" + str(args.run) + "/artifacts?per_page=100")
            assert candidates["total_count"] <= 100
            artifacts = [a for a in candidates["artifacts"] if a["name"] == "corrpre-pcie-mbist-native-boot-full"]
            assert len(artifacts) == 1 and not artifacts[0]["expired"]
            artifact = artifacts[0]
            raw = subprocess.check_output(["gh", "api", REPO + "actions/artifacts/" + str(artifact["id"]) + "/zip"])
            digest = hashlib.sha256(raw).hexdigest()
            if artifact.get("digest"):
                assert artifact["digest"] == "sha256:" + digest
            spec = out / "verified-boot-source.json"
            subprocess.run([sys.executable, "scripts/check_pcie_banked_boot_source.py",
                "--boot-run", str(BOOT_RUN), "--boot-head", BOOT_HEAD, "--artifact", str(artifact["id"]),
                "--zip-sha256", digest, "--protocol-run", str(PROTOCOL_RUN), "--out", str(spec)],
                cwd=ROOT, check=True)
            subprocess.run([sys.executable, "scripts/preserve_corrpre_pcie_mbist_boot_evidence.py",
                            "--source-spec", str(spec)], cwd=ROOT, check=True)
            source = ROOT / "cloud-corrpre-pcie-mbist-boot-evidence"
            proof = json.loads((source / "result.json").read_text())
            assert proof["gate_result"]["passed"] and proof["source_run"] == BOOT_RUN
            assert proof["original_zip_sha256"] == digest
            # The existing verifier checks actual28checks, both Ethernet+system
            # MBIST handover, native models, exact netlist hash and original failures.
            shutil.move(str(source), str(out / "native-boot-evidence"))
            report["verified_native_boot"] = dict(artifact=artifact["id"], zip_sha256=digest,
                native_log_banner=proof["native_log_banner"], source_spec=json.loads(spec.read_text()))
            save()
            launch("corrpre-banked-placement-cloud.yml", placement_title(),
                dict(boot_run=str(BOOT_RUN), boot_head=BOOT_HEAD, boot_artifact=str(artifact["id"]),
                     boot_zip_sha256=digest, protocol_run=str(PROTOCOL_RUN)), report, save)
        else:
            assert run["display_title"] == placement_title()
            group = "corrpre-banked-placement"
            stem = f"{group}-{args.run}-{run['run_attempt']}"
            release = api(f"releases/tags/cloud-results-{args.run}-{run['run_attempt']}-{group}")
            def named(suffix):
                selected = [a for a in release["assets"] if a["name"] == stem + suffix]
                assert len(selected) == 1
                raw, digest = get_asset(selected[0])
                (out / (stem + suffix)).write_bytes(raw)
                return json.loads(raw), digest
            summary, summary_sha = named(".summary.json")
            parts, parts_sha = named(".parts.json")
            spec = require_candidate(summary, run["head_sha"])
            assert parts["stem"] == stem and parts["source_directory"] == "cloud-corrpre-mbist-placement"
            assert parts["format"] == "ordered-tar-gzip-parts-v1"
            assert parts["verification"]["all_parts_and_combined_bytes_verified"] is True
            assert parts["verification"]["sha256"] == parts["sha256"]
            report["verified_placement_summary"] = dict(run=args.run, source_head=run["head_sha"],
                summary_sha256=summary_sha, parts_sha256=parts_sha,
                cts_odb_sha256=summary["cts_odb_sha256"], boot_source_spec=spec,
                scope="Native completion and source metadata. Successor independently verifies every archive byte before CAD.")
            save()
            launch("corrpre-banked-postcts-cloud.yml", repair_title(args.run),
                dict(placement_run=str(args.run), summary_sha256=summary_sha, parts_sha256=parts_sha),
                report, save)
        report["status"] = "VERIFIED_SOURCE_AND_DISPATCHED_OR_FOUND_EXACT_SUCCESSOR_NOT_PHYSICAL_ACCEPTANCE"
    except BaseException as error:
        report.update(status="FAIL_OR_ERROR_NO_BLIND_RESTART", error=repr(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
