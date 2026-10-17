# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Reject invalid metrology runtime before importing/launching native producer."""

from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import run_pcie_pll_loop_stream_v2 as run


def test_validated_runtime_contract():
    run.check_runtime((3, 12, 3), "2.5.3", True)


@pytest.mark.parametrize(
    "version,numpy,api",
    [
        ((3, 12, 3), "1.26.4", False),
        ((3, 12, 3), "2.5.3", False),
        ((3, 14, 0), "2.5.3", True),
        ((3, 12, 3), "2.5.4", True),
    ],
)
def test_incompatible_runtime_is_an_error(version, numpy, api):
    with pytest.raises(RuntimeError, match="requires validated"):
        run.check_runtime(version, numpy, api)
