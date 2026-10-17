#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind a LibreLane/OpenROAD timing log to the requested immutable ODB/SDC.

Checking a generated Tcl variable is insufficient: read_current_odb reads
CURRENT_ODB, whereas read_current_sdc reads _SDC_IN. Require actual load messages
and the recorded file digests before using a timing result.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def validate(log, odb, sdc, pins):
    observations = {}
    for kind, expected, pattern in (
        ('odb', odb, r"Reading OpenROAD database at '([^']+)'"),
        ('sdc', sdc, r"Reading design constraints file at '([^']+)'"),
    ):
        paths = re.findall(pattern, log)
        if len(paths) != 1 or Path(paths[0]).resolve() != Path(expected).resolve():
            raise ValueError(f'{kind}: expected one load of {expected}, observed {paths}')
        path = Path(expected)
        if str(path) not in pins:
            raise ValueError(f'{kind}: requested file is absent from the input manifest')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        pin = pins[str(path)]
        wanted = pin if isinstance(pin, str) else pin['sha256']
        if digest != wanted:
            raise ValueError(f'{kind}: input digest changed')
        observations[kind] = {'path': str(path.resolve()), 'sha256': digest}
    return {'status': 'PASS_LOADED_ODB_SDC_AND_INPUT_DIGESTS', 'observations': observations,
            'timing_accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('log', 'odb', 'sdc', 'record'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args()
    result = validate(args.log.read_text(), args.odb, args.sdc,
                      json.loads(args.record.read_text())['inputs'])
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
