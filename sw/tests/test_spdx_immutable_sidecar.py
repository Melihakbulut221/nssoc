# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# REUSE-IgnoreStart
"""REUSE sidecars must preserve captured bytes and still reject wrong licences."""
from pathlib import Path
import importlib.util
import sys

import pytest

PATH = Path(__file__).resolve().parents[2] / 'scripts/spdx_check.py'
SPEC = importlib.util.spec_from_file_location('sidecar_spdx', PATH)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


@pytest.mark.parametrize('apply', [False, True])
def test_valid_sidecar_never_rewrites_frozen_bytes(tmp_path, monkeypatch, apply):
    source = tmp_path / 'capture.spice'
    original = b'.subckt captured a b\nR1 a b 1\n.ends\n'
    source.write_bytes(original)
    Path(str(source) + '.license').write_text(
        'SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut\n'
        'SPDX-License-Identifier: CERN-OHL-W-2.0\n'
    )
    monkeypatch.setattr(M, 'ROOT', tmp_path)
    monkeypatch.setattr(M, 'tracked', lambda: ['capture.spice'])
    monkeypatch.setattr(sys, 'argv', ['spdx_check.py', *(['--apply'] if apply else [])])
    assert M.main() == 0
    assert source.read_bytes() == original


@pytest.mark.parametrize('sidecar', [
    '',
    'SPDX-License-Identifier: CERN-OHL-W-2.0\n',
    'SPDX-FileCopyrightText:\nSPDX-License-Identifier: CERN-OHL-W-2.0\n',
    'SPDX-FileCopyrightText: Owner\nprose SPDX-License-Identifier: CERN-OHL-W-2.0\n',
    'SPDX-FileCopyrightText: Owner\nSPDX-License-Identifier: CERN-OHL-W-2.0 junk\n',
    'SPDX-FileCopyrightText: Owner\nSPDX-License-Identifier: CERN-OHL-W-2.0\nSPDX-License-Identifier: Apache-2.0\n',
])
def test_missing_or_ambiguous_sidecar_is_not_a_valid_header(tmp_path, sidecar):
    source = tmp_path / 'capture.v'
    source.write_text('module capture; endmodule\n')
    Path(str(source) + '.license').write_text(sidecar)
    assert M.read_sidecar_tag(source) is None


@pytest.mark.parametrize('inline,sidecar', [
    ('', 'Apache-2.0'),
    ('// SPDX-License-Identifier: Apache-2.0\n', 'CERN-OHL-W-2.0'),
])
def test_wrong_license_or_conflicting_inline_still_fails(tmp_path, monkeypatch, inline, sidecar):
    source = tmp_path / 'capture.v'
    source.write_text(inline + 'module capture; endmodule\n')
    Path(str(source) + '.license').write_text(
        f'SPDX-FileCopyrightText: Owner\nSPDX-License-Identifier: {sidecar}\n'
    )
    monkeypatch.setattr(M, 'ROOT', tmp_path)
    monkeypatch.setattr(M, 'tracked', lambda: ['capture.v'])
    monkeypatch.setattr(sys, 'argv', ['spdx_check.py'])
    assert M.main() == 1
# REUSE-IgnoreEnd
