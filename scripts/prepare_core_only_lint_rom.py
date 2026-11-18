#!/usr/bin/env python3
"""Fetch only the authenticated core-only producer's compiled loader for lint."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import zipfile

P = "repos/Melihakbulut221/nssoc/"
RUN = 44238569057
HEAD = "bfb1fcc1bcd1d2def770ac26bd978767b0466e32"

def api(path):
    return json.loads(subprocess.check_output(["gh", "api", P + path]))

def archive(name):
    rows = [a for a in api(f"actions/runs/{RUN}/artifacts")["artifacts"] if a["name"] == name]
    assert len(rows) == 1
    item = rows[0]
    assert not item["expired"] and item["workflow_run"]["id"] == RUN
    assert item["workflow_run"]["head_sha"] == HEAD
    data = subprocess.check_output(["gh", "api", P + f"actions/artifacts/{item['id']}/zip"])
    assert item["digest"] == "sha256:" + hashlib.sha256(data).hexdigest()
    return zipfile.ZipFile(io.BytesIO(data)), item

def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true", "Cloud-only"
    run = api(f"actions/runs/{RUN}")
    assert run["head_sha"] == HEAD and run["run_attempt"] == 1 and run["conclusion"] == "success"
    mapping, mapped_meta = archive(f"core-only-mainchip-mapping-{RUN}")
    native, native_meta = archive(f"core-only-mainchip-source-native-{RUN}")
    report = json.loads(mapping.read("mapping.json"))
    assert report["source_head"] == HEAD and not report["ethernet_present"] and not report["pcie_present"]
    assert native.namelist() == ["build.tgz"]
    name = "hw/soc/out/core-only-mainchip/rtl/test_soc.bin"
    with tarfile.open(fileobj=io.BytesIO(native.read("build.tgz"))) as tar:
        members = [m for m in tar.getmembers() if m.name == name]
        assert len(members) == 1 and members[0].isfile()
        data = tar.extractfile(members[0]).read()
    digest = hashlib.sha256(data).hexdigest()
    assert digest == report["outputs"]["rtl/test_soc.bin"]
    assert digest == "ab7440619ca719358e6598b0cf291a268c8ccf13357b50ef3a89cbe583e71801"
    out = Path("hw/soc/out/core-only-lint-rom")
    out.mkdir(parents=True, exist_ok=False)
    (out / "test_soc.bin").write_bytes(data)
    (out / "source.json").write_text(json.dumps(dict(
        run=RUN, source_head=HEAD, member=name, sha256=digest,
        artifacts=[mapped_meta, native_meta], accepted=False,
        scope="Compiled loader bytes for physical-profile RTL lint; no boot acceptance"), indent=2) + "\n")

if __name__ == "__main__":
    main()
