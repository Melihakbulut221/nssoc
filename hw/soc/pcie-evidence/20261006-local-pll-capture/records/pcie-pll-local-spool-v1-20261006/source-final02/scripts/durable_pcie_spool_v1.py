#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Lossless local parts with durable ordering; no network or public verdicts.

The reservation is deliberately separate from the bounded payload. It is not a
filesystem quota. A failed commit retains staging/orphan bytes; it never makes
them silently part of the canonical stream or resumable solver state.
"""
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import json
import lzma
import os
from pathlib import Path
import re
import shutil


GIB = 1024**3
RAW_PART_CAP = 16 * 1024**2


@dataclass(frozen=True)
class Limits:
    reserve: int = 10 * GIB
    payload: int = 8 * GIB
    floor: int = GIB
    parts: int = 512


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    digest, size = hashlib.sha256(), 0
    with Path(path).open('rb') as stream:
        while chunk := stream.read(1024**2):
            digest.update(chunk)
            size += len(chunk)
    return dict(bytes=size, sha256=digest.hexdigest())


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def fresh_bytes(path, data):
    """Retain a short/failed write; never replace a previously existing file."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        offset = 0
        while offset < len(data):
            written = os.write(fd, memoryview(data)[offset:])
            require(written > 0, 'Incomplete durable write')
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.pending')
    fresh_bytes(temporary, encoded(value))
    os.replace(temporary, path)
    fsync_dir(path.parent)


def check_row(root, ledger, row, index, count, *, raw=False):
    require(set(row) == {'index', 'first_row', 'rows', 'name', 'uncompressed_bytes',
                        'uncompressed_sha256', 'bytes', 'sha256', 'status'},
            'Exact local row schema')
    require(row['index'] == index and row['first_row'] == count
            and type(row['rows']) is int and 0 < row['rows'] <= ledger['rows_per_part']
            and row['name'] == f"{ledger['prefix']}-part{index:05d}.bin.xz"
            and row['status'] == 'LOCAL_DURABLE'
            and row['uncompressed_bytes'] == row['rows'] * 8 * len(ledger['columns']),
            'Unique ordered complete local row')
    directory = Path(root) / 'committed' / f'{index:05d}'
    require(json.loads((directory / 'record.json').read_text()) == row,
            'Immutable row agrees with canonical ledger')
    path = directory / row['name']
    require(pin(path) == {k: row[k] for k in ('bytes', 'sha256')},
            'Exact retained compressed part')
    if raw:
        payload = lzma.decompress(path.read_bytes())
        require(len(payload) == row['uncompressed_bytes']
                and hashlib.sha256(payload).hexdigest() == row['uncompressed_sha256'],
                'Exact retained uncompressed part')
        return payload
    return path


def inspect_spool(root, *, raw=False):
    """Read canonical parts only; expose every staging and orphan directory."""
    root = Path(root)
    ledger = json.loads((root / 'parts.json').read_text())
    require(ledger['schema'] == 'PCIE_LOCAL_LOSSLESS_SPOOL_V1'
            and ledger['no_decimation'] is True
            and re.fullmatch(r'[a-z0-9][a-z0-9-]{4,110}', ledger['prefix'])
            and 0 < ledger['rows_per_part'] * 8 * len(ledger['columns']) <= RAW_PART_CAP,
            'Declared local stream identity')
    count, digest = 0, hashlib.sha256()
    for index, row in enumerate(ledger['parts']):
        result = check_row(root, ledger, row, index, count, raw=raw)
        if raw:
            digest.update(result)
        count += row['rows']
    require(count == ledger['committed_rows'], 'Exact canonical committed row count')
    expected = {f'{index:05d}' for index in range(len(ledger['parts']))}
    actual = {p.name for p in (root / 'committed').iterdir()}
    require(expected <= actual, 'No missing committed directory')
    staging = sorted(p.name for p in (root / 'staging').iterdir())
    orphans = sorted(actual - expected)
    if ledger['status'] == 'LOCAL_CAPTURE_COMPLETE':
        require(not staging and not orphans and count == ledger['rows'],
                'Complete capture has no uncommitted or orphan bytes')
        if raw:
            require(digest.hexdigest() == ledger['payload_sha256'],
                    'Complete local payload byte hash')
        for name, expected_pin in ledger['stream_metadata'].items():
            require(name in ('header.bin', 'trailer.bin')
                    and pin(root / name) == expected_pin, 'Exact durable stream metadata')
        require((root / 'trailer.bin').read_bytes() == str(count).encode(),
                'Exact durable native trailer')
    return dict(ledger=ledger, staging=staging, committed_orphans=orphans,
                rows=count, full_payload_rehashed=raw)


