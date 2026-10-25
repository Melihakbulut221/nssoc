#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove a new explicit state correspondence; preserve the original failed proof.

Only three candidate storage-boundary positions change. Every mapped cell and
all original symbolic inputs/output obligations remain. The fresh native proof
is unconstrained; direct netlist witnesses propose, but never prove, the mapping.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

import replay_alu_state_counterexample as replay

state = replay.state
ROOT = Path(__file__).resolve().parents[1]
REPLAY_SHA = '82568b1092fc4c1640faff1f92c3b898a91060366569ba8538981d21af0b8d4c'
BOUNDARIES = ('ff_state', 'ff_d', 'ff_clk', 'ff_reset_b')
# Index, original cell, old candidate cell, newly proposed candidate cell.
CORRECTION = (
    (9982, '_134510_', '_135104_', '_135110_'),
    (9983, '_134514_', '_135110_', '_135126_'),
    (9988, '_134529_', '_135126_', '_135104_'),
)
OWN = ('scripts/prove_alu_state_repair.py', 'sw/tests/test_alu_state_repair.py',
       '.github/workflows/timing-alu-state-repair.yml')


def object_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def permute(module, labels, mapping):
    """Move only complete FF boundary positions, preserving every other object."""
    state.require(mapping and set(mapping) == set(mapping.values()), 'Not a closed boundary permutation')
    result, meanings = copy.deepcopy(module), copy.deepcopy(labels)
    for suffix in BOUNDARIES:
        name = state.PREFIX+suffix
        port = module['ports'][name]
        state.require(port['direction'] == ('input' if suffix == 'ff_state' else 'output'), 'Wrong boundary direction')
        state.require(len(port['bits']) == len(labels[name]), 'Boundary labels differ')
        state.require(all(type(i) is int and 0 <= i < len(port['bits']) for i in mapping), 'Bad boundary index')
        for target, source in mapping.items():
            result['ports'][name]['bits'][target] = port['bits'][source]
            meanings[name][target] = labels[name][source]
    restored = copy.deepcopy(result)
    for suffix in BOUNDARIES:
        restored['ports'][state.PREFIX+suffix] = copy.deepcopy(module['ports'][state.PREFIX+suffix])
    state.require(restored == module, 'Mapped graph or non-FF boundary changed')
    return result, meanings


def witness(module, q_index, family, tag):
    q = module['ports'][state.PREFIX+'ff_state']['bits'][q_index]
    def wire(name, index=0):
        return module['netnames'][name]['bits'][index]
    def cell(name, kind, pins):
        found = module['cells'][name]
        state.require(found['type'] == kind and not found.get('parameters'), 'Witness cell type changed')
        state.require(all(found['connections'].get(pin) == [bit] for pin, bit in pins.items()), 'Witness connection changed')
        return found
    if family == 'qspi':
        name = '_063550_' if tag == 'original' else '_063685_'
        cell(name, 'sg13g2_nand2b_1', {'A_N': wire('u_qspi.phase', 2), 'B': q})
        return [name]
    if family == 'uart':
        name = '_116680_' if tag == 'original' else '_084219_'
        cell(name, 'sg13g2_nor2b_1', {'A': wire('u_uart0.rx_state', 1), 'B_N': q})
        return [name]
    state.require(family == 'can', 'Unknown witness family')
    inv, gate = ('_064333_', '_064334_') if tag == 'original' else ('_064014_', '_064015_')
    c = cell(inv, 'sg13g2_inv_1', {'A': q})
    cell(gate, 'sg13g2_a21oi_1', {'A1': c['connections']['Y'][0], 'B1': wire('u_can.ready'),
         'Y': module['ports'][state.PREFIX+'ff_d']['bits'][q_index]})
    return [inv, gate]


