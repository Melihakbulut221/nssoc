#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Add immutable local native captures to the existing evidence release.

Never replace an asset. Verify metadata plus authenticated and anonymous
streaming downloads against the same local bytes. This is preservation,
not an independent simulation or physical acceptance gate.
"""

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

REPO = "Melihakbulut221/nssoc"
TAG = "evidence-20260927-chip-io"


def digest(stream):
    h = hashlib.sha256()
    size = 0
    while chunk := stream.read(1024 * 1024):
        h.update(chunk)
        size += len(chunk)
    return dict(bytes=size, sha256=h.hexdigest())


def api(path):
    return json.loads(subprocess.check_output(["gh", "api", f"repos/{REPO}/{path}"]))


def authenticated(asset):
    with subprocess.Popen(
        [
            "gh",
            "api",
            f"repos/{REPO}/releases/assets/{asset['id']}",
            "-H",
            "Accept: application/octet-stream",
        ],
        stdout=subprocess.PIPE,
    ) as p:
        actual = digest(p.stdout)
        if p.wait():
            raise RuntimeError("Authenticated download failed")
    return actual


def anonymous(asset):
    req = urllib.request.Request(
        asset["browser_download_url"],
        headers={"User-Agent": "nssoc-evidence-roundtrip/1"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return digest(response)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("files", nargs="+", type=Path)
    a = p.parse_args()
    if a.out.exists():
        p.error("Use a fresh receipt path")
    if len({x.name for x in a.files}) != len(a.files):
        p.error("Ambiguous asset basenames")
    local = []
    for path in a.files:
        if not path.is_file() or path.is_symlink():
            p.error("Only regular files")
        with path.open("rb") as f:
            local.append(dict(path=str(path.resolve()), name=path.name, **digest(f)))
    record = dict(
        status="RUNNING",
        repo=REPO,
        tag=TAG,
        files=local,
        assets=[],
        physical_acceptance=False,
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)

    def save():
        a.out.write_text(json.dumps(record, indent=2) + "\n")

    save()
    try:
        for row in local:
            release = api(f"releases/tags/{TAG}")
            found = [x for x in release["assets"] if x["name"] == row["name"]]
            if not found:
                # On an uncertain transport response, a subsequent invocation
                # inspects existing release state; it never uses --clobber.
                subprocess.run(
                    ["gh", "release", "upload", TAG, row["path"], "--repo", REPO],
                    check=True,
                )
                found = [
                    x
                    for x in api(f"releases/tags/{TAG}")["assets"]
                    if x["name"] == row["name"]
                ]
            if len(found) != 1:
                raise ValueError("Missing/ambiguous asset")
            asset = found[0]
            expected = dict(bytes=row["bytes"], sha256=row["sha256"])
            if (asset["size"], asset["digest"], asset["state"]) != (
                row["bytes"],
                "sha256:" + row["sha256"],
                "uploaded",
            ):
                raise ValueError("Existing asset differs; refusing replacement")
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                auth = pool.submit(authenticated, asset)
                anon = pool.submit(anonymous, asset)
                verified = (auth.result(), anon.result())
            if verified != (expected, expected):
                raise ValueError("Download byte mismatch")
            with Path(row["path"]).open("rb") as f:
                if digest(f) != expected:
                    raise ValueError("Local capture changed")
            record["assets"].append(
                dict(
                    name=row["name"],
                    asset_id=asset["id"],
                    url=asset["browser_download_url"],
                    **expected,
                    authenticated_roundtrip=True,
                    anonymous_roundtrip=True,
                )
            )
            save()
            print("VERIFIED", row["name"], flush=True)
        record["status"] = "PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"
    except BaseException as error:
        record.update(status="FAIL", error=repr(error))
    finally:
        save()
    return record["status"] != "PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"


if __name__ == "__main__":
    raise SystemExit(main())
