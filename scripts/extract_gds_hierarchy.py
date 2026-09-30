#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Extract a GDSII root closure without reserializing any geometry or metadata.

Two bounded-memory passes over one regular source FD: index complete records,
then copy selected byte spans while rehashing the ENTIRE source. Selected cells
stay in source order, including original timestamps, properties and references.
The unchanged library prefix and ENDLIB are retained. Output is re-indexed and
checked against the original cell hashes before a success receipt is published.

Conservative supported profile: HEADER/BGNLIB/LIBNAME/UNITS library prefix;
BOUNDARY, PATH, SREF, AREF, TEXT and BOX elements, with ordinary properties.
Unknown records, records between cells, trailing padding, non-ASCII cell names,
external/missing references, duplicate cells and cycles are rejected, including
in unselected cells. This is byte-preservation evidence, not LVS/signoff.

Record encodings checked against KLayout v0.30.4 (commit
8b0a8c73175f6d84f841e88914d1a8819201e045), dbGDS2.h, dbGDS2Reader.cc and
GDS2ReaderBase::read_ref in dbGDS2ReaderBase.cc:
https://github.com/KLayout/klayout/tree/8b0a8c73175f6d84f841e88914d1a8819201e045/src/plugins/streamers/gds2/db_plugin
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import struct


class GDSFormatError(ValueError):
    """The input is malformed or outside the explicitly supported profile."""


# record type -> (GDS data type, fixed payload bytes or None).
RECORDS = {
    0x00: (2, 2), 0x01: (2, 24), 0x02: (6, None), 0x03: (5, 16),
    0x04: (0, 0), 0x05: (2, 24), 0x06: (6, None), 0x07: (0, 0),
    0x08: (0, 0), 0x09: (0, 0), 0x0A: (0, 0), 0x0B: (0, 0),
    0x0C: (0, 0), 0x0D: (2, 2), 0x0E: (2, 2), 0x0F: (3, 4),
    0x10: (3, None), 0x11: (0, 0), 0x12: (6, None), 0x13: (2, 4),
    0x16: (2, 2), 0x17: (1, 2), 0x19: (6, None), 0x1A: (1, 2),
    0x1B: (5, 8), 0x1C: (5, 8), 0x21: (2, 2), 0x26: (1, 2),
    0x2B: (2, 2), 0x2C: (6, None), 0x2D: (0, 0), 0x2E: (2, 2),
    0x2F: (3, 4), 0x30: (3, 4), 0x31: (3, 4), 0x34: (1, 2),
}
# These ordered sequences intentionally reject unsupported legacy extensions.
ELEMENT_FIELDS = {
    0x08: [0x0D, 0x0E, 0x10],
    0x09: [0x0D, 0x0E, 0x21, 0x0F, 0x30, 0x31, 0x10],
    0x0A: [0x12, 0x1A, 0x1B, 0x1C, 0x10],
    0x0B: [0x12, 0x1A, 0x1B, 0x1C, 0x13, 0x10],
    0x0C: [0x0D, 0x16, 0x17, 0x21, 0x0F, 0x1A, 0x1B, 0x1C, 0x10, 0x19],
    0x2D: [0x0D, 0x2E, 0x10],
}
REQUIRED_FIELDS = {
    0x08: {0x0D, 0x0E, 0x10}, 0x09: {0x0D, 0x0E, 0x10},
    0x0A: {0x12, 0x10}, 0x0B: {0x12, 0x13, 0x10},
    0x0C: {0x0D, 0x16, 0x10, 0x19}, 0x2D: {0x0D, 0x2E, 0x10},
}
COPY_BYTES = 1024 * 1024
MAX_CELLS = 10000
MAX_REFERENCES = 100000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def ascii_name(data):
    value = data[:-1] if data.endswith(b'\0') else data
    if not value or len(value) > 256 or any(c < 33 or c > 126 for c in value):
        raise GDSFormatError('Unsupported empty/oversized/non-ASCII/non-printable GDS name')
    return value.decode('ascii')


