# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fail-closed mapping inventory controls for the additive native launcher."""

import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "receive_native", ROOT / "scripts/check_pcie_gen3_receive_native.py"
)
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


@pytest.mark.parametrize("cell_type", ["$dff", "$memrd", "unknown", "sg13g2_fake_1"])
def test_unmapped_or_unrecognized_cell_rejected(cell_type):
    document = {"modules": {native.TOP: {"cells": {"u0": {"type": cell_type}}}}}
    with pytest.raises(ValueError, match="unknown IHP cell"):
        native.mapped_cell_count(document, 'cell ("sg13g2_buf_1") {}')


def test_empty_mapping_rejected():
    with pytest.raises(ValueError):
        native.mapped_cell_count({"modules": {native.TOP: {"cells": {}}}}, "")


def test_real_named_library_members_accepted():
    document = {
        "modules": {
            native.TOP: {
                "cells": {
                    "u0": {"type": "sg13g2_buf_1"},
                    "u1": {"type": "sg13g2_dfrbp_1"},
                }
            }
        }
    }
    assert (
        native.mapped_cell_count(
            document, 'cell ("sg13g2_buf_1") {} cell (sg13g2_dfrbp_1) {}'
        )
        == 2
    )
