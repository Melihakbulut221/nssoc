# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Count completed cocotb cases; missing, empty and malformed XML are errors."""

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def count_results(paths):
    passed = failed = skipped = 0
    if not paths:
        raise ValueError("no result files")
    for path in paths:
        root = ET.parse(path).getroot()
        if root.tag not in ("testsuites", "testsuite"):
            raise ValueError(f"{path}: not a JUnit result")
        cases = list(root.iter("testcase"))
        if not cases:
            raise ValueError(f"{path}: no test cases (collection may have failed)")
        for case in cases:
            if case.find("failure") is not None or case.find("error") is not None:
                failed += 1
            elif case.find("skipped") is not None:
                skipped += 1
            else:
                passed += 1
    return passed, failed, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        counts = count_results(args.paths)
    except (OSError, ValueError, ET.ParseError) as exc:
        parser.exit(1, f"invalid cocotb results: {exc}\n")
    print(*counts)


if __name__ == "__main__":
    main()