def real8(data):
    """GDS base-16 float; decoding validates UNITS, never changes output bytes."""
    mantissa = int.from_bytes(data[1:], 'big')
    value = mantissa * 16.0 ** ((data[0] & 127) - 64) / 2**56
    return -value if data[0] & 128 else value


def records(stream):
    offset = 0
    while True:
        header = stream.read(4)
        if not header:
            return
        if len(header) != 4:
            raise GDSFormatError(f'Truncated record header at {offset}')
        length, kind, dtype = struct.unpack('>HBB', header)
        if length < 4 or length % 2:
            raise GDSFormatError(f'Invalid record length {length} at {offset}')
        payload = stream.read(length - 4)
        if len(payload) != length - 4:
            raise GDSFormatError(f'Truncated record payload at {offset}')
        if kind not in RECORDS:
            raise GDSFormatError(f'Unsupported record 0x{kind:02x} at {offset}')
        expected_type, fixed_length = RECORDS[kind]
        if dtype != expected_type or (fixed_length is not None and len(payload) != fixed_length):
            raise GDSFormatError(f'Invalid data type/payload size at {offset}')
        if kind == 0x10 and (not payload or len(payload) % 8):
            raise GDSFormatError(f'XY must contain complete coordinate pairs at {offset}')
        yield offset, kind, payload, header + payload
        offset += length


def validate_element(kind, fields):
    if not REQUIRED_FIELDS[kind] <= fields.keys():
        raise GDSFormatError('Element lacks required records')
    xy = fields[0x10]
    points = len(xy) // 8
    if kind in (0x0A, 0x0C) and points != 1:
        raise GDSFormatError('SREF/TEXT requires one XY point')
    if kind == 0x0B:
        if points != 3 or any(n < 1 for n in struct.unpack('>hh', fields[0x13])):
            raise GDSFormatError('AREF requires three XY points and positive COLROW')
    if kind in (0x08, 0x2D):
        if points < 4 or (kind == 0x2D and points != 5) or xy[:8] != xy[-8:]:
            raise GDSFormatError('BOUNDARY/BOX must be closed with valid XY count')
    if kind == 0x09 and points < 2:
        raise GDSFormatError('PATH requires at least two XY points')
    return ascii_name(fields[0x12]) if kind in (0x0A, 0x0B) else None


def closure(cells, roots):
    """Iterative traversal rejects missing cells and cycles without recursion limits."""
    selected, active = set(), set()
    for root in roots:
        pending = [(root, False)]
        while pending:
            name, finish = pending.pop()
            if finish:
                active.remove(name)
                selected.add(name)
                continue
            if name in active:
                raise GDSFormatError(f'Cyclic hierarchy at {name}')
            if name in selected:
                continue
            if name not in cells:
                raise GDSFormatError(f'Missing referenced/root cell: {name}')
            active.add(name)
            pending.append((name, True))
            pending.extend((child, False) for child in cells[name]['references'])
    return selected


