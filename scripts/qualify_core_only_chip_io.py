#!/usr/bin/env python3
"""Cloud-only structural shell qualification; no physical chip acceptance."""
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path.cwd()
OUT = ROOT / "hw/soc/out/core-only-io-shell"
REPO = "repos/Melihakbulut221/nssoc/"
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def api(path):
    return json.loads(subprocess.check_output(["gh", "api", REPO + path]))
def archive(i, digest):
    metadata = api(f"actions/artifacts/{i}")
    assert not metadata["expired"] and metadata["workflow_run"]["id"] == 44238569057
    assert metadata["workflow_run"]["head_sha"] == "bfb1fcc1bcd1d2def770ac26bd978767b0466e32"
    raw = subprocess.check_output(["gh", "api", REPO + f"actions/artifacts/{i}/zip"])
    assert hashlib.sha256(raw).hexdigest() == digest
    assert metadata["digest"] == "sha256:" + digest
    return zipfile.ZipFile(io.BytesIO(raw))
def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    OUT.mkdir(parents=True, exist_ok=False)
    result = dict(source_head=os.environ["GITHUB_SHA"], status="RUNNING", accepted=False,
                  actual_chip_boot_passed=False, pad_cell_models_qualified=False,
                  physical_timing_complete=False, manufacturing_approval=False)
    try:
        paths = ["scripts/generate_chip_io.py", "hw/soc/chip-io-contract.json",
                 "hw/soc/core-only-chip-io-contract.json", "sw/golden/chip_status.py",
                 "hw/soc/rtl/chip/soc_status_serial.v", "sw/tests/test_chip_io.py",
                 "sw/tests/test_core_only_chip_io.py", "scripts/qualify_core_only_chip_io.py"]
        protected = {p: sha(ROOT / p) for p in paths}
        run = api("actions/runs/44238569057")
        assert run["head_sha"] == "bfb1fcc1bcd1d2def770ac26bd978767b0466e32"
        assert run["status"] == "completed" and run["conclusion"] == "success" and run["run_attempt"] == 1
        mapping = archive(14398058785, "a672ab826934df936115b0112382df52a79951f2e76d2faa935e488cf1d45f9b")
        report = json.loads(mapping.read("mapping.json"))
        native = archive(14397659747, "39123d25a3306248ab3a682810c3f24ccda1b0f00ff4454778960cb4cab8c8cc")
        with tarfile.open(fileobj=io.BytesIO(native.read("build.tgz"))) as tar:
            data = tar.extractfile("hw/soc/out/core-only-mainchip/synthesis/soc_top.mapped.json").read()
        assert hashlib.sha256(data).hexdigest() == report["outputs"]["synthesis/soc_top.mapped.json"]
        source = OUT / "core.mapped.json"; source.write_bytes(data)
        subprocess.run([sys.executable, "scripts/generate_chip_io.py", "--profile", "core-only",
                        "--core-json", str(source), "--output", str(OUT / "generated")], check=True)
        altered = OUT / "altered.mapped.json"; altered.write_bytes(data + b"\n")
        rejected = subprocess.run([sys.executable, "scripts/generate_chip_io.py", "--profile", "core-only",
                                   "--core-json", str(altered), "--output", str(OUT / "rejected")],
                                  capture_output=True, text=True)
        assert rejected.returncode != 0 and "differs from the reviewed contract" in rejected.stderr
        assert not (OUT / "rejected").exists()
        altered.unlink()
        # Compare legacy emitted RTL and pad inventory byte-for-byte to the unchanged parent.
        old = api("contents/scripts/generate_chip_io.py?ref=d6e690676c9f1fecaccea89b0ef4fcc6146d2e1b")
        namespace = {"__name__": "legacy_reference", "__file__": str(ROOT / "scripts/generate_chip_io.py")}
        exec(compile(base64.b64decode(old["content"]), "legacy_reference.py", "exec"), namespace)
        spec = importlib.util.spec_from_file_location("new_chip_generator", ROOT / "scripts/generate_chip_io.py")
        new = importlib.util.module_from_spec(spec); spec.loader.exec_module(new)
        legacy = json.loads((ROOT / "hw/soc/chip-io-contract.json").read_text())
        assert new.generate(legacy) == namespace["generate"](legacy)
        with (OUT / "pytest.log").open("w") as log:
            code = subprocess.call([sys.executable, "-m", "pytest", "-q",
                                    "sw/tests/test_chip_io.py", "sw/tests/test_core_only_chip_io.py",
                                    "--junitxml=" + str(OUT / "pytest.xml")],
                                   stdout=log, stderr=subprocess.STDOUT)
        print((OUT / "pytest.log").read_text(), flush=True)
        assert code == 0
        cases = ET.parse(OUT / "pytest.xml").getroot().findall(".//testcase")
        assert len(cases) == 19 and all(not list(c) for c in cases)
        assert all(sha(ROOT / p) == h for p, h in protected.items())
        manifest = json.loads((OUT / "generated/manifest.json").read_text())
        result.update(status="STRUCTURAL_CORE_ONLY_IO_TESTED_NOT_PHYSICAL", tests_passed=len(cases),
                      legacy_output_unchanged=True, changed_core_rejected=True,
                      protected_inputs=protected, sources_unchanged=True,
                      mapped_json_sha256=sha(source), generated_manifest=manifest,
                      scope="Generated chip wiring and real status-mailbox RTL tested with explicit core and I/O-cell stubs. Actual core boot, transistor pad models, CDC constraints, padframe placement/routing, DRC/LVS, ESD and package qualification remain separate.")
        source.unlink()
    except BaseException as error:
        result.update(status="FAIL_OR_ERROR", error=repr(error))
        raise
    finally:
        result["outputs"] = {str(p.relative_to(OUT)): sha(p) for p in OUT.rglob("*")
                             if p.is_file() and p.name != "result.json"}
        (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")

if __name__ == "__main__":
    main()
