# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Give the template's separate DEF reader the two exact SRAM abstractions."""
from pathlib import Path


def append_template_macro_lefs(command, macros):
    if ('--def-template' not in command or '--strict' not in command
            or '--permissive' in command or '--copy-def-power' in command):
        raise ValueError('Unchanged strict signal-only DEF template command required')
    if set(macros) != {'SP6TSRAM512x64', 'DP8TSRAMDP256x16'}:
        raise ValueError('Exact two SRAM master abstractions required')
    result = list(command)
    for master in sorted(macros):
        lefs = macros[master]
        if len(lefs) != 1 or Path(str(lefs[0])).name != master + '.lef':
            raise ValueError('One source-bound LEF per SRAM master required')
        path = str(lefs[0])
        if path in command:
            raise ValueError('Unexpected existing macro LEF in frozen template reader')
        result.extend(['--input-lef', path])
    return result
