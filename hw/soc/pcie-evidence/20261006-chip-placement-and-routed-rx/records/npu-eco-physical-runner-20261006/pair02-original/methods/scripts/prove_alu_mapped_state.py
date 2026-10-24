#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only all-binary next-state equivalence of the archived mapped C10 pair.

Only actual storage boundaries are exposed. Every combinational mapped cell
remains in the SAT problem. A proposed state bijection is an obligation, not a
proof: all FF D/clock/reset, clock-gate latch controls, external outputs and
opaque-memory inputs must agree for every shared state/input assignment.
Equal corresponding initial states and identical opaque SRAM behavior are
explicit preconditions. No reset-reachability, 4-state, CDC or physical claim.
"""
import argparse
import collections
import copy
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import time
import zipfile

import run_cloud_alu_prefix as archived
import run_cloud_timing_experiment as common

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = dict(url='https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/closure-alu-prefix-36998734236-20261002.zip',
               bytes=10989784, sha256='bc8345496dbcee984b9497eb6d3fd0d39b287a38e6d1e16d795c713bc11f5871')
PAIR = {
    'original': dict(bytes=10274923, sha256='5d05a3bc48cdd8c92dd51e61f1cff81f52e7ffcb973c2a8256f21b6648857fd8'),
    'candidate': dict(bytes=10370597, sha256='ff0fa54dac1855c21c43e3c463042ff21eefa3be65f8481ba79701742c5f796c'),
}
METHOD_PINS = {
    'scripts/run_cloud_alu_prefix.py': 'd7b390371a6f2a871b4861edcc6728d0856b9a5736308e5cc84b4bca393e5fea',
    'scripts/prepare_alu_prefix.py': 'ae22ae3b8e2206ade9d5f6499bc5c9f032d4143cc9b25eda9427f78500e020b5',
    'scripts/run_cloud_timing_experiment.py': '689c4dbd5a036fc1919d25c0d816f1740a878b11d7dfef432ae7e41c31197524',
    'scripts/bootstrap_oss.py': 'e721a22cd15131fcce79f0283863f0b6db2accb9c7349324360602e0f1c81277',
    archived.LOCK: '816eb1c44531345b1e8ad5b6fae5c099977ba30c5236e47a28e2bf1282a8006c',
    archived.MANIFEST: 'b8c3044903eff78728c4a5205a2e054576ad91ccdaa0bff28c59de3d88ae712a',
}
OWN = ('scripts/prove_alu_mapped_state.py', 'sw/tests/test_alu_mapped_state.py',
       '.github/workflows/timing-alu-mapped-state.yml')
FF = 'sg13g2_dfrbpq_1'
CG = 'sg13g2_lgcp_1'
SP = 'RM_IHPSG13_1P_2048x64_c2_bm_bist'
DP = 'RM_IHPSG13_2P_256x16_c2_bm_bist'
TT_SHA = '968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
REQUIREMENTS = dict(ff=10009, gate=3, memory=20, memory_input_bits=4032,
                    memory_output_bits=768, external_input_bits=48, external_output_bits=253)
PREFIX = '__mapped_state_equiv_'


def require(test, message):
    if not test:
        raise ValueError(message)


def quoted(path):
    return json.dumps(str(Path(path).resolve()))


def macro_ports(kind):
    require(kind in (SP, DP), 'Unknown opaque memory')
    data, address = (64, 11) if kind == SP else (16, 8)
    ports = {}
    for side in ('A',) if kind == SP else ('A', 'B'):
        for suffix in ('CLK', 'MEN', 'WEN', 'REN', 'DLY', 'BIST_CLK', 'BIST_EN', 'BIST_MEN', 'BIST_WEN', 'BIST_REN'):
            ports[side+'_'+suffix] = ('input', 1)
        for suffix in ('ADDR', 'BIST_ADDR'):
            ports[side+'_'+suffix] = ('input', address)
        for suffix in ('DIN', 'BM', 'BIST_DIN', 'BIST_BM'):
            ports[side+'_'+suffix] = ('input', data)
        ports[side+'_DOUT'] = ('output', data)
    return ports


def cell_contract(cell, ports):
    require(set(cell['connections']) == set(ports) and cell.get('parameters', {}) == {},
            'Changed storage pin set/parameters')
    require(cell['port_directions'] == {p: direction for p, (direction, _) in ports.items()},
            'Changed storage pin directions')
    for port, (_, width) in ports.items():
        require(len(cell['connections'][port]) == width, 'Changed storage pin width')


def inspect(module):
    require(not any(name.startswith(PREFIX) for name in (*module['ports'], *module['netnames'], *module['cells'])),
            'Reserved proof namespace already used')
    require(not module.get('memories') and not module.get('processes'), 'Unlowered state or processes')
    require(all(port['direction'] in ('input', 'output') for port in module['ports'].values()), 'Unsupported inout')
    require(all(bit in ('0', '1') or isinstance(bit, int)
                for port in module['ports'].values() for bit in port['bits']), 'Unknown/Z external port bit')
    counts = collections.Counter(ff=0, gate=0, memory=0, memory_input_bits=0, memory_output_bits=0)
    counts.update({'external_'+direction+'_bits': sum(len(p['bits']) for p in module['ports'].values()
                   if p['direction'] == direction) for direction in ('input', 'output')})
    state = {'ff': {}, 'gate': {}, 'memory': {}}
    drivers = set()
    for name, cell in module['cells'].items():
        kind = cell['type']
        if kind == FF:
            ports = dict(Q=('output', 1), D=('input', 1), CLK=('input', 1), RESET_B=('input', 1))
            group = 'ff'
        elif kind == CG:
            ports = dict(GCLK=('output', 1), GATE=('input', 1), CLK=('input', 1))
            group = 'gate'
        elif kind in (SP, DP):
            ports = macro_ports(kind)
            group = 'memory'
        else:
            require(kind.startswith('sg13g2_') and not re.search(r'(dff|dfr|dly|dlh|dll|lgcp)', kind),
                    'Unknown/unmapped/extra sequential cell: '+kind)
            continue
        cell_contract(cell, ports)
        counts[group] += 1
        state[group][name] = cell
        for port, (direction, width) in ports.items():
            if group == 'memory': counts['memory_'+direction+'_bits'] += width
            if direction == 'output':
                bits = cell['connections'][port]
                require(all(isinstance(bit, int) and bit not in drivers for bit in bits),
                        'Aliased/constant/multiple storage outputs')
                drivers.update(bits)
    require(all(bit in ('0', '1') or isinstance(bit, int)
                for cell in module['cells'].values() for bits in cell['connections'].values() for bit in bits),
            'Unknown/Z bit in mapped logic')
    return state, dict(counts)


def q_signatures(module, state):
    """Public aliases through exact buffers/inverters suggest, never prove, Q pairing."""
    labels = collections.defaultdict(set)
    for name, net in module['netnames'].items():
        if not re.fullmatch(r'_\d+_', name):
            offset = net.get('offset', 0)
            for index, bit in enumerate(net['bits']):
                labels[bit].add((name, offset+index))
    edges = collections.defaultdict(list)
    for cell in module['cells'].values():
        if re.fullmatch(r'sg13g2_(?:buf|inv)_\d+', cell['type']):
            invert = '_inv_' in cell['type']
            output = 'Y' if invert else 'X'
            cell_contract(cell, {'A': ('input', 1), output: ('output', 1)})
            edges[cell['connections']['A'][0]].append((cell['connections'][output][0], int(invert)))
    result = {}
    for name, cell in state['ff'].items():
        todo = [(cell['connections']['Q'][0], 0)]
        seen, signature = set(), set()
        while todo:
            bit, parity = todo.pop()
            if (bit, parity) in seen: continue
            seen.add((bit, parity))
            signature.update((label, index, parity) for label, index in labels[bit])
            todo.extend((target, parity ^ inv) for target, inv in edges[bit])
        result[name] = tuple(sorted(signature))
    return result


def propose_bijection(left, right):
    states = [inspect(m)[0] for m in (left, right)]
    require({p: (v['direction'], len(v['bits'])) for p, v in left['ports'].items()} ==
            {p: (v['direction'], len(v['bits'])) for p, v in right['ports'].items()}, 'External interface mismatch')
    for group in ('gate', 'memory'):
        require(states[0][group].keys() == states[1][group].keys(), 'Unmatched '+group)
        for name in states[0][group]:
            require(states[0][group][name]['type'] == states[1][group][name]['type'], 'Storage type mismatch')
    signatures = [q_signatures(m, state) for m, state in zip((left, right), states)]
    maps, anonymous = [], []
    for sig in signatures:
        mapping = {}
        for name, key in sig.items():
            if key:
                require(key not in mapping, 'Ambiguous public state anchor')
                mapping[key] = name
        maps.append(mapping)
        anonymous.append(sorted(name for name, key in sig.items() if not key))
    require(maps[0].keys() == maps[1].keys(), 'Unmatched public state anchors')
    require(len(anonymous[0]) == len(anonymous[1]), 'Unmatched anonymous state')
    pairs = [(maps[0][key], maps[1][key]) for key in sorted(maps[0])] + list(zip(*anonymous))
    require(len(pairs) == len(states[0]['ff']) == len(states[1]['ff']) and
            len({a for a, _ in pairs}) == len(pairs) == len({b for _, b in pairs}), 'State mapping is not bijective')
    return pairs, dict(anchored=len(maps[0]), proposed_anonymous=len(anonymous[0]),
                      anonymous_method='Lexicographic retained-cell order; untrusted until all equations prove')


def lift(module, ordered_ff):
    """Replace only actual state/opaque outputs; export all boundary obligations."""
    state, counts = inspect(module)
    require(set(ordered_ff) == set(state['ff']) and len(ordered_ff) == len(state['ff']), 'Incomplete state mapping')
    out = copy.deepcopy(module)
    bit_lists = [n['bits'] for n in module['netnames'].values()]
    bit_lists.extend(p['bits'] for p in module['ports'].values())
    bit_lists.extend(bits for cell in module['cells'].values() for bits in cell['connections'].values())
    next_bit = 1+max(bit for bits in bit_lists for bit in bits if isinstance(bit, int))
    labels = {}
    def port(name, direction, bits, meanings):
        key = PREFIX+name
        require(bits and len(bits) == len(meanings), 'Empty/mismatched proof boundary')
        out['ports'][key] = dict(direction=direction, bits=bits)
        labels[key] = meanings
    q, data, clk, reset = [], [], [], []
    for name in ordered_ff:
        pins = state['ff'][name]['connections']
        for dest, pin in ((q, 'Q'), (data, 'D'), (clk, 'CLK'), (reset, 'RESET_B')): dest.extend(pins[pin])
        del out['cells'][name]
    for name, direction, bits in [('ff_state', 'input', q), ('ff_d', 'output', data),
                                   ('ff_clk', 'output', clk), ('ff_reset_b', 'output', reset)]:
        port(name, direction, bits, ordered_ff)
    gate_states, gate_clks, gate_enables, gate_next, names = [], [], [], [], []
    for index, name in enumerate(sorted(state['gate'])):
        pins = state['gate'][name]['connections']
        current, nxt = next_bit, next_bit+1
        next_bit += 2
        gate_states.append(current); gate_clks.extend(pins['CLK']); gate_enables.extend(pins['GATE'])
        gate_next.append(nxt); names.append(name)
        del out['cells'][name]
        # Pinned lgcp statetable: CLK=L loads GATE, CLK=H retains int_GATE;
        # GCLK state_function is CLK * int_GATE, not an arbitrary cutpoint.
        width = {'WIDTH': format(1, '032b')}
        out['cells'][PREFIX+'gate_latch_'+str(index)] = dict(type='$mux', parameters=width,
            attributes={}, port_directions=dict(A='input', B='input', S='input', Y='output'),
            connections=dict(A=pins['GATE'], B=[current], S=pins['CLK'], Y=[nxt]))
        out['cells'][PREFIX+'gate_output_'+str(index)] = dict(type='$and',
            parameters={key:format(value, '032b') for key, value in dict(A_SIGNED=0, B_SIGNED=0, A_WIDTH=1, B_WIDTH=1, Y_WIDTH=1).items()},
            attributes={}, port_directions=dict(A='input', B='input', Y='output'),
            connections=dict(A=pins['CLK'], B=[current], Y=pins['GCLK']))
    if names:
        for name, direction, bits in [('gate_state', 'input', gate_states), ('gate_clk', 'output', gate_clks),
                                     ('gate_enable', 'output', gate_enables), ('gate_next', 'output', gate_next)]:
            port(name, direction, bits, names)
    memory_inputs, memory_outputs, in_labels, out_labels = [], [], [], []
    for name in sorted(state['memory']):
        cell = state['memory'][name]
        for pin, (direction, width) in sorted(macro_ports(cell['type']).items()):
            bits = cell['connections'][pin]
            dest, meanings = (memory_inputs, in_labels) if direction == 'input' else (memory_outputs, out_labels)
            dest.extend(bits); meanings.extend((name, pin, i) for i in range(width))
        del out['cells'][name]
    if state['memory']:
        port('memory_outputs', 'input', memory_outputs, out_labels)
        port('memory_inputs', 'output', memory_inputs, in_labels)
    require(len(out['cells']) == len(module['cells'])-counts['ff']-counts['memory']+counts['gate'],
            'Unexpected mapped-cell deletion')
    return out, labels


def validate_gate_liberty(path):
    require(common.sha(path) == TT_SHA, 'Changed Boolean-function Liberty')
    text = path.read_text()
    start = text.index('  cell (sg13g2_lgcp_1) {')
    body = text[start:text.index('\n  cell (', start+1)]
    required = ['clock_gating_integrated_cell : "latch_posedge";', 'statetable ("CLK GATE", "int_GATE")',
                'L L : - : L', 'L H : - : H', 'H - : - : N', 'state_function : "CLK * int_GATE";']
    require(all(x in body for x in required), 'Clock-gate latch semantics changed')
    return dict(type=CG, state='int_GATE', transparent_when='CLK=0', next='CLK ? state : GATE', output='CLK & state',
                liberty_sha256=TT_SHA)


def frontend_script(netlist, library, memory_library, sp_stub, output):
    return f'''read_liberty -lib {quoted(library)}
read_liberty -lib {quoted(memory_library)}
read_verilog -lib {quoted(sp_stub)}
read_verilog {quoted(netlist)}
hierarchy -check -top soc_top
check -assert
write_json {quoted(output)}
'''


def miter_script(left, right, library, model, timeout=1800):
    def load(path, name):
        return f'''read_liberty -ignore_miss_func {quoted(library)}
read_json {quoted(path)}
prep -top soc_top -flatten
select -assert-none t:sg13g2_* t:RM_* t:$dff* t:$adff* t:$dlatch*
rename soc_top {name}
design -stash {name}
'''
    return load(left, 'gold')+load(right, 'gate')+f'''design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
miter -equiv -flatten gold gate miter
hierarchy -top miter
opt -full
check -assert
stat
sat -verify -prove trigger 0 -show-inputs -show-outputs -timeout {timeout} -dump_json {quoted(str(model)+'.json')} -dump_vcd {quoted(str(model)+'.vcd')}
'''


def outcome(code, log):
    if code == 0 and log.count('SAT proof finished - no model found: SUCCESS!') == 1:
        return 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS'
    if code != 0 and 'model found: FAIL!' in log and 'proof did fail' in log:
        return 'COUNTEREXAMPLE_PRESERVED'
    raise ValueError('Native proof incomplete/tool error; no equivalence verdict')


def execute(runtime, script, output, name, timeout=2100):
    def limit():
        resource.setrlimit(resource.RLIMIT_AS, (6*1024**3, 6*1024**3))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    command = [str(runtime), 'yosys', '-Q', '-T', '-s', str(script)]
    started = time.monotonic()
    with (output/(name+'.log')).open('x') as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, preexec_fn=limit)
        try:
            code = child.wait(timeout=timeout)
        except BaseException:
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            child.wait()
            raise
    row = dict(command=command, returncode=code, seconds=time.monotonic()-started,
               script=archived.pin(script), log=archived.pin(output/(name+'.log')))
    common.save(output/(name+'-execution.json'), row)
    return row


def fixture():
    """Two observable independent FFs with real reset and mapped inverter."""
    cells = {}
    for i in range(2):
        cells['ff'+str(i)] = dict(type=FF, parameters={}, attributes={},
            port_directions=dict(Q='output', D='input', CLK='input', RESET_B='input'),
            connections=dict(Q=[10+i], D=[2+i], CLK=[4], RESET_B=[5]))
    cells['inv'] = dict(type='sg13g2_inv_1', parameters={}, attributes={},
        port_directions=dict(A='input', Y='output'), connections=dict(A=[10], Y=[12]))
    return dict(attributes={}, ports={
        'data':dict(direction='input', bits=[2,3]), 'clock':dict(direction='input', bits=[4]),
        'reset_b':dict(direction='input', bits=[5]), 'output_q':dict(direction='output', bits=[10,11,12])},
        cells=cells, netnames={name:dict(bits=[bit], hide_name=0, attributes={})
                             for name, bit in [('a',2),('b',3),('clk',4),('rst',5),('state0',10),('state1',11),('out_inv',12)]})


def controls(runtime, library, output):
    original = fixture()
    original['cells']['icg'] = dict(type=CG, parameters={}, attributes={},
        port_directions=dict(CLK='input', GATE='input', GCLK='output'),
        connections=dict(CLK=[4], GATE=[2], GCLK=[20]))
    original['cells']['ff1']['connections']['CLK'] = [20]
    original['netnames']['gated_clock'] = dict(bits=[20], attributes={})
    original['ports']['output_gclk'] = dict(direction='output', bits=[20])
    left, _ = lift(original, ['ff0', 'ff1'])
    common.save(output/'tiny-left.json', {'modules': {'soc_top': left}})
    results = {}
    for case in ('equal', 'wrong_state_pair', 'wrong_reset', 'wrong_output', 'wrong_gate_latch'):
        right, _ = lift(original, ['ff1', 'ff0'] if case == 'wrong_state_pair' else ['ff0', 'ff1'])
        if case == 'wrong_reset': right['ports'][PREFIX+'ff_reset_b']['bits'][0] = '0'
        if case == 'wrong_output': right['ports']['output_q']['bits'][0] = '0'
        if case == 'wrong_gate_latch': right['ports'][PREFIX+'gate_next']['bits'][0] = '0'
        path = output/('tiny-'+case+'.json'); common.save(path, {'modules': {'soc_top': right}})
        model = output/('tiny-'+case+'-model')
        script = output/('tiny-'+case+'.ys')
        script.write_text(miter_script(output/'tiny-left.json', path, library, model, 30))
        row = execute(runtime, script, output, 'tiny-'+case, 60)
        verdict = outcome(row['returncode'], (output/('tiny-'+case+'.log')).read_text())
        require(verdict == ('PROVED_ALL_BINARY_BOUNDARY_EQUATIONS' if case == 'equal' else 'COUNTEREXAMPLE_PRESERVED'),
                'Wrong native control outcome: '+case)
        if case != 'equal':
            require(model.with_suffix('.json').is_file() and model.with_suffix('.vcd').is_file(), 'Missing negative model')
        results[case] = dict(verdict=verdict, execution=row)
    return results


def run(output, work):
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full mapped-state native gate is cloud-only')
    output, work = common.fresh_directory(output), common.fresh_directory(work)
    row = dict(status='PREPARING', github_source_commit=os.environ.get('GITHUB_SHA'),
               original_producer_commit='b4387d7dc2436f0b223be17f93310b883c7344c1', original_run=36998734236,
               original_artifact=11223062019, archive=ARCHIVE, candidate_adopted=False,
               full_soc_functional_accepted=False, timing_accepted=False, manufacturing_approval=False,
               scope='All binary combinational equations at actual storage boundaries, under a proved state bijection; equal initial corresponding FF/latch state and identical opaque SRAM behavior are preconditions. No reset reachability, 4-state, CDC, SRAM internals or physical acceptance.',
               limits=dict(native_address_space_bytes=6*1024**3, sat_timeout_seconds=1800))
    methods = {}
    try:
        for name in (*METHOD_PINS, *OWN):
            source = ROOT/name
            if name in METHOD_PINS: require(common.sha(source) == METHOD_PINS[name], 'Changed pinned helper: '+name)
            dest = output/'methods'/name; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(source.read_bytes()); methods[name] = archived.pin(dest)
        row['methods'] = methods; common.save(output/'result.json', row)
        lock = archived.validate_lock(json.loads((ROOT/archived.LOCK).read_text()))
        manifest = common.validate_manifest(json.loads((ROOT/archived.MANIFEST).read_text()))
        bundle = work/'source-inputs'; archived.restore(ROOT/lock['archive']['path'], bundle, lock)
        library = bundle/'pdk/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        memory_lib = bundle/'pdk/libs.ref/sg13g2_sram/lib/RM_IHPSG13_2P_256x16_c2_bm_bist_typ_1p20V_25C.lib'
        stub = bundle/'repo/hw/soc/pnr/RM_IHPSG13_1P_2048x64_c2_bm_bist_bb.v'
        row['gate_semantics'] = validate_gate_liberty(library)
        archive = work/'source.zip'; common.download(ARCHIVE, archive)
        inputs = output/'inputs'; inputs.mkdir()
        with zipfile.ZipFile(archive) as z:
            require(len(z.namelist()) == len(set(z.namelist())), 'Duplicate original artifact members')
            for tag, expected in PAIR.items():
                info = z.getinfo('synthesis-'+tag+'/soc_top.netlist.v')
                require(info.file_size == expected['bytes'], 'Wrong mapped member size')
                path = inputs/(tag+'.v'); path.write_bytes(z.read(info)); common.verify_file(path, expected)
        runtime = work/'runtime.AppImage'; common.download(manifest['runtime'], runtime); runtime.chmod(0o755)
        row['runtime'] = manifest['runtime']
        tiny = output/'controls'; tiny.mkdir(); row['controls'] = controls(runtime, library, tiny)
        common.save(output/'result.json', row)
        modules = {}
        row['frontend'] = {}
        for tag in PAIR:
            path = work/(tag+'.frontend.json'); script = output/(tag+'-frontend.ys')
            script.write_text(frontend_script(inputs/(tag+'.v'), library, memory_lib, stub, path))
            execution = execute(runtime, script, output, tag+'-frontend', 180)
            require(execution['returncode'] == 0, 'Mapped frontend failed: '+tag)
            module = json.loads(path.read_text())['modules']['soc_top']
            state, counts = inspect(module); require(counts == REQUIREMENTS, 'Incomplete or changed mapped state boundary')
            require(collections.Counter(c['type'] for c in state['memory'].values()) == {SP:4, DP:16}, 'Opaque memory inventory changed')
            modules[tag] = module
            row['frontend'][tag] = dict(execution=execution, json=archived.pin(path), counts=counts,
                                       complete_mapped_cells=len(module['cells']))
        pairs, proposal = propose_bijection(modules['original'], modules['candidate'])
        require(proposal['anchored'] >= 9892 and proposal['proposed_anonymous'] <= 117, 'State anchor census regressed')
        common.save(output/'state-bijection-proposal.json', dict(pairs=pairs, **proposal, status='UNPROVED_PROPOSAL'))
        row['state_proposal'] = proposal
        for index, tag in enumerate(PAIR):
            lifted, meanings = lift(modules[tag], [pair[index] for pair in pairs])
            input_count = sum(len(p['bits']) for p in lifted['ports'].values() if p['direction']=='input')
            output_count = sum(len(p['bits']) for p in lifted['ports'].values() if p['direction']=='output')
            require((input_count, output_count) == (10828, 34321), 'Proof boundary bit census differs')
            common.save(output/(tag+'-obligations.json'), meanings)
            common.save(output/(tag+'-lifted.json'), {'modules': {'soc_top': lifted}})
        row.update(status='PROVING_ALL_BOUNDARIES', symbolic_input_bits=10828, compared_output_bits=34321)
        common.save(output/'result.json', row)
        script = output/'full-miter.ys'; model = output/'full-counterexample'
        script.write_text(miter_script(output/'original-lifted.json', output/'candidate-lifted.json', library, model))
        execution = execute(runtime, script, output, 'full-miter')
        verdict = outcome(execution['returncode'], (output/'full-miter.log').read_text())
        if verdict == 'COUNTEREXAMPLE_PRESERVED':
            require(model.with_suffix('.json').is_file() and model.with_suffix('.vcd').is_file(), 'Missing full counterexample')
        row.update(status=verdict, full_proof=execution, state_bijection_proved=verdict=='PROVED_ALL_BINARY_BOUNDARY_EQUATIONS')
        for tag, expected in PAIR.items(): common.verify_file(inputs/(tag+'.v'), expected)
        common.verify_file(runtime, manifest['runtime']); common.verify_file(archive, ARCHIVE)
        for name, expected in lock['files'].items(): common.verify_file(bundle/name, expected)
        for name, expected in methods.items(): common.verify_file(output/'methods'/name, expected)
        row['all_input_pins_rechecked'] = True
    except BaseException as exc:
        row.update(status='FAILED_OR_INCOMPLETE_PRESERVED', error=repr(exc))
        raise
    finally:
        row['outputs'] = {str(p.relative_to(output)): archived.pin(p) for p in sorted(output.rglob('*'))
                          if p.is_file() and p != output/'result.json'}
        common.save(output/'result.json', row)
    require(row['status'] == 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS',
            'Proposed mapped-state relation has a preserved counterexample; mapping itself may need correction')
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    print(run(args.output.resolve(), args.work.resolve())['status'])


if __name__ == '__main__': main()
