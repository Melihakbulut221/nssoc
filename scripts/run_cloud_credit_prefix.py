#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound late-enable carry reassociation; hosted candidate only."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-credit-prefix'
SOURCE = OUT / 'source/cloud-newer-postcts'
NUMBERS = [1737168, 1737171, 1737174, 1737178, 1737181, 1737185, 1737188]
NAMES = ['$abc$1705011$auto$blifparse.cc:397:parse_blif$' + str(n) for n in NUMBERS]
ODB_SHA = '660692b3e59756186bb017a62823999db593fa9d77b6e4181be9625fa7bfb707'
LOG_SHA = '80055c3fb2022a1366d03f8a010d0c671fe603c57b3ca6ca64350b5a44668374'

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def run(command, label, env=None, expected_failure=False):
    log = OUT / (label + '.log')
    with log.open('w') as stream:
        code = subprocess.call([str(v) for v in command], env=env, stdout=stream, stderr=subprocess.STDOUT)
    text = log.read_text(errors='replace')
    if not expected_failure and (code or re.search(r'(?m)^(Error:|\[ERROR)', text)):
        raise RuntimeError((label, code, text[-10000:]))
    return code, text

def tcl(script, label):
    path = OUT / (label + '.tcl')
    path.write_text(script)
    return run([os.environ['CLOUD_APPIMAGE'], 'openroad', '-exit', path], label)[1]

