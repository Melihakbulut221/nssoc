#!/usr/bin/env python3
"""Exercise extracted-STA guards in Tcl; not a physical timing proof."""
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'hw/soc/pnr'))
from core_only_routed_guards import CLOCK_GUARD, guarded_sta

def main():
    derate = (ROOT / 'hw/soc/flow/check_timing_derate.tcl').read_text()
    fixture = ('source $::env(SCRIPTS_DIR)/openroad/common/io.tcl\n'
               '    read_timing_info\nread_spefs\n'
               '    if { [get_property $clock is_propagated] } {\n'
               '        set is_virtual "yes"\n    }\n')
    adapted = guarded_sta(fixture, derate)
    assert 'namespace exists ::ord' in adapted
    assert adapted.index('read_spefs\n') < adapted.index(CLOCK_GUARD)
    assert 'set_propagated_clock' not in adapted and 'unset_propagated_clock' not in adapted
    rejected = 0
    for anchor in ('source $::env(SCRIPTS_DIR)/openroad/common/io.tcl\n',
                   'read_spefs\n', '    read_timing_info\n',
                   '    if { [get_property $clock is_propagated] } {\n        set is_virtual "yes"\n    }'):
        for broken in (fixture.replace(anchor, ''), fixture + anchor):
            try:
                guarded_sta(broken, derate)
            except ValueError:
                rejected += 1
            else:
                raise AssertionError('Malformed native script accepted')
    cases = []
    for label, clocks, name, period, propagated, percent, engine, good in [
        ('valid', 'clk_i', 'clk_i', '20', '1', '5.0', False, True),
        ('ideal', 'clk_i', 'clk_i', '20', '0', '5.0', False, False),
        ('budget', 'clk_i', 'clk_i', '21', '1', '5.0', False, False),
        ('extra_clock', 'clk_i extra', 'clk_i', '20', '1', '5.0', False, False),
        ('missing_clock', '', '', '20', '1', '5.0', False, False),
        ('wrong_clock', 'other', '', '20', '1', '5.0', False, False),
        ('wrong_derate', 'clk_i', 'clk_i', '20', '1', '4.0', False, False),
        ('integer_derate', 'clk_i', 'clk_i', '20', '1', '5', False, False),
        ('invalid_derate', 'clk_i', 'clk_i', '20', '1', 'invalid', False, False),
        ('missing_derate', 'clk_i', 'clk_i', '20', '1', None, False, False),
        ('openroad_engine', 'clk_i', 'clk_i', '20', '1', '5.0', True, False),
    ]:
        mock = f'proc all_clocks {{}} {{return {{{clocks}}}}}\nproc get_clocks {{x}} {{return {{{name}}}}}\n'
        mock += f'proc get_property {{clock key}} {{if {{$key eq "period"}} {{return {period}}}; return {propagated}}}\n'
        mock += 'unset -nocomplain ::env(TIME_DERATING_CONSTRAINT)\n'
        if percent is not None:
            mock += f'set ::env(TIME_DERATING_CONSTRAINT) {{{percent}}}\n'
        if engine:
            mock += 'namespace eval ::ord {}\n'
        script = mock + 'if {[catch {\n' + derate + '\nif {[namespace exists ::ord]} {error "wrong engine"}\n' + CLOCK_GUARD + '\n} msg]} {puts stderr $msg; exit 1}\nexit 0\n'
        result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
        assert (result.returncode == 0) == good, (label, result.stdout, result.stderr)
        cases.append(dict(case=label, expected_pass=good, returncode=result.returncode))
    report = dict(status='PASS_GUARDS_NOT_PHYSICAL_SIGNOFF', accepted=False,
                  malformed_script_rejections=rejected, tcl_cases=cases)
    out = ROOT / 'hw/soc/out/core-only-extracted-guards'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
