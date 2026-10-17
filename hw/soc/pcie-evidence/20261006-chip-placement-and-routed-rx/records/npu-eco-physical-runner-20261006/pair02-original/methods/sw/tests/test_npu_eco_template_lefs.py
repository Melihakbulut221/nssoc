# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Keep the exact full DEF and strict pin contract while supplying missing LEFs."""
import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('template_lefs', ROOT / 'hw/soc/pnr/npu_eco_template_lefs.py')
method = importlib.util.module_from_spec(spec)
spec.loader.exec_module(method)


def fixture():
    return (['openroad', '-python', '/runtime/apply_def_template.py', '--input-lef', '/tech.lef',
             '--input-lef', '/stdcell.lef', '--def-template', '/original-full.def', '--strict'],
            {name: ['/source/' + name + '.lef'] for name in ('SP6TSRAM512x64', 'DP8TSRAMDP256x16')})


def test_only_two_source_macro_lef_arguments_are_added():
    command, macros = fixture()
    original = copy.deepcopy((command, macros))
    result = method.append_template_macro_lefs(command, macros)
    assert (command, macros) == original
    assert result == command + ['--input-lef', '/source/DP8TSRAMDP256x16.lef',
                                '--input-lef', '/source/SP6TSRAM512x64.lef']


@pytest.mark.parametrize('fault', ['permissive', 'power', 'missing_strict', 'missing_template',
                                  'missing_macro', 'foreign_macro', 'no_lef', 'two_lefs',
                                  'wrong_master', 'already_present'])
def test_changed_template_or_incomplete_macro_library_rejected(fault):
    command, macros = fixture()
    if fault == 'permissive':
        command.append('--permissive')
    elif fault == 'power':
        command.append('--copy-def-power')
    elif fault == 'missing_strict':
        command.remove('--strict')
    elif fault == 'missing_template':
        command.remove('--def-template')
    elif fault == 'missing_macro':
        macros.pop('SP6TSRAM512x64')
    elif fault == 'foreign_macro':
        macros['foreign'] = ['/source/foreign.lef']
    elif fault == 'no_lef':
        macros['SP6TSRAM512x64'] = []
    elif fault == 'two_lefs':
        macros['SP6TSRAM512x64'] *= 2
    elif fault == 'wrong_master':
        macros['SP6TSRAM512x64'] = ['/source/DP8TSRAMDP256x16.lef']
    else:
        command.extend(['--input-lef', macros['SP6TSRAM512x64'][0]])
    with pytest.raises(ValueError):
        method.append_template_macro_lefs(command, macros)
