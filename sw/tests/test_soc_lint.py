# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""New, relocated or multiplied diagnostics must not inherit old allowances."""
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('soc_lint',ROOT/'scripts/check_soc_lint.py')
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)


def warning(code='LATCH', path='hw/soc/rtl/prim_clock_gating.v', signal='soc_top.g_clkgate.u_bus_cg.en_latch'):
    return f"%Warning-{code}: {ROOT/path}:40:3: Latch inferred for signal '{signal}' (not all control paths of combinational always assign a value)\n"


@pytest.mark.parametrize('mutation', ['new_signal','new_file','new_line','duplicate','removed'])
def test_diagnostic_ledger_rejects_changes(mutation):
    original = warning()
    changed = dict(new_signal=warning(signal='soc_top.accidental_latch'),
                   new_file=warning(path='hw/soc/rtl/soc_bus.v'),
                   new_line=original.replace(':40:3:',':41:3:'),duplicate=original*2,removed='')[mutation]
    expected = lint.diagnostics(original)
    assert not any(lint.compare(expected, expected).values())
    assert any(lint.compare(lint.diagnostics(changed),expected).values())


@pytest.mark.parametrize('line', ['%Warning: unknown format', '%Warning-NEW: unsupported summary'])
def test_unknown_diagnostic_format_fails(line):
    with pytest.raises(ValueError,match='Unparsed'): lint.diagnostics(line)


def test_outside_diagnostic_path_fails():
    with pytest.raises(ValueError): lint.diagnostics('%Warning-LATCH: /tmp/untrusted.v:1:2: warning')


def test_only_architectural_latch_is_eligible_for_exact_allowance():
    assert not lint.owned_policy(lint.diagnostics(warning()))
    assert lint.owned_policy(lint.diagnostics(warning(signal='soc_top.accidental_latch')))
    assert lint.owned_policy(lint.diagnostics(warning(path='hw/soc/rtl/soc_bus.v')))
    assert lint.owned_policy(lint.diagnostics(warning(code='IMPLICIT')))


def test_all_owned_modules_and_rom_template_restrict_implicit_nets():
    assert not lint.nettype_errors()


@pytest.mark.parametrize('text', [
    'module x; endmodule\n`default_nettype wire',
    '`default_nettype none\nmodule x; endmodule',
    '`default_nettype none\n`default_nettype wire\nmodule x; endmodule\n`default_nettype wire',
    '// `default_nettype none\nmodule x; endmodule\n`default_nettype wire',
])
def test_nettype_guard_rejects_missing_or_early_restore(tmp_path, text):
    rtl=tmp_path/'hw/soc/rtl';rtl.mkdir(parents=True)
    (rtl/'soc_logic_boot_rom.v.in').write_text('`default_nettype none\nmodule rom; endmodule\n`default_nettype wire')
    (rtl/'bad.v').write_text(text)
    assert lint.nettype_errors(tmp_path)==['hw/soc/rtl/bad.v']


def test_reviewed_policy_cannot_allow_new_owned_widths():
    p=json.loads(lint.POLICY.read_text())
    assert set(p['profiles'])=={'base','full'}
    for rows in p['profiles'].values():
        assert rows and not lint.owned_policy(rows)
        assert all(type(n) is int and n>0 for n in rows.values())


def test_explicit_lint_job_fails_when_toolchain_is_absent(tmp_path):
    import os
    proc=subprocess.run(['bash','scripts/ci_local.sh','lint'],cwd=ROOT,
                        env=dict(os.environ,OSS_CAD_SUITE=str(tmp_path/'missing')),
                        text=True,capture_output=True,timeout=30)
    assert proc.returncode!=0
    assert '1 failed, 0 skipped' in proc.stdout
