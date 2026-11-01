"""Acquire only three authenticated derived inputs on the GitHub runner."""
import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = "repos/Melihakbulut221/nssoc/"
M = "scripts/mainchip-targeted-counterpart-routing-inputs.json"

def api(path):
    return json.loads(subprocess.check_output(["gh", "api", R + path], timeout=90))

def remote(pin):
    if "asset_id" in pin:
        return subprocess.check_output(["gh", "api", "-H", "Accept: application/octet-stream",
                                        R + "releases/assets/" + str(pin["asset_id"])], timeout=120)
    d = api("contents/" + pin["path"] + "?ref=" + pin["source"])
    if not d.get("content"):
        d = api("git/blobs/" + d["sha"])
    return base64.b64decode(d["content"])

def main():
    e = os.environ
    assert e["GITHUB_ACTIONS"] == "true" and e["GITHUB_REPOSITORY"] == "Melihakbulut221/nssoc"
    assert e["GITHUB_RUN_ATTEMPT"] == "1" and e["APPROVED_SOURCE"] == e["GITHUB_SHA"]
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == e["GITHUB_SHA"]
    m = json.loads((ROOT / M).read_bytes())
    assert m["native_execution_authorized"] is False
    for name, pin in m["source_files"].items():
        raw = (ROOT / name).read_bytes()
        assert len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"], name
    release = api("releases/430116200")
    assert release["id"] == 430116200 and release["tag_name"] == "cloud-results-41230348060-1-mainchip-stale-wire-terminal-readback"
    assert release["target_commitish"] == "a472ca9f5955d28d8767b8f51aa34ba553b9b699" and release["draft"] is False
    ref = api("git/ref/tags/" + release["tag_name"])
    assert ref["object"]["type"] == "commit" and ref["object"]["sha"] == release["target_commitish"]
    asset = next(x for x in release["assets"] if x["id"] == 696171435)
    pin = m["inputs"]["insertion_plan.json"]
    assert asset["name"] == pin["asset_name"] and asset["size"] == pin["bytes"]
    assert asset["digest"] == "sha256:" + pin["sha256"]
    out = ROOT / m["materialized_directory"]
    out.mkdir(exist_ok=False)
    for name, pin in m["inputs"].items():
        assert "/" not in name and "\\" not in name and name.endswith(".json")
        raw = remote(pin)
        (out / name).write_bytes(raw)
        assert len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"], name
        json.loads(raw)
    (out / "acquisition.json").write_text(json.dumps(dict(
        source=e["GITHUB_SHA"], run=int(e["GITHUB_RUN_ID"]), inputs=m["inputs"],
        release=release, ref=ref, native_acquisition=False), sort_keys=True, indent=2) + "\n")

if __name__ == "__main__":
    main()
