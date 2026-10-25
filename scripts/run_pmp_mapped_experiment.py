#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bounded isolated C10 PMP mapping, unconstrained equivalence and zero-wire STA.

This measures the prepared comparator candidate without changing default RTL.
RTL-to-mapped results remain distinct from mapped-pair results, including any
counterexample. No routed, whole-SoC or production acceptance follows from this.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import time

import prepare_pmp_prefix as pmp

APP_SHA = 'd6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
PREPARE_SHA = '8bc267084c47f90b422e0e89b7384c9e442cda84f4a7393637e9a5c6e1632c4d'
PDK_FILES = {
    'lib/sg13g2_stdcell_typ_1p20V_25C.lib': '968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4',
    'lib/sg13g2_stdcell_slow_1p08V_125C.lib': 'ed1cff6e4d66d89d200e94c2213b8926a71c451218ca2df9b1157c98460e4b1d',
    'lib/sg13g2_stdcell_fast_1p32V_m40C.lib': '547c5fb3ef0eabe0362de7fb361ff736f6791987996b4b1af39b70deb569a72e',
    'lef/sg13g2_tech.lef': 'e3470344dfac5347b176fb3f8e0f0548d17a66b8f433626a8987dcb2ae4828b6',
    'lef/sg13g2_stdcell.lef': 'c7575039af0b124e1834c407bfb9ac7a2db576d1e3533d98474dad3fbc2af589',
}
LIB_NAMES = dict(typ='typ_1p20V_25C', slow='slow_1p08V_125C', fast='fast_1p32V_m40C')
PROFILE = 'chparam -set PMPGranularity 0 -set PMPNumRegions 4 -set PMPNumChan 3 ibex_pmp'
PORTS = dict(csr_pmp_cfg_i=('input', 24), csr_pmp_addr_i=('input', 136),
             csr_pmp_mseccfg_i=('input', 3), debug_mode_i=('input', 1),
             priv_mode_i=('input', 6), pmp_req_addr_i=('input', 102),
             pmp_req_type_i=('input', 6), pmp_req_err_o=('output', 3))
MAX_OUTPUT = 30 * 1024**2
MAX_AS = 2 * 1024**3
SDC = '''create_clock -name virtual_pmp -period 20
set_input_delay 0 -clock virtual_pmp [all_inputs]
set_output_delay 0 -clock virtual_pmp [all_outputs]
set_driving_cell -lib_cell sg13g2_buf_4 [all_inputs]
set_load 0.005 [all_outputs]
set_timing_derate -early 0.95
set_timing_derate -late 1.05
'''


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def ys(path):
    return json.dumps(str(Path(path).resolve()))


def tcl(path):
    value = str(Path(path).resolve())
    if any(c in value for c in '{}\n\r\\'):
        raise ValueError('Unsupported Tcl path')
    return '{' + value + '}'


def map_script(source, output, tag, lib):
    if tag not in ('original', 'candidate'):
        raise ValueError('Unsupported mapping case')
    return f'''read_liberty -lib {ys(lib)}
read_verilog {ys(source)}
{PROFILE}
hierarchy -check -top ibex_pmp
synth -flatten -top ibex_pmp
opt -purge
abc -liberty {ys(lib)} -constr {ys(output/'abc.constr')} -D 20
opt_clean -purge
check -assert
write_verilog -noattr {ys(output/(tag+'.netlist.v'))}
write_json {ys(output/(tag+'.mapped.json'))}
splitnets
clean
write_verilog -noattr -noexpr -nohex -nodec {ys(output/(tag+'.sta.v'))}
tee -o {ys(output/(tag+'.area.rpt'))} stat -liberty {ys(lib)}
'''


def proof_script(left, left_mapped, right, right_mapped, lib, model_prefix):
    def load(path, mapped, name):
        return ((f'read_liberty -ignore_miss_func {ys(lib)}\n' if mapped else '')
                + f'read_verilog {ys(path)}\n' + ('' if mapped else PROFILE + '\n')
                + f'prep -top ibex_pmp -flatten\nrename ibex_pmp {name}\ndesign -stash {name}\n')
    return load(left, left_mapped, 'gold') + load(right, right_mapped, 'gate') + f'''design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
miter -equiv -flatten gold gate miter
hierarchy -top miter
memory_map
opt_clean
sat -verify -prove trigger 0 -show-inputs -show-outputs -timeout 120 -dump_json {ys(str(model_prefix)+'.json')} -dump_vcd {ys(str(model_prefix)+'.vcd')}
'''