class Spool:
    def __init__(self, root, prefix, *, limits=Limits()):
        self.root, self.prefix, self.limits = Path(root), prefix, limits
        require(re.fullmatch(r'[a-z0-9][a-z0-9-]{4,110}', prefix), 'Safe unique prefix')
        require(all(type(v) is int and v > 0 for v in asdict(limits).values()),
                'Positive finite spool limits')
        require(shutil.disk_usage(self.root.parent).free >=
                limits.reserve + limits.payload + limits.floor, 'SSD entry reservation')
        self.root.mkdir()
        self.lock = (self.root / 'producer.lock').open('xb')
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for name in ('staging', 'committed'):
            (self.root / name).mkdir()
        reserve = self.root / 'reservation.bin'
        fd = os.open(reserve, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.posix_fallocate(fd, 0, limits.reserve)
            os.fsync(fd)
        finally:
            os.close(fd)
        require(reserve.stat().st_blocks * 512 >= limits.reserve,
                'Reservation must be physically allocated')
        fresh_bytes(self.root / 'configuration.json', encoded(dict(
            schema='PCIE_LOCAL_LOSSLESS_SPOOL_V1', prefix=prefix, limits=asdict(limits),
            reservation_is_filesystem_quota=False, native_resume_supported=False)))
        fsync_dir(self.root)
        fsync_dir(self.root.parent)
        self.check()

    def check(self, extra=0):
        require(shutil.disk_usage(self.root).free >= self.limits.floor + extra,
                'SSD continuous free floor')
        used = sum(p.stat().st_size for p in self.root.rglob('*')
                   if p.is_file() and p.name != 'reservation.bin')
        require(used + extra <= self.limits.payload, 'SSD payload and metadata cap')
        return used

    def metadata(self, name, data):
        require(name in ('header.bin', 'trailer.bin'), 'Exact stream metadata name')
        self.check(len(data))
        fresh_bytes(self.root / name, data)
        fsync_dir(self.root)

    def terminal(self, result, native_root=None):
        """Only called after native wait/reap, including a failed native result."""
        self.check()
        retained = {}
        if native_root is not None:
            native_root = Path(native_root)
            directory = self.root / 'native-terminal-capture'
            directory.mkdir()
            for source in sorted(native_root.rglob('*')):
                if not source.is_file():
                    continue
                require(not source.is_symlink(), 'Native capture has no symlink')
                relative = source.relative_to(native_root)
                expected = pin(source)
                self.check(expected['bytes'])
                destination = directory / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                fresh_bytes(destination, source.read_bytes())
                require(pin(destination) == expected == pin(source),
                        'Exact immutable terminal native capture')
                fsync_dir(destination.parent)
                retained[str(relative)] = expected
            for child in sorted((p for p in directory.rglob('*') if p.is_dir()),
                                key=lambda p: len(p.parts), reverse=True):
                fsync_dir(child)
            fsync_dir(directory)
        try:
            observed = inspect_spool(self.root, raw=True)
        except BaseException as error:
            invalid = dict(status='ERROR_LOCAL_MANIFEST_NATIVE_FILES_RETAINED',
                           result=result, native_capture=retained, error=repr(error),
                           public_verified=False, native_resume_supported=False,
                           reservation_retained=True)
            invalid_bytes = encoded(invalid)
            self.check(len(invalid_bytes))
            fresh_bytes(self.root / 'native-terminal-invalid.json', invalid_bytes)
            fsync_dir(self.root)
            raise
        terminal = dict(status='NATIVE_TERMINAL_LOCAL_RETAINED', result=result,
                        canonical_manifest=pin(self.root / 'parts.json'),
                        staging=observed['staging'], orphans=observed['committed_orphans'],
                        native_capture=retained,
                        public_verified=False, native_resume_supported=False)
        terminal_bytes = encoded(terminal)
        self.check(len(terminal_bytes))
        fresh_bytes(self.root / 'native-terminal.json', terminal_bytes)
        fsync_dir(self.root)
        (self.root / 'reservation.bin').unlink()
        fsync_dir(self.root)
        return terminal

    def close(self):
        self.lock.close()


class PartQueue:
    """Same raw framing/compression; each flush waits only for local durability."""
    def __init__(self, root, prefix, columns, spool, rows_per_part, reclaim, min_free_bytes):
        self.root, self.spool = Path(root), spool
        require(isinstance(spool, Spool) and prefix == spool.prefix,
                'Exact independently owned local spool')
        require(reclaim is True and min_free_bytes == 512 * 1024**2,
                'Retained capture resource contract')
        self.root.mkdir()
        self.columns, self.prefix, self.rows_per_part = list(columns), prefix, rows_per_part
        self.width = len(columns) * 8
        require(0 < rows_per_part * self.width <= RAW_PART_CAP, 'Bounded native part')
        self.pending, self.rows, self.parts = bytearray(), 0, []
        self.hash = hashlib.sha256()
        self.ledger = dict(schema='PCIE_LOCAL_LOSSLESS_SPOOL_V1', status='CAPTURING_LOCAL',
                           prefix=prefix, columns=self.columns, rows_per_part=rows_per_part,
                           no_decimation=True, parts=self.parts, committed_rows=0,
                           limits=asdict(spool.limits), public_verified=False)
        self._save()

    def _save(self):
        self.spool.check(2 * len(encoded(self.ledger)))
        atomic_json(self.spool.root / 'parts.json', self.ledger)
        atomic_json(self.root / 'parts.json', self.ledger)

    def append(self, sample):
        require(len(sample) == self.width, 'Complete native frame')
        self.hash.update(sample)
        self.pending.extend(sample)
        self.rows += 1
        if len(self.pending) == self.width * self.rows_per_part:
            self.flush()

    def flush(self):
        if not self.pending:
            return
        index = len(self.parts)
        require(index < self.spool.limits.parts, 'Finite part count cap')
        raw = bytes(self.pending)
        packed = lzma.compress(raw, preset=1)
        row = dict(index=index, first_row=self.rows - len(raw) // self.width,
                   rows=len(raw) // self.width, name=f'{self.prefix}-part{index:05d}.bin.xz',
                   uncompressed_bytes=len(raw), uncompressed_sha256=hashlib.sha256(raw).hexdigest(),
                   bytes=len(packed), sha256=hashlib.sha256(packed).hexdigest(),
                   status='LOCAL_DURABLE')
        self.spool.check(len(packed) + len(encoded(row)) + 2 * len(encoded(self.ledger)) + 8192)
        staging = self.spool.root / 'staging' / f'{index:05d}'
        committed = self.spool.root / 'committed' / f'{index:05d}'
        require(not committed.exists(), 'Never replace committed part')
        staging.mkdir()
        fresh_bytes(staging / row['name'], packed)
        fresh_bytes(staging / 'record.json', encoded(row))
        fsync_dir(staging)
        os.rename(staging, committed)
        fsync_dir(committed.parent)
        fsync_dir(staging.parent)
        self.parts.append(row)
        self.ledger['committed_rows'] += row['rows']
        self._save()
        self.pending.clear()

    def finish(self):
        self.flush()
        observed = inspect_spool(self.spool.root, raw=True)
        require(observed['rows'] == self.rows and not observed['staging']
                and not observed['committed_orphans'], 'Complete ordered local capture')
        require((self.spool.root / 'trailer.bin').read_bytes() == str(self.rows).encode(),
                'Exact completed native count trailer')
        self.ledger.update(status='LOCAL_CAPTURE_COMPLETE', rows=self.rows,
                           payload_sha256=self.hash.hexdigest(),
                           stream_metadata={name: pin(self.spool.root / name)
                                            for name in ('header.bin', 'trailer.bin')})
        self._save()
        inspect_spool(self.spool.root, raw=True)
        return self.ledger
