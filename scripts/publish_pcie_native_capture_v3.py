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
import sys
import threading
import time
import urllib.error
import urllib.request

import characterize_pcie_clock_trim_stream_v2 as lifecycle
import publish_pcie_native_capture_v2 as previous

TRANSPORT_CLEANUP_GRACE_SECONDS = 1.0
STDERR_CAPTURE_LIMIT = 256 * 1024
READ_CHUNK_BYTES = 65536

OWNER_SHA = '39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886'

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
        "nssoc_transient_transport", "tls handshake timeout", "connection reset", "connection refused",
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
        if pin(lifecycle.__file__)["sha256"] != OWNER_SHA:
            raise IntegrityError("Frozen process owner changed")
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
                if self.stop.is_set():
                    row.update(status="FATAL_NO_RETRY", error=str(error), explicit_stop=True)
                    raise lifecycle.Cancelled("Explicit publisher stop during transport completion") from error
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
        stderr_complete = False
        stdout_complete = False
        stderr_limited = False
        process = None
        selector = selectors.DefaultSelector()
        prior_grace = lifecycle.FAILURE_GRACE_SECONDS
        lifecycle.FAILURE_GRACE_SECONDS = TRANSPORT_CLEANUP_GRACE_SECONDS
        try:
            with stderr.open("xb") as err, stdout.open("xb") as out:
                owner = lifecycle.ProcessOwner(owner_path)
                original_cancel = owner.request_cancel
                def request_cancel(reason):
                    # Propagate actual signal cancellation on every exit path,
                    # including a transient error raised before context teardown.
                    # Ordinary timeout/failure cleanup must remain retryable.
                    if str(reason) in ("Parent received SIGINT", "Parent received SIGTERM"):
                        self.stop.set()
                    original_cancel(reason)
                owner.request_cancel = request_cancel
                with owner:
                    process = owner.launch("publisher", command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
                    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
                    while selector.get_map():
                        self.check()
                        owner.check()
                        if time.monotonic() - started >= self.timeout:
                            timeout = True
                            raise TransportError("Bounded transport deadline exceeded")
                        for key, _ in selector.select(0.05):
                            chunk = os.read(key.fd, READ_CHUNK_BYTES)
                            if not chunk:
                                selector.unregister(key.fileobj)
                                if key.data == "stderr": stderr_complete = True
                                else: stdout_complete = True
                            elif key.data == "stderr":
                                err.write(chunk)
                                if err.tell() > STDERR_CAPTURE_LIMIT:
                                    stderr_limited = True
                                    raise IntegrityError("Stderr resource limit: retained received prefix; child terminated")
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
                        err.flush()
                        text = stderr.read_text(errors="replace")
                        if transient_text(text):
                            raise TransportError("Classified transient child transport failure; exact stderr retained")
                        raise RuntimeError("Non-retryable child failure; exact stderr retained")
            # A signal after complete() can set only the nested owner flag.
            # Check both owners after context cleanup/handler restoration.
            owner.check()
            self.check()
            return stdout.read_bytes() if prefix is None else prefix.record()
        finally:
            lifecycle.FAILURE_GRACE_SECONDS = prior_grace
            selector.close()
            if process is not None:
                row["returncode"] = process.poll()
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()
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
                       deadline_triggered=timeout, stderr_capture_complete=stderr_complete,
                       stdout_capture_complete=stdout_complete, stderr_limit_bytes=STDERR_CAPTURE_LIMIT,
                       stderr_limit_triggered=stderr_limited, final_chunk_maximum_bytes=READ_CHUNK_BYTES,
                       stderr=preserve(stderr),
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
        # A separate owned worker makes the whole urllib transfer (DNS, redirects,
        # handshake and reads) interruptible under the same hard deadline.
        def operation(directory, row):
            row.update(asset=asset, retained_local_source=dict(path=str(source), **expected))
            prefix = Prefix(source, directory)
            try:
                self.command([sys.executable, str(Path(__file__).resolve()),
                              "--anonymous-worker", asset["browser_download_url"],
                              str(directory / "http-response.json")], directory, row, prefix)
                if {k:prefix.record()[k] for k in ("bytes", "sha256")} != expected:
                    raise IntegrityError("Anonymous completed body has wrong length/hash")
                return expected
            finally:
                response = directory / "http-response.json"
                if response.exists(): row["response"] = dict(path=str(response), **pin(response))
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


def anonymous_worker(url, metadata):
    """Only transport I/O; parent owns this process group and deadline."""
    record = dict(status="RUNNING")
    try:
        request = urllib.request.Request(url, headers={"User-Agent":"nssoc-evidence-roundtrip/3"})
        with urllib.request.urlopen(request, timeout=5.0) as response:
            record.update(status="HTTP_RESPONSE", http_status=response.status,
                          headers=dict(response.headers))
            save(metadata, record)
            while chunk := response.read(65536):
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
        record["status"] = "COMPLETE_HTTP_STREAM"
        save(metadata, record)
        return 0
    except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead) as error:
        # Exact exception stderr is retained by the owned parent. The original
        # local capture remains the source for any verified received prefix.
        retryable = isinstance(error, (TimeoutError, ConnectionError, http.client.IncompleteRead))
        if isinstance(error, http.client.IncompleteRead) and error.partial:
            sys.stdout.buffer.write(error.partial); sys.stdout.buffer.flush()
        if isinstance(error, urllib.error.HTTPError):
            retryable = error.code in (429,500,502,503,504)
            record.update(http_status=error.code, headers=dict(error.headers))
            body = metadata.with_name("http-error-body.bin")
            with body.open("xb") as out:
                while chunk := error.read(65536):
                    out.write(chunk)
                    if out.tell() > 4*1024**2:
                        record["error_body_prefix_only"] = True
                        break
            record["error_body"] = dict(path=str(body), **pin(body))
        elif isinstance(error, urllib.error.URLError):
            retryable = isinstance(error.reason,(TimeoutError,ConnectionError)) or transient_text(str(error.reason))
        record.update(status="HTTP_TRANSPORT_FAILURE", exception=repr(error), retryable=retryable)
        save(metadata,record)
        print("NSSOC_TRANSIENT_TRANSPORT" if retryable else "NSSOC_PERMANENT_TRANSPORT",repr(error),file=sys.stderr)
        return 75 if retryable else 1


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
                per_attempt_deadline_seconds=a.timeout,source=pin(__file__),predecessor=pin(previous.__file__),process_owner=pin(lifecycle.__file__))
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
    if len(sys.argv)==4 and sys.argv[1]=="--anonymous-worker":
        raise SystemExit(anonymous_worker(sys.argv[2],Path(sys.argv[3])))
    raise SystemExit(main())
