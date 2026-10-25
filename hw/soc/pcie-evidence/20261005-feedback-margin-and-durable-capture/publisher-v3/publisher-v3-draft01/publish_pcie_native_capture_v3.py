#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded transport retries, immutable assets, exact retained download prefixes.

This publisher changes no native capture or acceptance criterion. Failed transfer
prefixes that equal the retained local capture are represented losslessly by its
pin and prefix length/hash; differing received chunks are saved and never retried.
Each child group is owned by the existing PID/start-guarded process owner.
"""
import argparse
import hashlib
import gzip
import http.client
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request

import characterize_pcie_clock_trim_stream_v2 as lifecycle
import publish_pcie_native_capture_v2 as previous

TRANSPORT_CLEANUP_GRACE_SECONDS = 1.0

PREVIOUS_SHA = "70ea108b29f1fcd07ec6d4759a3caac97db3da862a6d49d4e696154572509bf3"
REPO, TAG = previous.REPO, previous.TAG


class IntegrityError(ValueError):
    pass


class TransportError(RuntimeError):
    pass


def pin(path):
    with Path(path).open("rb") as f:
        return previous.digest(f)


def save(path, value):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as f:
        json.dump(value, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary, path)


def transient_text(text):
    text = text.lower()
    return any(word in text for word in (
        "tls handshake timeout", "connection reset", "connection refused",
        "temporary failure", "i/o timeout", "timed out", "unexpected eof",
        "http 429", "http 500", "http 502", "http 503", "http 504",
    ))


class Prefix:
    """Retain a received stream exactly without duplicating its verified prefix."""
    def __init__(self, source, directory):
        self.source = Path(source)
        self.file = self.source.open("rb")
        self.directory = directory
        self.hash = hashlib.sha256()
        self.bytes = 0
        self.matched = 0
        self.mismatch = None

    def consume(self, chunk):
        self.hash.update(chunk)
        self.bytes += len(chunk)
        if self.file.read(len(chunk)) != chunk:
            p = self.directory / "mismatching-chunk.bin"
            p.write_bytes(chunk)
            self.mismatch = dict(path=str(p), offset=self.matched, **pin(p))
            raise IntegrityError("Received bytes differ from retained capture")
        self.matched += len(chunk)

    def record(self):
        return dict(bytes=self.bytes, sha256=self.hash.hexdigest(),
                    matched_local_prefix_bytes=self.matched,
                    reconstruction="retained local source prefix, then mismatching chunk if present",
                    mismatching_chunk=self.mismatch)

    def close(self):
        self.file.close()


class Client:
    def __init__(self, directory, attempts=4, timeout=120.0, backoff=1.0):
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=False)
        self.attempts, self.timeout, self.backoff = attempts, timeout, backoff
        self.stop = threading.Event()
        self.journal = []
        self.serial = 0

    def check(self):
        if self.stop.is_set():
            raise lifecycle.Cancelled("Explicit publisher stop")

    def retry(self, kind, operation):
        for attempt in range(1, self.attempts + 1):
            self.check()
            self.serial += 1
            directory = self.directory / f"{self.serial:04d}-{kind}-attempt{attempt}"
            directory.mkdir()
            row = dict(kind=kind, attempt=attempt, directory=str(directory), status="RUNNING")
            self.journal.append(row)
            save(self.directory / "attempts.json", self.journal)
            try:
                result = operation(directory, row)
                row["status"] = "PASS"
                return result
            except TransportError as error:
                row.update(status="TRANSPORT_FAILURE", error=str(error))
                if attempt == self.attempts:
                    raise
            except BaseException as error:
                row.update(status="FATAL_NO_RETRY", error=repr(error))
                raise
            finally:
                save(self.directory / "attempts.json", self.journal)
            self.stop.wait(min(self.backoff * 2 ** (attempt - 1), 8.0))
        raise AssertionError("Unreachable retry completion")

    def command(self, command, directory, row, prefix=None):
        """Bounded streaming child; save all stderr and retained stdout evidence."""
        stderr = directory / "stderr.bin"
        stdout = directory / "stdout.bin"
        owner_path = directory / "owned-processes.json"
        row["command"] = list(map(str, command))
        started = time.monotonic()
        timeout = False
        process = None
        selector = selectors.DefaultSelector()
        prior_grace = lifecycle.FAILURE_GRACE_SECONDS
        lifecycle.FAILURE_GRACE_SECONDS = TRANSPORT_CLEANUP_GRACE_SECONDS
        try:
            with stderr.open("xb") as err, stdout.open("xb") as out:
                with lifecycle.ProcessOwner(owner_path) as owner:
                    process = owner.launch("publisher", command, stdout=subprocess.PIPE, stderr=err)
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while selector.get_map():
                        self.check()
                        owner.check()
                        if time.monotonic() - started >= self.timeout:
                            timeout = True
                            raise TransportError("Bounded transport deadline exceeded")
                        for key, _ in selector.select(0.05):
                            chunk = os.read(key.fd, 65536)
                            if not chunk:
                                selector.unregister(key.fileobj)
                            elif prefix is not None:
                                prefix.consume(chunk)
                            else:
                                out.write(chunk)
                                if out.tell() > 4 * 1024**2:
                                    raise IntegrityError("Metadata response exceeds explicit4MiB bound")
                    while process.poll() is None:
                        self.check()
                        owner.check()
                        if time.monotonic() - started >= self.timeout:
                            timeout = True
                            raise TransportError("Bounded transport deadline exceeded")
                        self.stop.wait(0.05)
                    code = owner.complete(process)
                    row["returncode"] = code
                    if code:
                        text = stderr.read_text(errors="replace")
                        if transient_text(text):
                            raise TransportError("Classified transient child transport failure; exact stderr retained")
                        raise RuntimeError("Non-retryable child failure; exact stderr retained")
            return stdout.read_bytes() if prefix is None else prefix.record()
        finally:
            lifecycle.FAILURE_GRACE_SECONDS = prior_grace
            selector.close()
            if process is not None:
                row["returncode"] = process.poll()
                if process.stdout:
                    process.stdout.close()
            def preserve(path):
                original = pin(path)
                compressed = path.with_suffix(path.suffix + ".gz")
                with path.open("rb") as src, gzip.open(compressed, "wb", compresslevel=3) as dst:
                    while chunk := src.read(65536): dst.write(chunk)
                with gzip.open(compressed, "rb") as src:
                    if previous.digest(src) != original: raise IntegrityError("Transport log readback differs")
                path.unlink()  # Exact compressed readback retained, no unique evidence removed.
                return dict(path=str(compressed), **pin(compressed), uncompressed=original)
            row.update(elapsed_seconds=time.monotonic()-started, deadline_seconds=self.timeout,
                       cleanup_grace_seconds=TRANSPORT_CLEANUP_GRACE_SECONDS,
                       deadline_triggered=timeout, stderr=preserve(stderr),
                       stdout=preserve(stdout), owned_processes=str(owner_path))
            if prefix is not None:
                row["observed_download"] = prefix.record()

    def api(self, path):
        def operation(directory, row):
            raw = self.command(["gh", "api", f"repos/{REPO}/{path}"], directory, row)
            try:
                return json.loads(raw)
            except ValueError as error:
                raise IntegrityError("Invalid metadata JSON") from error
        return self.retry("metadata", operation)

    def authenticated(self, asset, source, expected):
        def operation(directory, row):
            row.update(asset=asset, retained_local_source=dict(path=str(source), **expected))
            prefix = Prefix(source, directory)
            try:
                self.command(["gh", "api", f"repos/{REPO}/releases/assets/{asset['id']}",
                              "-H", "Accept: application/octet-stream"], directory, row, prefix)
                if {k:prefix.record()[k] for k in ("bytes", "sha256")} != expected:
                    raise IntegrityError("Authenticated completed body has wrong length/hash")
                return expected
            finally:
                prefix.close()
        return self.retry("authenticated", operation)

    def anonymous(self, asset, source, expected):
        def operation(directory, row):
            row.update(asset=asset, retained_local_source=dict(path=str(source), **expected))
            prefix = Prefix(source, directory)
            started = time.monotonic()
            try:
                request = urllib.request.Request(asset["browser_download_url"],
                                                 headers={"User-Agent":"nssoc-evidence-roundtrip/3"})
                with urllib.request.urlopen(request, timeout=min(self.timeout, 5.0)) as response:
                    row["response"] = dict(status=response.status, headers=dict(response.headers))
                    while True:
                        self.check()
                        if time.monotonic()-started >= self.timeout:
                            raise TransportError("Bounded anonymous deadline exceeded")
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        prefix.consume(chunk)
                if {k:prefix.record()[k] for k in ("bytes", "sha256")} != expected:
                    raise IntegrityError("Anonymous completed body has wrong length/hash")
                return expected
            except (urllib.error.URLError, TimeoutError, http.client.IncompleteRead) as error:
                raw = directory / "exception.txt"
                raw.write_text(repr(error)+"\n")
                row["exception"] = dict(path=str(raw), **pin(raw))
                if isinstance(error, http.client.IncompleteRead) and error.partial:
                    prefix.consume(error.partial)
                retryable = isinstance(error, (TimeoutError, http.client.IncompleteRead))
                if isinstance(error, urllib.error.HTTPError):
                    retryable = error.code in (429,500,502,503,504)
                elif isinstance(error, urllib.error.URLError):
                    retryable = isinstance(error.reason, (TimeoutError, ConnectionError)) or transient_text(str(error.reason))
                if retryable:
                    raise TransportError("Classified transient anonymous transport failure; exact exception retained") from error
                raise
            finally:
                row.update(observed_download=prefix.record(), elapsed_seconds=time.monotonic()-started,
                           deadline_seconds=self.timeout, socket_timeout_seconds=min(self.timeout,5.0))
                prefix.close()
        return self.retry("anonymous", operation)

    def upload(self, tag, source):
        # Upload is attempted once. On uncertain failure caller re-queries state;
        # no retry can overwrite an existing asset and no --clobber is used.
        def operation(directory, row):
            return self.command(["gh","release","upload",tag,str(source),"--repo",REPO], directory,row)
        attempts = self.attempts
        try:
            self.attempts = 1
            return self.retry("upload", operation)
        finally:
            self.attempts = attempts


def validate_asset(asset, row):
    if (asset["size"],asset["digest"],asset["state"]) != (row["bytes"],"sha256:"+row["sha256"],"uploaded"):
        raise IntegrityError("Existing asset differs; refusing replacement")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--tag",default=TAG)
    parser.add_argument("--attempts",type=int,default=4)
    parser.add_argument("--timeout",type=float,default=120.0)
    parser.add_argument("files",nargs="+",type=Path)
    a=parser.parse_args()
    directory=a.out.with_suffix(".transport")
    if a.out.exists() or directory.exists():parser.error("Fresh receipt and transport directory required")
    if not 1<=a.attempts<=4 or not 0<a.timeout<=120:parser.error("At most4 attempts and120s per attempt")
    if len({p.name for p in a.files})!=len(a.files):parser.error("Ambiguous asset basenames")
    if pin(previous.__file__)["sha256"]!=PREVIOUS_SHA:parser.error("Frozen predecessor changed")
    local=[]
    for p in a.files:
        if not p.is_file() or p.is_symlink():parser.error("Only regular files")
        local.append(dict(path=str(p.resolve()),name=p.name,**pin(p)))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    client=Client(directory,a.attempts,a.timeout)
    record=dict(status="RUNNING",repo=REPO,tag=a.tag,files=local,assets=[],physical_acceptance=False,
                publisher_revision=3,transport_directory=str(directory),transport_attempts=a.attempts,
                per_attempt_deadline_seconds=a.timeout,source=pin(__file__),predecessor=pin(previous.__file__))
    handlers={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    for sig in handlers:signal.signal(sig,lambda signum,frame:client.stop.set())
    save(a.out,record)
    try:
        for row in local:
            client.check()
            found=[x for x in client.api(f"releases/tags/{a.tag}")["assets"] if x["name"]==row["name"]]
            if not found:
                try:
                    client.upload(a.tag,row["path"])
                except TransportError:
                    # An uncertain upload may have succeeded: inspect immutable state.
                    pass
                found=[x for x in client.api(f"releases/tags/{a.tag}")["assets"] if x["name"]==row["name"]]
            if len(found)!=1:raise IntegrityError("Missing/ambiguous asset after state reconciliation")
            asset=found[0];validate_asset(asset,row)
            expected={k:row[k] for k in ("bytes","sha256")}
            client.authenticated(asset,row["path"],expected)
            client.anonymous(asset,row["path"],expected)
            if pin(row["path"])!=expected:raise IntegrityError("Local capture changed")
            client.check()
            record["assets"].append(dict(name=row["name"],asset_id=asset["id"],url=asset["browser_download_url"],
                                         **expected,authenticated_roundtrip=True,anonymous_roundtrip=True))
            save(a.out,record)
            print("VERIFIED",row["name"],flush=True)
        record["status"]="PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"
    except BaseException as error:
        if isinstance(error, lifecycle.Cancelled): client.stop.set()
        record.update(status="FAIL",error=repr(error))
    finally:
        record["transport_journal"]=dict(path=str(directory/"attempts.json"),**pin(directory/"attempts.json")) if client.journal else None
        record["explicit_stop"]=client.stop.is_set()
        save(a.out,record)
        for sig,handler in handlers.items():signal.signal(sig,handler)
    return record["status"]!="PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"


if __name__=="__main__":
    raise SystemExit(main())
