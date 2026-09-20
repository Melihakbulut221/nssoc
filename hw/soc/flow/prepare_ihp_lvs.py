#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fetch the pinned, unmodified IHP LVS deck; does not assert LVS success."""
import argparse
import json
from pathlib import Path

from prepare_ihp_drc import SOC, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=SOC / 'tools/ihp-lvs-5e6d592')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((SOC / 'tools').resolve()):
        parser.error("Output must stay inside this project's hw/soc/tools")
    lock = json.loads((SOC / 'pnr/ihp-lvs.lock.json').read_text())
    entrypoint = prepare(lock, args.output)
    print(f"Verified {len(lock['files'])} files at {lock['commit']}")
    print(entrypoint)


if __name__ == '__main__':
    main()