def corrected_proposal(original, candidate, proposal, labels):
    pairs = proposal['pairs']
    state.require(len(pairs) == 10009 and proposal['anchored'] == 9892 and proposal['proposed_anonymous'] == 117,
                  'Original state census changed')
    state.require(len({a for a, _ in pairs}) == len({b for _, b in pairs}) == len(pairs), 'Original proposal not bijective')
    original_indices = {a: i for i, (a, _) in enumerate(pairs)}
    candidate_indices = {b: i for i, (_, b) in enumerate(pairs)}
    mapping = {}
    for index, original_id, old_id, new_id in CORRECTION:
        state.require(original_indices[original_id] == index and pairs[index] == [original_id, old_id],
                      'Exact old state identity/index mismatch')
        mapping[index] = candidate_indices[new_id]
    state.require(set(mapping) == set(mapping.values()) and len(mapping) == 3, 'Incomplete three-state permutation')
    for suffix in BOUNDARIES:
        name = state.PREFIX+suffix
        state.require(labels['original'][name] == [p[0] for p in pairs]
                      and labels['candidate'][name] == [p[1] for p in pairs], 'Original obligation identity mismatch')
    witnesses = {}
    for family, index in [('qspi', 9982), ('can', 9983), ('uart', 9988)]:
        witnesses[family] = {'original': witness(original, index, family, 'original'),
                             'candidate': witness(candidate, mapping[index], family, 'candidate')}
    fixed, fixed_labels = permute(candidate, labels['candidate'], mapping)
    new_pairs = copy.deepcopy(pairs)
    for index, _, _, new_id in CORRECTION:
        new_pairs[index][1] = new_id
    state.require([a for a, _ in new_pairs] == [a for a, _ in pairs]
                  and sorted(b for _, b in new_pairs) == sorted(b for _, b in pairs), 'State identities not conserved')
    state.require(fixed_labels[state.PREFIX+'ff_state'] == [p[1] for p in new_pairs], 'Corrected identity mismatch')
    receipt = dict(status='UNPROVED_CORRECTED_PROPOSAL', pairs=new_pairs, corrected_positions=sorted(mapping),
                   candidate_old_position_for_new=mapping, direct_mapped_cell_witnesses=witnesses,
                   all_original_state_ids_preserved=True, all_candidate_state_ids_preserved=True,
                   mapped_cells_unchanged=candidate['cells'] == fixed['cells'],
                   candidate_cells_sha256=object_sha(candidate['cells']),
                   original_failed_proposal_sha256=object_sha(proposal),
                   old_failed_proof_preserved=True, equivalence_proved=False)
    return fixed, fixed_labels, receipt


def unconstrained_script(left, right, library, model):
    script = state.miter_script(left, right, library, model)
    state.require(' -set ' not in script and '-set-assumes' not in script
                  and script.count('sat -verify -prove trigger 0 ') == 1, 'Proof is not unconstrained')
    return script