def sta_script(netlist, lib, stdcell, sdc):
    return f'''read_lef {tcl(stdcell/'lef/sg13g2_tech.lef')}
read_lef {tcl(stdcell/'lef/sg13g2_stdcell.lef')}
read_liberty {tcl(lib)}
read_verilog {tcl(netlist)}
link_design ibex_pmp
read_sdc {tcl(sdc)}
if {{[llength [all_inputs]] != 278 || [llength [all_outputs]] != 3}} {{ error "Unexpected PMP interface" }}
puts "PMP_INTERFACE 278 3"
puts [format "PMP_WORST_SETUP_NS %s" [sta::format_time [sta::worst_slack_cmd max] 9]]
foreach port [lsort [all_outputs]] {{
    puts "PMP_OUTPUT_BEGIN [get_property $port full_name]"
    report_checks -path_delay max -to $port -group_path_count 1 -fields {{fanout cap slew}} -digits 9
    puts "PMP_OUTPUT_END"
}}
puts "PMP_STA_COMPLETE"
exit
'''


def inspect_mapped(path):
    module = json.loads(path.read_text())['modules']['ibex_pmp']
    ports = {name: (port['direction'], len(port['bits'])) for name, port in module['ports'].items()}
    if ports != PORTS:
        raise ValueError('Mapped PMP profile or interface changed')
    cells = module['cells']
    if not cells or any(not cell['type'].startswith('sg13g2_') for cell in cells.values()):
        raise ValueError('Unmapped or absent standard cells')
    if any(re.search(r'(dfr|dff|latch|dlh|dll)', cell['type']) for cell in cells.values()):
        raise ValueError('Unexpected state in combinational PMP')
    return dict(input_bits=278, output_bits=3, cell_count=len(cells),
                cell_types=sorted({cell['type'] for cell in cells.values()}))


def proof_outcome(returncode, log):
    if returncode == 0 and log.count('SAT proof finished - no model found: SUCCESS!') == 1:
        return 'PROVED_ALL_BINARY_INPUTS'
    if returncode != 0 and 'proof did fail' in log and 'model found: FAIL!' in log:
        return 'COUNTEREXAMPLE'
    raise ValueError('Formal result is incomplete or not a proof/counterexample')


def parse_sta(log):
    if re.search(r'(^|\n)(Error|ERROR|\[ERROR)', log) or log.count('PMP_STA_COMPLETE') != 1:
        raise ValueError('STA incomplete or failed')
    if log.count('PMP_INTERFACE 278 3') != 1:
        raise ValueError('Missing exact PMP STA interface')
    matches = re.findall(r'^PMP_WORST_SETUP_NS ([-+\d.eE]+)$', log, re.M)
    blocks = re.findall(r'^PMP_OUTPUT_BEGIN ([^\n]+)\n(.*?)^PMP_OUTPUT_END$', log, re.M | re.S)
    if len(matches) != 1 or len(blocks) != 3 or {x[0] for x in blocks} != {f'pmp_req_err_o[{i}]' for i in range(3)}:
        raise ValueError('STA does not cover all three outputs exactly once')
    slack = float(matches[0])
    rows = {}
    for name, body in blocks:
        arrivals = re.findall(r'^\s*([-+\d.eE]+)\s+data arrival time\s*$', body, re.M)
        slacks = re.findall(r'^\s*([-+\d.eE]+)\s+slack \((?:MET|VIOLATED)\)\s*$', body, re.M)
        if len(arrivals) != 2 or len(slacks) != 1 or abs(float(arrivals[0])+float(arrivals[1])) > 2e-6:
            raise ValueError('Missing timed path or endpoint slack')
        rows[name] = dict(arrival_ns=float(arrivals[0]), slack_ns=float(slacks[0]))
    if not math.isfinite(slack) or any(not math.isfinite(v) for row in rows.values() for v in row.values()):
        raise ValueError('Non-finite timing')
    if abs(min(row['slack_ns'] for row in rows.values()) - slack) > 2e-6:
        raise ValueError('Worst slack disagrees with complete output paths')
    return dict(worst_setup_slack_ns=slack, worst_arrival_ns=max(x['arrival_ns'] for x in rows.values()), outputs=rows)