def native():
    import odb
    spec = importlib.util.spec_from_file_location('hold_geometry', ROOT / 'scripts/prepare_cloud_ethernet_hold.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    row, power = module.row, module.power
    db = odb.dbDatabase.create()
    mode = os.environ['CREDIT_PREFIX_NATIVE']
    odb.read_db(db, str(SOURCE / 'relocated-placement.odb' if mode == 'prepare' else OUT / 'placed.odb'))
    block = db.getChip().getBlock()
    if mode == 'audit':
        before = json.loads((OUT / 'preparation.json').read_text())
        actual = {i.getName(): i for i in block.getInsts()}
        assert set(actual) == set(before['instances']) | set(before['added'])
        for name, original in before['instances'].items():
            assert row(actual[name]) == before['changed'].get(name, original), ('Original instance drift', name)
            actual[name].setPlacementStatus(before['statuses'][name])
        for name, expected in before['added'].items():
            value = row(actual[name])
            assert value['master'] == expected['master'] and value['pins'] == expected['pins']
            assert str(actual[name].getPlacementStatus()) == 'PLACED'
        assert {p.getName(): p.getNet().getName() if p.getNet() else None for p in block.getBTerms()} == before['boundary']
        assert set(n.getName() for n in block.getNets()) == set(before['net_names']) | set(before['added_nets'])
        assert power(block) == before['power']
        odb.write_db(db, str(OUT / 'candidate.odb'))
        (OUT / 'geometry.json').write_text(json.dumps(dict(
            status='PASS_ONLY_DECLARED_CARRY_INPUT_REASSOCIATION_AND_NEW_AND_GATES',
            original_instances=len(before['instances']), added_instances=len(before['added']),
            changed_instances=before['changed'], original_geometry_unchanged=True,
            power_geometry_unchanged=True), indent=2) + '\n')
        return
    assert mode == 'prepare' and sha(SOURCE / 'relocated-placement.odb') == ODB_SHA
    original = dict(instances={i.getName(): row(i) for i in block.getInsts()},
        statuses={i.getName(): str(i.getPlacementStatus()) for i in block.getInsts()},
        boundary={p.getName(): p.getNet().getName() if p.getNet() else None for p in block.getBTerms()},
        net_names=sorted(n.getName() for n in block.getNets()), power=power(block),
        added={}, added_nets=[], changed={})
    gates = [block.findInst(n) for n in NAMES]
    assert all(gates)
    gate_rows = [row(i) for i in gates]
    outputs, data = [], []
    for index, g in enumerate(gates):
        assert g.getMaster().getName() == ('sg13g2_nand2_1' if index == 6 else 'sg13g2_and2_1')
        output_pin = 'Y' if index == 6 else 'X'
        outputs.append(g.findITerm(output_pin).getNet().getName())
        data.append(g.findITerm('A').getNet().getName())
        assert g.findITerm('B').getNet()
        if index:
            assert g.findITerm('B').getNet().getName() == outputs[index - 1]
    enable = gates[0].findITerm('B').getNet().getName()
    assert enable == '$abc$1705011$new_n58989'
    leaves = [enable] + data
    assert len(set(leaves)) == 8 and not set(leaves) & set(outputs)
    master = db.findMaster('sg13g2_and2_1')
    assert master and master.getWidth() > 0
    for i in block.getInsts():
        if str(i.getPlacementStatus()) == 'PLACED':
            i.setPlacementStatus('FIRM')
    cache = {}
    def prefix(items, driver):
        if len(items) == 1:
            return block.findNet(items[0])
        key = tuple(items)
        if key in cache:
            return cache[key]
        split = len(items) // 2
        left, right = prefix(items[:split], driver), prefix(items[split:], driver)
        name = 'nssoc_credit_prefix_' + str(len(original['added']))
        netname = name + '_out'
        assert not block.findInst(name) and not block.findNet(netname)
        net = odb.dbNet.create(block, netname)
        inst = odb.dbInst.create(block, master, name)
        x, y = driver.getLocation()
        inst.setOrient(driver.getOrient())
        inst.setLocation(x + master.getWidth(), y)
        inst.setPlacementStatus('PLACED')
        inst.findITerm('A').connect(left)
        inst.findITerm('B').connect(right)
        inst.findITerm('X').connect(net)
        for terminal in inst.getITerms():
            kind = str(terminal.getSigType())
            if kind in ('POWER', 'GROUND'):
                peers = [t for t in driver.getITerms() if str(t.getSigType()) == kind]
                assert len(peers) == 1 and peers[0].getNet()
                terminal.connect(peers[0].getNet())
        original['added'][name] = row(inst)
        original['added_nets'].append(netname)
        cache[key] = net
        return net
    for index, gate in enumerate(gates[1:], 1):
        net = prefix(data[:index + 1], gate)
        gate.findITerm('A').disconnect()
        gate.findITerm('A').connect(net)
        gate.findITerm('B').disconnect()
        gate.findITerm('B').connect(block.findNet(enable))
        original['changed'][gate.getName()] = row(gate)
    assert power(block) == original['power']
    for net in block.getNets():
        if str(net.getSigType()) not in ('POWER', 'GROUND'):
            assert not net.getWire() and not net.getGlobalWire()
            assert net.getRSegCount() == net.getCapNodeCount() == 0
    # Emit both real gate cones from native connectivity, with shared cutpoints.
    # read_liberty supplies the actual functional cell models for the SAT proof.
    lines = ['module credit_prefix_miter(input [7:0] stimulus, output bad);',
             'wire [6:0] reference_value, candidate_value;']
    def cone(rows, label):
        allnets = sorted({r['pins'][p] for _, r in rows for p in ('A', 'B', 'Y' if r['master']=='sg13g2_nand2_1' else 'X')})
        names = {n: label + '_n' + str(k) for k, n in enumerate(allnets)}
        lines.append('wire ' + ', '.join(names.values()) + ';')
        for k, net in enumerate(leaves):
            lines.append('assign ' + names[net] + ' = stimulus[' + str(k) + '];')
        for name, r in rows:
            outpin = 'Y' if r['master'] == 'sg13g2_nand2_1' else 'X'
            ports = ','.join('.' + p + '(' + names[r['pins'][p]] + ')' for p in ('A', 'B', outpin))
            lines.append(r['master'] + ' ' + label + '_' + name + '(' + ports + ');')
        for k, net in enumerate(outputs):
            lines.append('assign ' + label + '_value[' + str(k) + '] = ' + names[net] + ';')
    cone([('g'+str(i), r) for i, r in enumerate(gate_rows)], 'reference')
    candidate = [('g'+str(i), row(g)) for i, g in enumerate(gates)]
    candidate += [('p'+str(i), r) for i, r in enumerate(original['added'].values())]
    cone(candidate, 'candidate')
    lines += ['assign bad = |(reference_value ^ candidate_value);', 'endmodule']
    (OUT / 'miter.v').write_text('\n'.join(lines) + '\n')
    original['cone'] = dict(enable=enable, data=data, outputs=outputs, original=gate_rows,
                            candidate=[r for n,r in candidate], cutpoint_bits=8)
    (OUT / 'preparation.json').write_text(json.dumps(original, separators=(',', ':')) + '\n')
    odb.write_db(db, str(OUT / 'proposed.odb'))

def main():
    from read_opensta_phase_slacks import parse_phases
    assert os.environ.get('GITHUB_ACTIONS') == 'true'
    OUT.mkdir(exist_ok=False)
    result = dict(status='RUNNING', adopted=False, timing_accepted=False,
        scope='Equivalent reassociation of one mapped credit carry cone. Same cells outside declared cone, clocks, constraints and RC. Placement estimates; full routing, extraction, hold and PHY remain required.')
    try:
        evidence = json.loads((ROOT / 'docs/evidence/cloud-local-optimize-buffers-route-failure-20261013.json').read_text())
        receipt = evidence['receipt']
        assert evidence['run'] == 38371498733
        result['source'] = receipt
        packed = OUT / 'source.tar.gz'
        run(['curl', '--fail', '--location', '--retry', '4', receipt['url'], '-o', packed], 'download')
        assert sha(packed) == receipt['sha256'] and packed.stat().st_size == receipt['bytes']
        with tarfile.open(packed) as tar:
            tar.extractall(OUT / 'source', filter='data')
        packed.unlink()
        assert sha(SOURCE / 'relocated-placement.odb') == ODB_SHA
        assert sha(SOURCE / 'relocated-placement-sta.log') == LOG_SHA
        assert sha(SOURCE / 'relocated-placement-sta.tcl') == evidence['failure_outputs']['relocated-placement-sta.tcl']
        old = json.loads((SOURCE / 'result.json').read_text())
        paths = [p for p in old['source_inputs'] if p.endswith('/inputs/postcts.odb')]
        assert len(paths) == 1
        prefix = paths[0].removesuffix('/inputs/postcts.odb')
        for p, digest in old['source_inputs'].items():
            assert p.startswith(prefix + '/')
            assert sha(SOURCE / p[len(prefix)+1:]) == digest
        script = (SOURCE / 'relocated-placement-sta.tcl').read_text().replace(prefix, str(SOURCE))
        assert str(SOURCE / 'relocated-placement.odb') in script and prefix not in script
        result['baseline'] = parse_phases(tcl(script, 'baseline'), 'CORNER')
        assert result['baseline'] == parse_phases((SOURCE / 'relocated-placement-sta.log').read_text(), 'CORNER')
        run([os.environ['CLOUD_APPIMAGE'], 'openroad', '-exit', '-python', Path(__file__).resolve()],
            'prepare', dict(os.environ, CREDIT_PREFIX_NATIVE='prepare'))
        standard = [p for p in SOURCE.rglob('*.lib') if 'stdcell' in p.name and '_typ_' in p.name]
        assert len(standard) == 1
        def prove(path, label, negative=False):
            commands = f'read_liberty -ignore_miss_func {standard[0]}; read_verilog {path}; hierarchy -check -top credit_prefix_miter; flatten; prep -top credit_prefix_miter; sat -verify -prove bad 0 -show-inputs'
            return run([os.environ['CLOUD_APPIMAGE'], 'yosys', '-p', commands], label, expected_failure=negative)
        prove(OUT / 'miter.v', 'proof')
        text = (OUT / 'miter.v').read_text()
        match = re.search(r'sg13g2_nand2_1 candidate_g6\([^\n]+;', text)
        assert match
        wrong = match[0].replace('sg13g2_nand2_1', 'sg13g2_and2_1').replace('.Y(', '.X(')
        (OUT / 'wrong-final-gate.v').write_text(text[:match.start()] + wrong + text[match.end():])
        code, log = prove(OUT / 'wrong-final-gate.v', 'proof-negative', True)
        assert code != 0 and 'proof did fail' in log
        result['logic'] = dict(status='PASS_ALL_256_CUTPOINT_ASSIGNMENTS_ALL_SEVEN_ORIGINAL_OUTPUTS',
            actual_liberty_sha256=sha(standard[0]), miter_sha256=sha(OUT / 'miter.v'),
            proof_sha256=sha(OUT / 'proof.log'), negative_control='ACTUAL_FINAL_NAND_REPLACED_BY_AND_REJECTED')
        tcl(f'read_db {{{OUT/"proposed.odb"}}}\nset_thread_count 2\ndetailed_placement -max_displacement {{30 15}}\ncheck_placement -verbose\nwrite_db {{{OUT/"placed.odb"}}}\n', 'legalize')
        run([os.environ['CLOUD_APPIMAGE'], 'openroad', '-exit', '-python', Path(__file__).resolve()],
            'audit', dict(os.environ, CREDIT_PREFIX_NATIVE='audit'))
        result['geometry'] = json.loads((OUT / 'geometry.json').read_text())
        candidate = script.replace(str(SOURCE / 'relocated-placement.odb'), str(OUT / 'candidate.odb'))
        result['candidate'] = parse_phases(tcl(candidate, 'candidate'), 'CORNER')
        assert result['candidate'].keys() == result['baseline'].keys()
        result['group_deltas_ns'] = {}
        for corner, before in result['baseline'].items():
            after = result['candidate'][corner]
            assert after['groups'].keys() == before['groups'].keys()
            result['group_deltas_ns'][corner] = {g: after['groups'][g]['worst_slack_ns']-v['worst_slack_ns']
                for g,v in before['groups'].items()}
        result.update(status='COMPLETE_SOURCE_BOUND_CREDIT_PREFIX_ECO_SCREEN_NOT_SIGNOFF',
                      candidate_odb_sha256=sha(OUT / 'candidate.odb'))
    except BaseException as error:
        result.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

if __name__ == '__main__':
    native() if os.environ.get('CREDIT_PREFIX_NATIVE') else main()
