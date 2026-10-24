# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Explicit schematic headroom hypothesis on the verified assembled source.

The unchanged metal belongs to the old device geometry. Every result is a
sensitivity experiment, never an extracted-layout or full-PHY acceptance.
"""
import hashlib
import re


def resize_final(text, profile):
    assert profile == 'data8_select10'
    targets = {f'xd{i:04d}': (6, 10) for i in range(1, 5)}
    targets.update({f'xd{i:04d}': (3, 8) for i in range(43, 55)})
    found = {}
    output = []
    for line in text.splitlines(keepends=True):
        parts = line.split()
        name = parts[0].lower() if parts else ''
        if name not in targets:
            output.append(line)
            continue
        assert name not in found, 'Duplicate final device'
        assert len(parts) >= 9 and parts[5].lower() == 'npn13g2', 'Wrong final device model/arity'
        old, new = targets[name]
        matches = list(re.finditer(r'(?i)(?<!\S)nx=(\d+)(?!\S)', line))
        assert len(matches) == 1 and int(matches[0].group(1)) == old, 'Wrong original final device size'
        hit = matches[0]
        changed = line[:hit.start(1)] + str(new) + line[hit.end(1):]
        found[name] = {'original_nx': old, 'candidate_nx': new, 'nodes': parts[1:5]}
        output.append(changed)
    assert set(found) == set(targets), 'Missing final device'
    result = ''.join(output)
    return result, {'profile': profile, 'changed_devices': found,
        'source_sha256': hashlib.sha256(text.encode()).hexdigest(),
        'candidate_sha256': hashlib.sha256(result.encode()).hexdigest(),
        'physical_device_geometry_matches': False, 'qualified_pex': False,
        'scope': 'Exactly twelve final data Nx3->8 and four selectors Nx6->10; reference/tails, all other devices, metal R/C and connectivity unchanged. Old physical metal is a sensitivity control, not matching candidate extraction. New layout/LVS/RC and every original corner remain required.'}
