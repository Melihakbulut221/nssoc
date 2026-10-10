# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Macro interface elaboration commands preserve actual source contents."""
import importlib.util
from pathlib import Path
import sys

import pytest

FLOW = Path(__file__).resolve().parents[2]/'hw/soc/flow'
sys.path.insert(0, str(FLOW))
try:
    SPEC = importlib.util.spec_from_file_location('check_clones_cli', FLOW/'check_eco_logic_clones.py')
    CHECK = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(CHECK)
finally:
    sys.path.pop(0)


def test_opaque_macro_interfaces_loaded_after_actual_libraries(tmp_path):
    actual, macro = tmp_path/'actual.lib', tmp_path/'black box.v'
    assert CHECK.library_script([actual], [macro]).splitlines() == [
        f'read_liberty -lib "{actual}"', f'read_verilog -lib "{macro}"']
    assert CHECK.library_script([actual], []) == f'read_liberty -lib "{actual}"'


@pytest.mark.parametrize('control', ['\n', '\r', '\0'])
def test_yosys_command_path_injection_rejected(control):
    with pytest.raises(ValueError, match='control character'):
        CHECK.quote(Path('macro'+control+'read_verilog evil'))


def test_quotes_are_yosys_escaped():
    assert CHECK.quote('a"b\\c') == '"a\\"b\\\\c"'
