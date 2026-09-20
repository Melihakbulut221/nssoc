#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Report one fixed global route in independent single-corner OpenROAD processes.

Consumes a LibreLane step environment, a matching placed ODB and an exported
write_global_route_segments file. Does not place, route, repair or export a
modified design. Estimated RC is not detailed-route extraction or signoff.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time

from probe_generated_clock_corners import tcl_path

CORNERS = ('nom_fast_1p32V_m40C', 'nom_typ_1p20V_25C', 'nom_slow_1p08V_125C')
# LibreLane's base SDC divides this value by integer 100. JSON round trips
# can turn 5.0 into 5; Tcl then silently applies zero derating. Reject that
# environment before read_current_odb loads the SDC, without changing it.
DERATE_FILE = Path(__file__).with_name('check_timing_derate.tcl')
DERATE_GUARD = DERATE_FILE.read_text()
FILTER = '''foreach prefix {_LIB_CORNER_ _LAYER_RC_ _VIA_R_} {
 set keep {}
 foreach key [lsort -dictionary [array names ::env ${prefix}*]] {
  if {[lindex $::env($key) 0] eq $selected_corner} {lappend keep $::env($key)}
  unset ::env($key)
 }
 if {$prefix eq "_LIB_CORNER_" && [llength $keep] != 1} {
  error "Exactly one matching Liberty corner is required"
 }
 set idx 0
 foreach value $keep {set ::env(${prefix}${idx}) $value; incr idx}
}
'''


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def electrical_counts(text):
    """Count explicit violations; reject unrecognized report content.

    OpenSTA omits sections with no violations, so empty output is valid only
    after the caller has checked the tool exit and timing completion marker.
    """
    headings = {'max slew': 'slew', 'max capacitance': 'capacitance',
                'max fanout': 'fanout'}
    counts = dict.fromkeys(headings.values(), 0)
    kind = None
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line in headings:
            kind = headings[line]
            if kind in seen:
                raise ValueError('Repeated electrical section')
            seen.add(kind)
        elif line.startswith('Pin ') or set(line) == {'-'}:
            if kind is None:
                raise ValueError('Electrical table without heading')
        elif re.fullmatch(r'\S+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+[-+\d.eE]+\s+\(VIOLATED\)', line):
            if kind is None:
                raise ValueError('Electrical violation outside a known report section')
            counts[kind] += 1
        else:
            raise ValueError('Unrecognized electrical report line: ' + line)
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('environment', 'scripts', 'odb', 'segments', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--openroad', default='openroad')
    args = parser.parse_args(argv)
    paths = {key: getattr(args, key).resolve() for key in
             ('environment', 'scripts', 'odb', 'segments', 'output')}
    tool = shutil.which(args.openroad)
    if tool is None:
        raise ValueError('OpenROAD executable unavailable')
    tracked = {str(paths[key]): digest(paths[key]) for key in ('environment', 'odb', 'segments')}
    tracked[str(DERATE_FILE)] = digest(DERATE_FILE)
    for name in ('io.tcl', 'set_rc.tcl'):
        p = paths['scripts'] / 'openroad/common' / name
        tracked[str(p)] = digest(p)
    out = paths['output']
    out.mkdir(parents=True, exist_ok=False)
    record = dict(scope=__doc__, inputs=tracked, results={}, source_unchanged=None)
    (out / 'inputs.json').write_text(json.dumps(record, indent=2) + '\n')
    for corner in CORNERS:
        directory = out / corner
        directory.mkdir()
        script = (f'set ::env(SCRIPTS_DIR) {tcl_path(paths["scripts"])}\n'
                  f'set ::env(_TCL_ENV_IN) {tcl_path(paths["environment"])}\n'
                  'source $::env(SCRIPTS_DIR)/openroad/common/io.tcl\n' +
                  DERATE_GUARD + f'set selected_corner {corner}\n' + FILTER +
                  f'set ::env(CURRENT_ODB) {tcl_path(paths["odb"])}\n'
                  f'set ::env(STEP_DIR) {tcl_path(directory)}\n'
                  'foreach key [array names ::env SAVE_*] {unset ::env($key)}\n'
                  'read_current_odb\n'
                  'if {[lln::get_corner_names] ne [list $selected_corner]} '
                  '{error "Unexpected active corner set"}\n'
                  'lln::set_sta_cmd_corner $selected_corner\n'
                  'source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl\n'
                  'set_routing_layers -signal $::env(RT_MIN_LAYER)-$::env(RT_MAX_LAYER)\n'
                  f'read_global_route_segments {tcl_path(paths["segments"])}\n'
                  'estimate_parasitics -global_routing\n'
                  'foreach kind {max min} {\n'
                  ' report_checks -corner $selected_corner -path_delay $kind '
                  '-group_path_count 1000 -format full_clock_expanded -digits 6 '
                  '> $::env(STEP_DIR)/${kind}.rpt\n}\n'
                  'report_check_types -corner $selected_corner -max_slew -max_cap '
                  '-max_fanout -violators > $::env(STEP_DIR)/electrical.rpt\n'
                  'report_clock_properties > $::env(STEP_DIR)/clocks.rpt\n'
                  'puts "CORNER_RESULT $selected_corner setup '
                  '[worst_slack -corner $selected_corner -max] hold '
                  '[worst_slack -corner $selected_corner -min]"\n')
        path = directory / 'report.tcl'
        path.write_text(script)
        command = [tool, '-exit', '-no_splash', str(path)]
        start = time.monotonic()
        with (directory / 'run.log').open('x') as log:
            try:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
                code = result.returncode
            except subprocess.TimeoutExpired:
                code = 124
        text = (directory / 'run.log').read_text()
        found = re.findall(r'CORNER_RESULT (\S+) setup ([\d.eE+-]+) hold ([\d.eE+-]+)', text)
        row = dict(command=command, returncode=code, elapsed_s=time.monotonic() - start)
        record['results'][corner] = row
        if code or len(found) != 1 or found[0][0] != corner:
            (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
            raise RuntimeError('Corner report failed; retained logs are not a PASS')
        row.update(setup_ns=float(found[0][1]), hold_ns=float(found[0][2]))
        counts = electrical_counts((directory / 'electrical.rpt').read_text())
        if not all(math.isfinite(row[k]) for k in ('setup_ns', 'hold_ns')):
            raise ValueError('Nonfinite timing result')
        row['electrical'] = counts
        row['estimated_checks_pass'] = (row['setup_ns'] >= 0 and row['hold_ns'] >= 0
                                        and not any(counts.values()))
        (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    record['source_unchanged'] = all(digest(Path(p)) == value for p, value in tracked.items())
    if not record['source_unchanged']:
        raise RuntimeError('Input changed during reporting')
    record['all_estimated_checks_pass'] = all(r['estimated_checks_pass'] for r in record['results'].values())
    (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record['results'], indent=2))
    return 0 if record['all_estimated_checks_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
