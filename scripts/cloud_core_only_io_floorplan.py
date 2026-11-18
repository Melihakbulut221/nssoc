#!/usr/bin/env python3
"""Place native pads for the core-only port contract; no integrated chip claim."""
import base64
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from qualify_core_only_chip_io import archive
ROOT = Path.cwd().resolve()
OUT = ROOT / "hw/soc/out/core-only-io-floorplan"
REV = "c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c"
PINS = {"lef": "8b3dc3960960c08e07a1cde3dd9cd0484f5b12df07c4628726fff551bb775c0c",
        "gds": "aafb713ba3cd547ca48e919ec68eb6a8ed0f09051fed0fad813d3fdb043a4fa5"}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    OUT.mkdir(parents=True, exist_ok=False)
    result = dict(status="PREPARING", source_head=os.environ["GITHUB_SHA"], accepted=False,
                  contains_core=False, signals_routed=False, full_chip_lvs_passed=False,
                  manufacturing_approval=False)
    try:
        version = importlib.metadata.version("klayout")
        assert version == "0.30.9"
        result["klayout_python_version"] = version
        paths = [Path(__file__), ROOT/"scripts/qualify_core_only_chip_io.py",
                 ROOT/"scripts/generate_chip_io.py", ROOT/"scripts/make_chip_io_floorplan.py",
                 ROOT/"hw/soc/core-only-chip-io-contract.json"]
        protected = {str(p): sha(p) for p in paths}
        mapped = archive(14398058785, "a672ab826934df936115b0112382df52a79951f2e76d2faa935e488cf1d45f9b")
        mapping = json.loads(mapped.read("mapping.json"))
        assert mapping["source_head"] == "bfb1fcc1bcd1d2def770ac26bd978767b0466e32"
        native = archive(14397659747, "39123d25a3306248ab3a682810c3f24ccda1b0f00ff4454778960cb4cab8c8cc")
        with tarfile.open(fileobj=io.BytesIO(native.read("build.tgz"))) as tar:
            data = tar.extractfile("hw/soc/out/core-only-mainchip/synthesis/soc_top.mapped.json").read()
        assert hashlib.sha256(data).hexdigest() == mapping["outputs"]["synthesis/soc_top.mapped.json"]
        core_json = OUT/"core.mapped.json"
        core_json.write_bytes(data)
        generated = OUT/"generated"
        subprocess.run([sys.executable,"scripts/generate_chip_io.py","--profile","core-only",
                        "--core-json",str(core_json),"--output",str(generated)],check=True)
        manifest = json.loads((generated/"manifest.json").read_text())
        assert manifest["signal_pads"] == 76 and manifest["supply_pads"] == 4
        pdk = OUT/"pdk"; sources = {}
        for ext, expected in PINS.items():
            relative = "libs.ref/sg13g2_io/"+ext+"/sg13g2_io."+ext
            endpoint = "repos/IHP-GmbH/IHP-Open-PDK/contents/ihp-sg13g2/"+relative+"?ref="+REV
            row = json.loads(subprocess.check_output(["gh","api",endpoint]))
            if row.get("encoding") != "base64":
                row = json.loads(subprocess.check_output(["gh","api","repos/IHP-GmbH/IHP-Open-PDK/git/blobs/"+row["sha"]]))
            data = base64.b64decode(row["content"])
            assert hashlib.sha256(data).hexdigest() == expected
            path = pdk/relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            sources[str(path)] = expected
        with (OUT/"placement.log").open("w") as log:
            code = subprocess.call([sys.executable,"scripts/make_chip_io_floorplan.py",
                "--pdk",str(pdk),"--pads",str(generated/"pads.json"),"--output",str(OUT/"floorplan")],
                stdout=log,stderr=subprocess.STDOUT)
        assert code == 0, (OUT/"placement.log").read_text()
        placed = json.loads((OUT/"floorplan/result.json").read_text())
        assert placed["status"] == "PASS_NATIVE_IO_PLACEMENT_AND_ABSTRACT_RAIL_ABUTMENT_ONLY"
        assert placed["signal_and_supply_cells"] == 80 and placed["corners"] == 4
        assert not placed["contains_core"] and not placed["signals_routed"]
        assert sha(OUT/"floorplan/io-floorplan.gds") == placed["output_sha256"]
        assert all(sha(p) == h for p,h in {**protected,**sources}.items())
        result.update(status="CORE_ONLY_NATIVE_PAD_PLACEMENT_COMPLETE_NOT_INTEGRATED_CHIP",
            upstream_revision=REV, protected_inputs=protected, native_sources=sources,
            source_mapping_run=44238569057, mapped_json_sha256=sha(core_json),
            generated_manifest=manifest, placement=placed, sources_unchanged=True,
            scope="Current core-only 76 signal + 4 supply pads, native IHP corners/fillers. Provisional 4.0x3.2 mm ring, LEF footprint/rail abutment and streamed GDS instance readback. No core/mailbox placement, signal routing, transistor LVS, chip DRC, power/ESD/package or timing approval.")
    except BaseException as error:
        result.update(status="FAIL_OR_ERROR",error=repr(error));raise
    finally:
        result["outputs"] = {str(p.relative_to(OUT)):sha(p) for p in OUT.rglob("*")
            if p.is_file() and p != OUT/"result.json"}
        (OUT/"result.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__ == "__main__": main()