def index_stream(stream):
    """Index names, references, original byte spans and hashes; no geometry tree."""
    stream.seek(0)
    total_hash, header_hash = hashlib.sha256(), hashlib.sha256()
    cells, units, current, element = {}, None, None, None
    header_pos, header_end, endlib, size, reference_count = 0, None, None, 0, 0
    fields, order, pending_property = {}, -1, False
    header_types = [0x00, 0x01, 0x02, 0x03]
    for offset, kind, payload, raw in records(stream):
        if endlib is not None:
            raise GDSFormatError('Trailing data/padding after ENDLIB is unsupported')
        total_hash.update(raw)
        size = offset + len(raw)
        if header_pos < len(header_types):
            if kind != header_types[header_pos]:
                raise GDSFormatError('Expected HEADER/BGNLIB/LIBNAME/UNITS library prefix')
            header_hash.update(raw)
            if kind == 0x02:
                ascii_name(payload)
            if kind == 0x03:
                if real8(payload[:8]) <= 0 or real8(payload[8:]) <= 0:
                    raise GDSFormatError('UNITS must contain positive GDS real8 values')
                units = raw.hex()
            header_pos += 1
            header_end = size
            continue
        if current is None:
            if kind == 0x04:
                endlib = dict(start=offset, end=size, bytes=len(raw), sha256=digest(raw))
            elif kind == 0x05:
                if len(cells) >= MAX_CELLS:
                    raise GDSFormatError('Cell index memory bound exceeded')
                current = dict(start=offset, name=None, references=set(), hash=hashlib.sha256())
                current['hash'].update(raw)
            else:
                raise GDSFormatError('Unsupported record between cells or before ENDLIB')
            continue
        current['hash'].update(raw)
        if current['name'] is None:
            if kind != 0x06:
                raise GDSFormatError('STRNAME must immediately follow BGNSTR')
            current['name'] = ascii_name(payload)
            if current['name'] in cells:
                raise GDSFormatError(f'Duplicate cell: {current["name"]}')
            continue
        if element is None:
            if kind == 0x07:
                name = current['name']
                cells[name] = dict(start=current['start'], end=size, bytes=size-current['start'],
                                   sha256=current['hash'].hexdigest(), references=sorted(current['references']))
                current = None
            elif kind in ELEMENT_FIELDS:
                element, fields, order, pending_property = kind, {}, -1, False
            else:
                raise GDSFormatError(f'Unsupported record 0x{kind:02x} in structure')
            continue
        if kind == 0x11:
            if pending_property:
                raise GDSFormatError('PROPATTR lacks PROPVALUE')
            reference = validate_element(element, fields)
            if reference is not None:
                current['references'].add(reference)
                reference_count += 1
                if reference_count > MAX_REFERENCES:
                    raise GDSFormatError('Reference index memory bound exceeded')
            element = None
        elif kind == 0x2B:
            if pending_property or not REQUIRED_FIELDS[element] <= fields.keys():
                raise GDSFormatError('Invalid PROPATTR position/pair')
            pending_property, order = True, 999
        elif kind == 0x2C:
            if not pending_property:
                raise GDSFormatError('PROPVALUE lacks PROPATTR')
            pending_property = False
        else:
            allowed = [0x26, 0x2F] + ELEMENT_FIELDS[element]
            if pending_property or kind not in allowed or kind in fields or allowed.index(kind) <= order:
                raise GDSFormatError('Unexpected, duplicate or out-of-order element record')
            order = allowed.index(kind)
            fields[kind] = payload
    if endlib is None or current is not None or element is not None or header_pos != 4:
        raise GDSFormatError('Incomplete GDS library/structure/element')
    # Validate the whole library, even references hidden in excluded structures.
    closure(cells, cells)
    return dict(bytes=size, sha256=total_hash.hexdigest(), cells=cells,
                header=dict(start=0, end=header_end, bytes=header_end, sha256=header_hash.hexdigest()),
                endlib=endlib, units_record_hex=units)


def safe_path(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f'Symlink path component rejected: {part}')
    return path


def fingerprint(stream):
    value = os.fstat(stream.fileno())
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def copy_spans(stream, output, spans):
    """Second source pass hashes skipped bytes too; source changes fail closed."""
    stream.seek(0)
    source_hash, output_hash = hashlib.sha256(), hashlib.sha256()
    position, which = 0, 0
    while chunk := stream.read(COPY_BYTES):
        source_hash.update(chunk)
        end = position + len(chunk)
        while which < len(spans) and spans[which]['start'] < end:
            span = spans[which]
            left, right = max(position, span['start']), min(end, span['end'])
            if right > left:
                part = chunk[left-position:right-position]
                output.write(part)
                output_hash.update(part)
            if span['end'] > end:
                break
            which += 1
        position = end
    if which != len(spans):
        raise ValueError('Source was truncated during copying')
    return source_hash.hexdigest(), output_hash.hexdigest(), position


