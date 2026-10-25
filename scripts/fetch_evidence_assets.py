#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fetch immutable-name release evidence and verify every byte before use."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'https://github.com/Melihakbulut221/nssoc/releases/download/'


def validate(record):
    tag = record['release_tag']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', tag):
        raise ValueError('Invalid release tag')
    rows = record['assets']
    if not rows or len({r['name'] for r in rows}) != len(rows):
        raise ValueError('Missing or duplicate asset inventory')
    for row in rows:
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]+', row['name']) or
                row['url'] != PREFIX+tag+'/'+row['name'] or
                not re.fullmatch(r'[a-f0-9]{64}', row['sha256']) or
                type(row['bytes']) is not int or not 0 < row['bytes'] <= 2*1024**3):
            raise ValueError('Invalid asset identity, size or repository URL')
    return rows


def verify(path, row):
    if path.stat().st_size != row['bytes']:
        raise ValueError('Wrong asset size: '+row['name'])
    with path.open('rb') as source:
        if hashlib.file_digest(source, 'sha256').hexdigest() != row['sha256']:
            raise ValueError('Wrong asset digest: '+row['name'])


def fetch(row, directory, verify_only=False):
    destination = directory/row['name']
    if destination.exists() or verify_only:
        verify(destination, row)
        return
    # Never extract archives or overwrite an existing/failed download.
    partial = directory/(row['name']+'.partial')
    size = 0
    with partial.open('xb') as output, urlopen(row['url'], timeout=120) as source:
        for chunk in iter(lambda: source.read(1024*1024), b''):
            size += len(chunk)
            if size > row['bytes']:
                raise ValueError('Download exceeded declared size')
            output.write(chunk)
    verify(partial, row)
    partial.rename(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    directory = args.out.resolve()
    if not directory.is_relative_to(ROOT/'hw/soc/out'):
        parser.error('Keep the evidence cache below hw/soc/out')
    rows = validate(json.loads(args.manifest.read_text()))
    if not args.verify_only:
        directory.mkdir(parents=True, exist_ok=True)
    for row in rows:
        fetch(row, directory, args.verify_only)
        print('VERIFIED', row['name'])


if __name__ == '__main__':
    main()
