#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail before native launch unless the validated Python/NumPy runtime is selected.

Use hw/soc/tools/cocotb-venv/bin/python directly, without resolving its symlink.
This wrapper preserves the frozen producer and adds its own bytes to the producer
input inventory through the existing loaded-method census.
"""

import hashlib
from pathlib import Path
import sys

PRODUCER_SHA = "79de51fcd210e1141b187a3fc83546e9933b5d5c6c36a9d0bc85aa6a69d2da9d"


def check_runtime(version, numpy_version, has_trapezoid):
    if tuple(version[:2]) != (3, 12) or numpy_version != "2.5.3" or not has_trapezoid:
        raise RuntimeError(
            "Native loop metrology requires validated Python3.12/NumPy2.5.3 with trapezoid; use the un-resolved cocotb-venv Python executable"
        )


def main():
    import numpy

    check_runtime(
        sys.version_info, numpy.__version__, callable(getattr(numpy, "trapezoid", None))
    )
    source = Path(__file__).with_name("characterize_pcie_pll_loop_stream_v2.py")
    if hashlib.sha256(source.read_bytes()).hexdigest() != PRODUCER_SHA:
        raise RuntimeError("Frozen stream v2 producer changed")
    import characterize_pcie_pll_loop_stream_v2 as producer

    return producer.main()


if __name__ == "__main__":
    raise SystemExit(main())
