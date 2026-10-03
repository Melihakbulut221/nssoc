#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fetch locked, untouched IHP models and mapping Liberty for native boot.

This is a functional verification subset, not an installed physical PDK.
"""
import argparse
import json
from pathlib import Path

from prepare_ihp_drc import SOC, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=SOC / 'tools/ihp-native-boot-c4b8b4e')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((SOC / 'tools').resolve()):
        parser.error("Output must stay inside this project's hw/soc/tools")
    lock = json.loads((SOC / 'pnr/ihp-native-boot.lock.json').read_text())
    prepare(lock, args.output)
    print(f"Verified {len(lock['files'])} native boot inputs at {lock['commit']}")
    print(args.output.resolve() / 'ihp-sg13g2')


if __name__ == '__main__':
    main()