def tree_bytes(path):
    return sum(item.stat().st_size for item in path.rglob('*') if item.is_file())


def bounded_run(command, log, output, timeout):
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (MAX_AS, MAX_AS))
        resource.setrlimit(resource.RLIMIT_FSIZE, (8 * 1024**2, 8 * 1024**2))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    started = time.monotonic()
    with log.open('x') as stream:
        child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                 start_new_session=True, preexec_fn=limit)
        try:
            while child.poll() is None:
                if time.monotonic() - started > timeout or tree_bytes(output) > MAX_OUTPUT - 1024**2:
                    raise RuntimeError('Native experiment exceeded time/output budget')
                time.sleep(0.1)
        except BaseException:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
            raise
    if tree_bytes(output) > MAX_OUTPUT:
        raise RuntimeError('Native experiment output exceeded 30 MiB')
    return dict(command=command, returncode=child.returncode, elapsed_seconds=time.monotonic()-started,
                log_sha256=sha(log))


def run(prepared, output, app, stdcell):
    prepared, output, app, stdcell = (x.resolve() for x in (prepared, output, app, stdcell))
    preparation = pmp.verify_prepared(prepared)
    expected = {app: APP_SHA, Path(pmp.__file__).resolve(): PREPARE_SHA,
                **{stdcell/name: digest for name, digest in PDK_FILES.items()}}
    for path, digest in expected.items():
        if sha(path) != digest:
            raise ValueError('Pinned runtime/method/PDK changed: ' + str(path))
    pins = {str(path): digest for path, digest in expected.items()}
    pins.update({str(prepared/name): digest for name, digest in preparation['sources'].items()})
    pins[str(Path(__file__).resolve())] = sha(__file__)
    output.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING', profile=preparation['profile'], input_sha256=pins,
                  steps=[], mapping={}, proofs={}, timing={}, candidate_adopted=False,
                  timing_accepted=False, whole_soc_validated=False, manufacturing_approval=False,
                  constraints=dict(virtual_period_ns=20, abc_target_ps=20, external_delay_ns=0,
                    driving_cell='sg13g2_buf_4', output_load_pf=0.005, early_derate=0.95,
                    late_derate=1.05, wire_parasitics='ZERO_NOT_EXTRACTED'),
                  limits=dict(address_space_bytes=MAX_AS, output_bytes=MAX_OUTPUT),
                  scope='Isolated current-profile PMP, all binary inputs without assumptions; AppImage Yosys 0.62 mapping, not full-C10 synthesis. Library-only STA, no placement, extraction or physical acceptance.')
    def save():
        (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    def execute(name, command, timeout=180):
        row = bounded_run(command, output/(name+'.log'), output, timeout)
        row['name'] = name
        result['steps'].append(row)
        save()
        return row, (output/(name+'.log')).read_text()
    def write(name, data):
        path = output/name
        path.write_text(data)
        pins[str(path)] = sha(path)
        return path
    libs = {name: stdcell/f'lib/sg13g2_stdcell_{suffix}.lib' for name, suffix in LIB_NAMES.items()}
    try:
        save()
        row, log = execute('yosys-version', [str(app), 'yosys', '-V'], 30)
        if row['returncode'] or 'Yosys 0.62' not in log or '7326bb7d6641500ecb285c291a54a662cb1e76cf' not in log:
            raise ValueError('Unexpected Yosys runtime')
        row, log = execute('openroad-version', [str(app), 'openroad', '-version'], 30)
        if row['returncode'] or 'dcf36133a369abc8f3c5e5738cd4d82e4903c0e0' not in log:
            raise ValueError('Unexpected OpenROAD runtime')
        write('abc.constr', 'set_driving_cell sg13g2_buf_4\nset_load 0.005\n')
        write('pmp.sdc', SDC)
        for tag in ('original', 'candidate'):
            script = write(tag+'-map.ys', map_script(prepared/(tag+'.v'), output, tag, libs['typ']))
            row, _ = execute(tag+'-map', [str(app), 'yosys', '-Q', '-T', '-s', str(script)])
            if row['returncode']:
                raise ValueError('Mapping failed: ' + tag)
            result['mapping'][tag] = inspect_mapped(output/(tag+'.mapped.json'))
            for suffix in ('.netlist.v', '.sta.v', '.mapped.json', '.area.rpt'):
                pins[str(output/(tag+suffix))] = sha(output/(tag+suffix))
            save()
        cases = [
            ('original_rtl_to_mapped', prepared/'original.v', False, output/'original.netlist.v', True),
            ('candidate_rtl_to_mapped', prepared/'candidate.v', False, output/'candidate.netlist.v', True),
            ('mapped_original_to_candidate', output/'original.netlist.v', True, output/'candidate.netlist.v', True),
            ('wrong_comparison_control', prepared/'negative.v', False, output/'candidate.netlist.v', True),
        ]
        for name, left, lm, right, rm in cases:
            prefix = output/(name+'-counterexample')
            script = write(name+'.ys', proof_script(left, lm, right, rm, libs['typ'], prefix))
            row, log = execute(name, [str(app), 'yosys', '-Q', '-T', '-s', str(script)])
            verdict = proof_outcome(row['returncode'], log)
            models = {str(path.relative_to(output)): sha(path) for path in (prefix.with_suffix('.json'), prefix.with_suffix('.vcd')) if path.exists()}
            if verdict == 'COUNTEREXAMPLE' and len(models) != 2:
                raise ValueError('Counterexample model was not preserved')
            result['proofs'][name] = dict(verdict=verdict, counterexamples=models)
            save()
        if result['proofs']['wrong_comparison_control']['verdict'] != 'COUNTEREXAMPLE':
            raise ValueError('Wrong-comparison negative control was not rejected')
        for tag in ('original', 'candidate'):
            result['timing'][tag] = {}
            for corner, lib in libs.items():
                name = tag+'-'+corner
                script = write(name+'.tcl', sta_script(output/(tag+'.sta.v'), lib, stdcell, output/'pmp.sdc'))
                row, log = execute(name, [str(app), 'openroad', '-no_init', '-exit', str(script)], 60)
                if row['returncode']:
                    raise ValueError('STA failed: ' + name)
                result['timing'][tag][corner] = parse_sta(log)
                save()
        result['status'] = ('COMPLETE_ALL_EQUIVALENCE_PROVED_NEGATIVE_REJECTED'
            if all(result['proofs'][name]['verdict'] == 'PROVED_ALL_BINARY_INPUTS' for name, *_ in cases[:3])
            else 'COMPLETE_WITH_PRESERVED_EQUIVALENCE_COUNTEREXAMPLES')
        result['comparison'] = {corner: dict(
            arrival_change_ns=result['timing']['candidate'][corner]['worst_arrival_ns']-result['timing']['original'][corner]['worst_arrival_ns'],
            slack_change_ns=result['timing']['candidate'][corner]['worst_setup_slack_ns']-result['timing']['original'][corner]['worst_setup_slack_ns']) for corner in libs}
    except BaseException as exc:
        result.update(status='ERROR_OR_INCOMPLETE', error=repr(exc))
        raise
    finally:
        changed = [path for path, digest in pins.items() if not Path(path).is_file() or sha(path) != digest]
        result['input_and_generated_source_pins_unchanged'] = not changed
        if changed:
            result.update(status='ERROR_OR_INCOMPLETE', changed_inputs=changed)
        result['output_bytes_before_receipt'] = tree_bytes(output)
        result['output_inventory'] = {str(path.relative_to(output)): dict(bytes=path.stat().st_size, sha256=sha(path))
            for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'result.json'}
        save()
    if result['status'] == 'ERROR_OR_INCOMPLETE':
        raise ValueError('Experiment inputs changed')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'output', 'app', 'stdcell'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(run(args.prepared, args.output, args.app, args.stdcell)['status'])


if __name__ == '__main__':
    main()
