# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read every published local capsule member; no simulation or solver execution."""
import hashlib
import json
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path

R = Path.cwd()
O = Path(__file__).resolve().parent


def pin(p):
    p = Path(p)
    with p.open("rb") as f:
        return {"bytes": p.stat().st_size, "sha256": hashlib.file_digest(f, "sha256").hexdigest()}


def load(p):
    return json.loads(Path(p).read_text())


rows = []
for version, prefix, validation in [
    (5, "default-controls", "pcie-integrity-v5-default-controls-validation-20261005.json"),
    (9, "controls", "pcie-integrity-v9-core-controls-validation-20261005.json"),
    (7, "maximum-controls", "pcie-integrity-v7-max4118-validation-20261005.json"),
]:
    base = R / f"hw/soc/out/pcie-integrity-v{version}-20261005"
    v = load(base / validation)
    mpath = base / f"{prefix}-members.json"
    m = load(mpath)
    release = load(base / f"{prefix}-release.json")
    assert release["status"] == "PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"
    asset = next(a for a in release["assets"] if a["name"].endswith(".tar.xz"))
    a = base / asset["name"]
    assert pin(a) == {k: asset[k] for k in ("bytes", "sha256")}
    assert asset["authenticated_roundtrip"] and asset["anonymous_roundtrip"]
    expected = {n: {k: h[k] for k in ("bytes", "sha256")} for n, h in m.items()}
    expected["members.json"] = pin(mpath)
    seen = {}
    xml = []
    results = []
    with tarfile.open(a, "r|xz") as t:
        for member in t:
            name = member.name
            assert member.isfile() and name not in seen and not Path(name).is_absolute()
            assert ".." not in Path(name).parts
            f = t.extractfile(member)
            h = hashlib.sha256()
            n = 0
            keep = name.endswith(("results.xml", "result.json")) and member.size < 1024 * 1024
            chunks = []
            while b := f.read(1024 * 1024):
                n += len(b)
                h.update(b)
                if keep:
                    chunks.append(b)
            assert n == member.size
            seen[name] = {"bytes": n, "sha256": h.hexdigest()}
            if keep and name.endswith("results.xml"):
                counts = [0, 0, 0]
                names = []
                for case in ET.fromstring(b"".join(chunks)).iter("testcase"):
                    names.append(case.attrib.get("name"))
                    if case.find("skipped") is not None:
                        counts[2] += 1
                    elif case.find("failure") is not None or case.find("error") is not None:
                        counts[1] += 1
                    else:
                        counts[0] += 1
                xml.append({"member": name, "counts": counts, "cases": names})
            if keep and name.endswith("result.json"):
                d = json.loads(b"".join(chunks))
                if all(k in d for k in ("passed", "failed", "skipped")):
                    results.append({"member": name, "counts": [d[k] for k in ("passed", "failed", "skipped")]})
    assert seen == expected, (set(seen) - set(expected), set(expected) - set(seen))
    for r in results:
        stem = str(Path(r["member"]).parent)
        x = next((x for x in xml if str(Path(x["member"]).parent) == stem), None)
        if x:
            assert x["counts"] == r["counts"]
    sources = v.get("sources")
    if sources is None:
        freeze = load(base / "source-freeze.json")
        assert pin(base / "source-freeze.json") == v["source_freeze"]
        sources = freeze["files"]
    for name, h in sources.items():
        assert pin(R / name) == h
        assert h in seen.values(), name
    if version == 7:
        assert len(xml) == 1 and xml[0]["counts"] == [13, 0, 0]
        assert xml[0]["cases"] == v["cases"]
    rows.append({
        "version": version, "release": str((base / f"{prefix}-release.json").relative_to(R)),
        "release_pin": pin(base / f"{prefix}-release.json"),
        "validation": {"path": str((base / validation).relative_to(R)), **pin(base / validation)},
        "archive": {"path": str(a), **pin(a)}, "publication": asset,
        "members_rehashed": len(seen), "current_source_pins_rehashed": len(sources),
        "saved_XML_recounts": xml,
    })

result = {
    "status": "PASS_LOCAL_FULL_MEMBER_SOURCE_AND_SAVED_XML_ADDENDA_AUDIT",
    "method": pin(Path(__file__)), "components": rows,
    "scope": "Full local capsule and all member hashes compared against manifests and retained dual-roundtrip publication digests; current source pins and saved XML recounted. No fresh network retrieval, HDL/SAT/native rerun or full protocol/physical acceptance. Separate V5 compiled-preservation archive was not fetched in this audit.",
}
(O / "addenda-archive-audit.json").write_text(json.dumps(result, indent=2) + "\n")
print([(r["version"], r["members_rehashed"], len(r["saved_XML_recounts"])) for r in rows])
print(pin(O / "addenda-archive-audit.json"))
