#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Route the hash-bound repaired chip ring on an independent worker.

This completes routing/streamout only. Native DRC, antenna, density, LVS and
timing remain separate gates. No elapsed watchdog is imposed by this runner.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import resource
import subprocess
import time

from run_chip_native_shard import restore
from fetch_evidence_assets import fetch, validate, verify
from bootstrap_flow import verify as verify_tool

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def relocate(template, original, bundle, metadata):
    """Only approved absolute path prefixes may differ from the local recipe."""
    if isinstance(template, dict):
        if not isinstance(original, dict) or template.keys() != original.keys():
            raise ValueError("Configuration keys changed")
        return {k: relocate(v, original[k], bundle, metadata) for k, v in template.items()}
    if isinstance(template, list):
        if not isinstance(original, list) or len(template) != len(original):
            raise ValueError("Configuration list changed")
        return [relocate(v, old, bundle, metadata) for v, old in zip(template, original)]
    if isinstance(template, str) and template.startswith("@BUNDLE@/"):
        relative = PurePosixPath(template[len("@BUNDLE@/"):])
        if relative.is_absolute() or ".." in relative.parts or "\\" in str(relative):
            raise ValueError("Escaping bundle path")
        parts = relative.parts
        if parts and parts[0] == "workspace":
            old = Path(metadata["workspace"]).joinpath(*parts[1:])
        elif len(parts) >= 2 and parts[:2] == ("pdk", "ihp-sg13g2"):
            old = Path(metadata["pdk"]).joinpath(*parts[2:])
        else:
            raise ValueError("Unrecognized bundle path")
        path = (bundle / str(relative)).resolve()
        if str(old) != original or not path.is_relative_to(bundle.resolve()) or not path.exists():
            raise ValueError("Missing or changed relocated input")
        return str(path)
    if (type(template) is not type(original) or template != original
            or (isinstance(template, str) and template.startswith("/"))):
        raise ValueError("Non-path configuration changed or absolute path left unresolved")
    return template


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    out = ROOT / "hw/soc/out/cloud-ring-routing"
    out.mkdir(parents=True, exist_ok=False)
    rec = dict(status="PREPARING", physical_acceptance=False, manufacturing_approval=False)

    def save():
        (out / "result.json").write_text(json.dumps(rec, indent=2) + "\n")

    try:
        save()
        manifest = ROOT / "docs/evidence/chip-ring-routing-input-assets-20260928.json"
        rows = validate(json.loads(manifest.read_text()))
        if len(rows) != 1:
            raise ValueError("Exactly one input bundle required")
        if args.archive:
            archive = args.archive.resolve()
            verify(archive, rows[0])
        else:
            fetch(rows[0], out)
            archive = out / rows[0]["name"]
        bundle = out / "bundle"
        inventory = restore(archive, bundle)
        meta = json.loads((bundle / "relocation.json").read_text())
        for kind in ("config", "state"):
            template = json.loads((bundle / (kind + ".template.json")).read_text())
            original = json.loads((bundle / ("original-" + kind + ".json")).read_text())
            relocated = relocate(template, original, bundle, meta)
            (out / (kind + ".json")).write_text(json.dumps(relocated, indent=2) + "\n")
        config = json.loads((out / "config.json").read_text())
        if config["DESIGN_NAME"] != "nssoc_chip" or config["PDN_CORE_RING_HSPACING"] != 5:
            raise ValueError("Wrong repaired-ring candidate")
        flow = (bundle / meta["flow"]).resolve()
        if not flow.is_relative_to(bundle) or not flow.is_file():
            raise ValueError("Missing or escaping flow source")
        app = ROOT / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"
        verify_tool(app, "x86_64")
        command = [str(app), "python", str(flow), "--flow", "ChipAssembly", "--manual-pdk",
                   "--pdk-root", str(bundle / "pdk"), "--pdk", "ihp-sg13g2",
                   "--force-run-dir", str(out / "run"), "--from", "Odb.RemovePDNObstructions",
                   "--with-initial-state", str(out / "state.json"), str(out / "config.json")]
        rec.update(status="PREPARED", input_bundle_sha256=rows[0]["sha256"],
                   input_files=len(inventory), command=command,
                   scope="Repaired-ring routing candidate only; core0/0; all native physical and final timing gates remain required.")
        pins = {str(p): digest(p) for p in [Path(__file__).resolve(),
                ROOT / "scripts/run_chip_native_shard.py", ROOT / "scripts/fetch_evidence_assets.py",
                ROOT / "scripts/bootstrap_flow.py", manifest, app,
                out / "config.json", out / "state.json"]}
        rec["input_sha256"] = pins
        save()
        if args.prepare_only:
            return 0
        (out / "run").mkdir(exist_ok=False)
        rec["status"] = "RUNNING_RING_ROUTING"
        save()
        start = time.monotonic()
        with (out / "run.log").open("x") as stream:
            child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, preexec_fn=limits)
            rec["child_pid"] = child.pid
            save()
            code = child.wait()
        rec.update(returncode=code, elapsed_seconds=time.monotonic() - start)
        if code:
            raise RuntimeError("Physical routing failed; preserve raw diagnostics")
        # The immutable bundle must also remain unchanged during tool execution.
        for name, row in inventory.items():
            if digest(bundle / name) != row["sha256"]:
                raise ValueError("Input modified during routing: " + name)
        if any(digest(path) != sha for path, sha in pins.items()):
            raise ValueError("Routing method or relocated input changed")
        final = json.loads((out / "run/final/state.json").read_text())
        gds = Path(final["klayout_gds"]).resolve()
        if not gds.is_relative_to(out / "run") or not gds.is_file():
            raise ValueError("Missing candidate GDS")
        rec.update(status="ROUTED_REQUIRES_NATIVE_PHYSICAL_AUDITS", gds=str(gds), gds_sha256=digest(gds))
        save()
        return 0
    except Exception as exc:
        rec.update(status="ERROR", error=repr(exc))
        save()
        raise


if __name__ == "__main__":
    raise SystemExit(main())