def controls(runtime, library, output):
    tiny = state.fixture()
    tiny['cells']['ff2'] = copy.deepcopy(tiny['cells']['ff0'])
    tiny['cells']['ff2']['connections'].update(Q=[30], D=[31])
    tiny['ports']['third_data'] = dict(direction='input', bits=[31])
    tiny['ports']['third_output'] = dict(direction='output', bits=[30])
    left, _ = state.lift(tiny, ['ff0', 'ff1', 'ff2'])
    old, labels = state.lift(tiny, ['ff2', 'ff0', 'ff1'])
    corrected, _ = permute(old, labels, {0: 1, 1: 2, 2: 0})
    bad_reset = copy.deepcopy(corrected); bad_reset['ports'][state.PREFIX+'ff_reset_b']['bits'][0] = '0'
    left_path = output/'tiny-original.json'; state.common.save(left_path, {'modules': {'soc_top': left}})
    results = {}
    for name, module, expected in [('wrong_three_cycle', old, 'COUNTEREXAMPLE_PRESERVED'),
            ('corrected_three_cycle', corrected, 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS'),
            ('wrong_reset', bad_reset, 'COUNTEREXAMPLE_PRESERVED')]:
        path = output/(name+'.json'); state.common.save(path, {'modules': {'soc_top': module}})
        script = output/(name+'.ys'); script.write_text(unconstrained_script(left_path, path, library, output/(name+'-model')))
        execution = state.execute(runtime, script, output, name, 60)
        verdict = state.outcome(execution['returncode'], (output/(name+'.log')).read_text())
        state.require(verdict == expected, 'Wrong native permutation control outcome')
        if verdict == 'COUNTEREXAMPLE_PRESERVED':
            state.require((output/(name+'-model.json')).is_file() and (output/(name+'-model.vcd')).is_file(),
                          'Missing native negative permutation counterexample')
        results[name] = dict(verdict=verdict, execution=execution)
    return results


def run(output, work):
    state.require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full corrected correspondence proof is cloud-only')
    output, work = state.common.fresh_directory(output), state.common.fresh_directory(work)
    row = dict(status='PREPARING', github_source_commit=os.environ.get('GITHUB_SHA'),
        original_failed_run=replay.SOURCE_RUN, original_failed_commit=replay.SOURCE_COMMIT,
        original_failed_artifact=replay.ARTIFACT_ID, original_failed_proof_preserved=True,
        symbolic_input_bits=10828, compared_output_bits=34321, state_bijection_proved=False,
        candidate_adopted=False, full_soc_functional_accepted=False, timing_accepted=False, manufacturing_approval=False,
        scope='Unconstrained binary storage-boundary equations under the corrected bijection. Equal initial corresponding FF/latch state and identical opaque SRAM behavior are preconditions. No reset reachability, 4-state, CDC, memory internals or physical acceptance.')
    methods = {}; generated = {}
    try:
        state.require(state.common.sha(ROOT/'scripts/prove_alu_mapped_state.py') == replay.STATE_METHOD,
                      'Original state producer changed')
        state.require(state.common.sha(ROOT/'scripts/replay_alu_state_counterexample.py') == REPLAY_SHA,
                      'Original replay producer changed')
        for name in (*state.METHOD_PINS, 'scripts/prove_alu_mapped_state.py', 'scripts/replay_alu_state_counterexample.py', *OWN):
            if name in state.METHOD_PINS:
                state.require(state.common.sha(ROOT/name) == state.METHOD_PINS[name], 'Pinned dependency changed')
            dest = output/'methods'/name; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT/name).read_bytes()); methods[name] = state.archived.pin(dest)
        row['methods'] = methods; state.common.save(output/'result.json', row)
        archive = work/'failed-artifact.zip'; row['archive_download'] = replay.fetch_artifact(archive)
        source = work/'original'; old = replay.restore(archive, source)
        row['original_result_pin'] = replay.MEMBERS['result.json']; row['original_failed_native_proof'] = old['full_proof']
        proposal = json.loads((source/'state-bijection-proposal.json').read_text())
        docs = {tag: json.loads((source/(tag+'-lifted.json')).read_text()) for tag in ('original', 'candidate')}
        modules = {tag: doc['modules']['soc_top'] for tag, doc in docs.items()}
        labels = {tag: json.loads((source/(tag+'-obligations.json')).read_text()) for tag in modules}
        corrected, corrected_labels, correction = corrected_proposal(modules['original'], modules['candidate'], proposal, labels)
        for module in (modules['original'], corrected):
            counts = tuple(sum(len(p['bits']) for p in module['ports'].values() if p['direction'] == d) for d in ('input', 'output'))
            state.require(counts == (10828, 34321), 'Full proof boundary census changed')
        candidate = output/'corrected-candidate-lifted.json'
        corrected_doc = copy.deepcopy(docs['candidate']); corrected_doc['modules']['soc_top'] = corrected
        state.common.save(candidate, corrected_doc)
        state.common.save(output/'corrected-candidate-obligations.json', corrected_labels)
        state.common.save(output/'corrected-state-proposal.json', correction)
        generated = {str(p.relative_to(output)): state.archived.pin(p) for p in
                     (candidate, output/'corrected-candidate-obligations.json', output/'corrected-state-proposal.json')}
        row['corrected_proposal'] = {k: v for k, v in correction.items() if k != 'pairs'}
        # Release Python's two large graph copies before launching the native SAT process.
        del docs, modules, corrected, corrected_doc, module
        lock = state.archived.validate_lock(json.loads((ROOT/state.archived.LOCK).read_text()))
        bundle = work/'library-source'; state.archived.restore(ROOT/lock['archive']['path'], bundle, lock)
        library = bundle/'pdk/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        row['gate_semantics'] = state.validate_gate_liberty(library)
        manifest = state.common.validate_manifest(json.loads((ROOT/state.archived.MANIFEST).read_text()))
        runtime = work/'runtime.AppImage'; state.common.download(manifest['runtime'], runtime); runtime.chmod(0o755)
        row['immutable_inputs'] = dict(liberty=state.archived.pin(library), runtime=state.archived.pin(runtime), archive=replay.ARTIFACT)
        tiny = output/'controls'; tiny.mkdir(); row['controls'] = controls(runtime, library, tiny)
        row['status'] = 'PROVING_ALL_BOUNDARIES'; state.common.save(output/'result.json', row)
        script = output/'corrected-miter.ys'; model = output/'corrected-counterexample'
        script.write_text(unconstrained_script(source/'original-lifted.json', candidate, library, model))
        execution = state.execute(runtime, script, output, 'corrected-miter')
        verdict = state.outcome(execution['returncode'], (output/'corrected-miter.log').read_text())
        if verdict == 'COUNTEREXAMPLE_PRESERVED':
            state.require(model.with_suffix('.json').is_file() and model.with_suffix('.vcd').is_file(), 'Missing new counterexample')
        row.update(status=verdict, native_proof=execution, state_bijection_proved=verdict == 'PROVED_ALL_BINARY_BOUNDARY_EQUATIONS')
        for name, pin in replay.MEMBERS.items(): state.common.verify_file(source/name, pin)
        for name, pin in generated.items(): state.common.verify_file(output/name, pin)
        for name, pin in methods.items(): state.common.verify_file(output/'methods'/name, pin)
        for name, pin in lock['files'].items(): state.common.verify_file(bundle/name, pin)
        state.common.verify_file(runtime, manifest['runtime']); state.common.verify_file(archive, replay.ARTIFACT)
        row['all_input_and_generated_pins_rechecked'] = True
    except BaseException as exc:
        row.update(status='FAILED_OR_INCOMPLETE', error=repr(exc)); raise
    finally:
        row['outputs'] = {str(p.relative_to(output)): state.archived.pin(p) for p in sorted(output.rglob('*'))
                          if p.is_file() and p != output/'result.json'}
        state.common.save(output/'result.json', row)
    state.require(row['state_bijection_proved'], 'New unconstrained proof produced a preserved counterexample')
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args(); print(run(args.output.resolve(), args.work.resolve())['status'])


if __name__ == '__main__': main()
