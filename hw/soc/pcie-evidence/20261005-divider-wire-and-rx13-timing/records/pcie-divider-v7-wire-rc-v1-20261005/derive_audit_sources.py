# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Full byte bridges from the frozen VCO wire-RC checker; no native execution."""
from pathlib import Path
import difflib
import hashlib
import json

B = Path(__file__).resolve().parent
P = B.parent / 'pcie-vco-v6-local-v1-wire-20261005'


def pin(p):
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


bridges = []
for name, replacements in [
    ('audit_wire_rc.py', [
        ("B=Path(__file__).resolve().parent", "B=Path(__file__).resolve().parent\nGEOMETRY=B.parent/'pcie-divider-v7-wire-v5-20261005'"),
        ("parent=B/'terminal-reference-planes.json'", "parent=GEOMETRY/'terminal-reference-planes.json'"),
        ('==20', '==37'), ('range(1,21)', 'range(1,38)'),
        ('==151', '==205'), ('==145', '==198'), ('==56', '==85'),
        ("==['21']", "==['38']"), ("==['20']", "==['37']"),
        ('original_devices=62,public_ports=6,physical_wire_components=20,geometry_probes=151,metal_device_terminals=145',
         'original_devices=91,public_ports=7,physical_wire_components=37,geometry_probes=205,metal_device_terminals=198'),
        ('unmodeled_body_well_terminals=56', 'unmodeled_body_well_terminals=85'),
        ('connected_wire_components=20', 'connected_wire_components=37'),
        ('collapsed_matrix_entries=21**2', 'collapsed_matrix_entries=38**2'),
    ]),
    ('check_native_mutations.py', [
        ("P=Path('/dev/shm/nssoc-vco-v4-mim-v6-local-v1-wire-rc-01')", "P=Path('/dev/shm/nssoc-div4-v7-wire-rc-01')"),
        ("a=json.loads((B/'anchors.json').read_text())", "a=json.loads((m.GEOMETRY/'anchors.json').read_text())"),
        ("B/'anchors.json',", "m.GEOMETRY/'anchors.json',"),
    ]),
]:
    old = (P / name).read_text()
    new = old
    operations = []
    for source, target in replacements:
        count = new.count(source)
        assert count, (name, source)
        new = new.replace(source, target)
        operations.append(dict(old=source, new=target, count=count))
    inverse = new
    for op in reversed(operations):
        inverse = inverse.replace(op['new'], op['old'])
    assert inverse == old, name
    if name == 'audit_wire_rc.py':
        assert new.count('==205') == 3 and '375' not in new
        assert new.count('==37') == 6
        assert 'original_devices=91,public_ports=7,physical_wire_components=37,geometry_probes=205,metal_device_terminals=198' in new
    compile(new, str(B / name), 'exec')
    (B / name).write_text(new)
    bridges.append(dict(parent=str(P / name), parent_pin=pin(P / name),
                        new=str(B / name), new_pin=pin(B / name),
                        operations=operations, whole_byte_inverse=True,
                        diff=''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True)))))
(B / 'audit-source-bridges.json').write_text(json.dumps(dict(
    status='PASS_FULL_BYTE_AUDIT_DERIVATION_ONLY', methods=bridges,
    native_executed=False, all_original_graph_capacitance_and_attachment_rules_unchanged=True,
    method=pin(Path(__file__))), indent=2) + '\n')
print('PASS two exact full byte bridges; native pending')