def extract(source, roots, output_dir, source_sha256=None):
    source, output_dir = safe_path(source), safe_path(output_dir)
    roots = list(dict.fromkeys(roots))
    if not roots:
        raise ValueError('At least one root is required')
    if os.path.lexists(output_dir):
        raise FileExistsError(f'Output must be a fresh directory: {output_dir}')
    # Ancestors must already exist. This avoids surprising directory creation.
    if not output_dir.parent.is_dir():
        raise ValueError('Output parent directory must already exist')
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(source, flags), 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('Source must be a regular file')
        before = fingerprint(stream)
        original = index_stream(stream)
        if fingerprint(stream) != before:
            raise ValueError('Source changed during indexing')
        if source_sha256 is not None and original['sha256'] != source_sha256:
            raise ValueError('Source SHA256 does not match expected pin')
        selected = closure(original['cells'], roots)
        names = [name for name in original['cells'] if name in selected]
        spans = [original['header']] + [original['cells'][n] for n in names] + [original['endlib']]
        output_dir.mkdir(mode=0o700)
        output = output_dir / 'subset.gds'
        receipt_path = output_dir / 'receipt.json'
        try:
            with output.open('xb') as target:
                source_hash, output_hash, copied_source_bytes = copy_spans(stream, target, spans)
                target.flush()
                os.fsync(target.fileno())
            if source_hash != original['sha256'] or copied_source_bytes != original['bytes'] or fingerprint(stream) != before:
                raise ValueError('Source changed between/during passes')
            with output.open('rb') as target:
                result = index_stream(target)
            if result['sha256'] != output_hash or set(result['cells']) != selected:
                raise ValueError('Output hash/hierarchy does not match selected closure')
            for name in names:
                for field in ('bytes', 'sha256', 'references'):
                    if original['cells'][name][field] != result['cells'][name][field]:
                        raise ValueError(f'Output cell changed: {name}')
            if result['header'] != original['header'] or result['units_record_hex'] != original['units_record_hex'] or result['endlib']['sha256'] != original['endlib']['sha256']:
                raise ValueError('Output library header/units/footer changed')
            receipt = dict(schema=1, status='BYTE_PRESERVED_HIERARCHY_SUBSET',
                created=datetime.now(timezone.utc).isoformat(), roots=roots,
                source=dict(path=str(source), bytes=original['bytes'], sha256=original['sha256'], cell_count=len(original['cells'])),
                output=dict(path=str(output), bytes=result['bytes'], sha256=result['sha256'], cell_count=len(names)),
                library_header=original['header'], units_record_hex=original['units_record_hex'],
                endlib_sha256=original['endlib']['sha256'],
                cells={n: dict(source=original['cells'][n], output=result['cells'][n]) for n in names},
                excluded_cells=[n for n in original['cells'] if n not in selected],
                geometry_records_modified=False, missing_references=False, cycles=False,
                all_source_bytes_rehashed_in_second_pass=True, lvs_accepted=False, manufacturing_approval=False,
                script_sha256=digest(Path(__file__).read_bytes()))
            with receipt_path.open('x', encoding='utf-8') as target:
                json.dump(receipt, target, indent=2)
                target.write('\n')
            return receipt
        except BaseException:
            # Only these fresh files were created by this invocation.
            receipt_path.unlink(missing_ok=True)
            output.unlink(missing_ok=True)
            output_dir.rmdir()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--source-sha256')
    parser.add_argument('--root', required=True, action='append', dest='roots')
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    receipt = extract(args.source, args.roots, args.output_dir, args.source_sha256)
    print(json.dumps(receipt['output'], indent=2))


if __name__ == '__main__':
    main()
