#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only diagnostic replay of one failed, unchanged mapped-state relation.

The original unconstrained proof remains failed. This fixes every input to its
preserved binary counterexample solely to expose the differing boundary bits.
No state pairing, graph, constraint in the original proof, or default RTL is
changed, and this diagnostic cannot establish equivalence or adoption.
"""
import argparse
import json
import os
from pathlib import Path
import zipfile

import prove_alu_mapped_state as state

ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = '166bd17a338b67b1359e69a463f3bd620d316b0f'
SOURCE_RUN = 37003975081
ARTIFACT_ID = 11224653850
ARTIFACT = dict(bytes=10538738, sha256='8a90ec932cd6f4bfd04b49b40c33f44ad123f703673cb779977b4de74a90cb5a',
    url='https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/closure-alu-state-failure-37003975081-20261002.zip')
STATE_METHOD = '4ea03404cd11bdeda05dc018c8b9b4032f8622754f15dca7b6faef4b6d922335'
MEMBERS = {
    'result.json': dict(bytes=18113, sha256='1b0860a7a0ca2e3aef64a6cbb3c2714c34ee97b9f19865572a00d38e8ac2341a'),
    'original-lifted.json': dict(bytes=62328955, sha256='86f311ceb14b05dd0f8341587fb8b248e97e8bb496c29cfe1e750b7c8d27b64f'),
    'candidate-lifted.json': dict(bytes=62840132, sha256='9634ed9aded3bbdec25af332b31da9432069c1059c4d416a991787d71a3d74b8'),
    'original-obligations.json': dict(bytes=1089942, sha256='8bef55772abce630e5c62052e047f7f240f779323648974b5d2fb8f7da1ad307'),
    'candidate-obligations.json': dict(bytes=1089942, sha256='5afdd42515ef1e8ed0eb095f601f3ab143f9787e6a96e41f238752c7205864b1'),
    'full-counterexample.json': dict(bytes=12168, sha256='5d7c6fee0450d4ae83f3440b6e4e198425dd0d29e549f359bb72f6e7478e8789'),
    'full-miter.log': dict(bytes=319559, sha256='b151fc08c41dee095102b0a76330548dcd85bc5fff887b2180f3ddcc255a1300'),
    'full-miter.ys': dict(bytes=1127, sha256='729672a08ee0ac3eda576054b60426b556a9334aeeb6b16da75c59d5b542e733'),
    'full-miter-execution.json': dict(bytes=480, sha256='7b1ffa20576849409ad51d262a3f4ffd69d0bb0a83bcfd500dcc1221a8e214d8'),
    'state-bijection-proposal.json': dict(bytes=480630, sha256='70adfc6592ef7b728eaa0a5fbfa3a29162adfdf86350ccc36afca80d0a843deb'),
}
OWN = ('scripts/replay_alu_state_counterexample.py', 'sw/tests/test_alu_state_counterexample.py',
       '.github/workflows/timing-alu-state-replay.yml')


def wave_values(model):
    values = {}
    for signal in model['signal']:
        name = signal['name']
        state.require(name not in values, 'Duplicate model signal')
        data = signal.get('data')
        if data:
            value = data[0]
        else:
            value = signal['wave'][0]
        state.require(isinstance(value, str) and value and set(value) <= {'0','1'}, 'Nonbinary/empty model signal')
        values[name] = value
    return values


def assignments(model, module):
    values = wave_values(model)
    expected = {'in_'+name: len(port['bits']) for name, port in module['ports'].items() if port['direction']=='input'}
    actual = {name: value for name, value in values.items() if name.startswith('in_')}
    state.require(actual.keys() == expected.keys() and all(len(actual[name]) == width for name, width in expected.items()),
                  'Counterexample does not assign every input exactly at declared width')
    state.require(values.get('trigger') == '1', 'Original counterexample trigger is not one')
    state.require(all(name.startswith('in_') or name=='trigger' for name in values), 'Unexpected original model signal')
    return actual


def replay_script(left, right, library, model, fixed):
    script = state.miter_script(left, right, library, model, 60)
    old = 'miter -equiv -flatten gold gate miter\n'
    state.require(script.count(old)==1, 'Original miter interface changed')
    script = script.replace(old, 'miter -equiv -make_outputs -make_outcmp -flatten gold gate miter\n')
    for name, value in fixed.items():
        state.require(name.startswith('in_') and all(c.isalnum() or c=='_' for c in name)
                      and value and set(value)<={'0','1'}, 'Unsafe/nonbinary fixed model assignment')
    settings = ' '.join(f"-set {name} {len(value)}'b{value}" for name, value in sorted(fixed.items()))
    script = script.replace('sat -verify -prove trigger 0 ', 'sat -verify -prove trigger 0 '+settings+' ', 1)
    return script


def differences(model, left, right, fixed, meanings):
    values = wave_values(model)
    state.require(values.get('trigger')=='1', 'Preserved counterexample no longer triggers')
    for name, value in fixed.items():
        state.require(values.get(name)==value, 'Replay input differs from original counterexample')
    actual_inputs = {name for name in values if name.startswith('in_')}
    state.require(actual_inputs==fixed.keys(), 'Replay added/omitted an input')
    outputs = {name:len(port['bits']) for name,port in left['ports'].items() if port['direction']=='output'}
    state.require(outputs=={name:len(port['bits']) for name,port in right['ports'].items() if port['direction']=='output'},
                  'Changed lifted interface')
    expected_names = {'trigger', *fixed}
    rows = []; groups = {}
    for name, width in outputs.items():
        expected_names.update(prefix+name for prefix in ('gold_', 'gate_', 'cmp_'))
        gold, gate, cmp = (values.get(prefix+name) for prefix in ('gold_', 'gate_', 'cmp_'))
        state.require(gold is not None and gate is not None and len(gold)==len(gate)==width,
                      'Missing/incorrect full compared output width')
        state.require(cmp==str(int(gold==gate)), 'Native comparison signal disagrees with compared vectors')
        for bit, (a,b) in enumerate(zip(reversed(gold),reversed(gate))):
            if a==b: continue
            row = dict(port=name, bit=bit, original=int(a), candidate=int(b))
            for tag in ('original','candidate'):
                if name in meanings[tag]:
                    state.require(len(meanings[tag][name])==width, 'Obligation label count differs')
                    row[tag+'_boundary'] = meanings[tag][name][bit]
            rows.append(row); groups[name]=groups.get(name,0)+1
    state.require(set(values)==expected_names and rows, 'Incomplete/extra replay output set or no difference')
    return dict(compared_bits=sum(outputs.values()), differing_bits=len(rows), by_port=groups, differences=rows)


def fetch_artifact(output):
    """The permanent public mirror contains the unchanged failed artifact bytes."""
    state.common.download(ARTIFACT, output)
    return dict(ARTIFACT, source_run=SOURCE_RUN, source_commit=SOURCE_COMMIT,
                original_artifact_id=ARTIFACT_ID, source_kind='permanent_public_release')


def restore(archive, output):
    state.common.verify_file(archive, ARTIFACT)
    output.mkdir()
    with zipfile.ZipFile(archive) as source:
        state.require(len(source.namelist())==len(set(source.namelist())), 'Duplicate source artifact member')
        for name, pin in MEMBERS.items():
            item = source.getinfo(name)
            state.require(item.file_size==pin['bytes'], 'Changed source member size')
            path = output/name
            with source.open(item) as stream, path.open('xb') as target:
                while block := stream.read(1024**2): target.write(block)
            state.common.verify_file(path, pin)
    result = json.loads((output/'result.json').read_text())
    state.require(result['github_source_commit']==SOURCE_COMMIT and result['status']=='COUNTEREXAMPLE_PRESERVED'
                  and result['state_bijection_proved'] is False and result['all_input_pins_rechecked'] is True,
                  'Original failed verdict changed')
    state.require(result['symbolic_input_bits']==10828 and result['compared_output_bits']==34321,
                  'Original boundary census changed')
    for name,pin in MEMBERS.items():
        if name!='result.json': state.require(result['outputs'][name]==pin, 'Original captured member differs')
    return result


def run(output, work):
    state.require(os.environ.get('GITHUB_ACTIONS')=='true', 'Full counterexample replay is cloud-only')
    output, work = state.common.fresh_directory(output), state.common.fresh_directory(work)
    row = dict(status='PREPARING_DIAGNOSTIC', github_source_commit=os.environ.get('GITHUB_SHA'),
        original_source_commit=SOURCE_COMMIT, original_run=SOURCE_RUN, original_artifact=ARTIFACT_ID,
        original_unconstrained_proof_status='COUNTEREXAMPLE_PRESERVED', fixed_assignment_for_diagnosis_only=True,
        state_mapping_changed=False, source_graphs_changed=False, candidate_adopted=False,
        equivalence_proved=False, full_soc_functional_accepted=False, timing_accepted=False, manufacturing_approval=False)
    inputs = {}; methods = {}
    try:
        state.require(state.common.sha(ROOT/'scripts/prove_alu_mapped_state.py')==STATE_METHOD, 'Original state method changed')
        for name in (*state.METHOD_PINS, 'scripts/prove_alu_mapped_state.py', *OWN):
            if name in state.METHOD_PINS:
                state.require(state.common.sha(ROOT/name)==state.METHOD_PINS[name], 'Pinned dependency changed')
            dest = output/'methods'/name; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT/name).read_bytes()); methods[name]=state.archived.pin(dest)
        row['methods']=methods; state.common.save(output/'result.json',row)
        archive = work/'failed-artifact.zip'; row['archive_download']=fetch_artifact(archive)
        source = work/'original'; old = restore(archive,source)
        row['original_result_pin']=MEMBERS['result.json']; row['original_full_proof']=old['full_proof']
        lock = state.archived.validate_lock(json.loads((ROOT/state.archived.LOCK).read_text()))
        bundle = work/'library-source'; state.archived.restore(ROOT/lock['archive']['path'],bundle,lock)
        library = bundle/'pdk/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
        state.validate_gate_liberty(library)
        manifest = state.common.validate_manifest(json.loads((ROOT/state.archived.MANIFEST).read_text()))
        runtime = work/'runtime.AppImage'; state.common.download(manifest['runtime'],runtime); runtime.chmod(0o755)
        inputs = {name:state.archived.pin(path) for name,path in [('liberty',library),('runtime',runtime),('artifact',archive)]}
        modules = {tag:json.loads((source/(tag+'-lifted.json')).read_text())['modules']['soc_top'] for tag in ('original','candidate')}
        model = json.loads((source/'full-counterexample.json').read_text())
        fixed = assignments(model,modules['original'])
        state.require(fixed==assignments(model,modules['candidate']) and sum(map(len,fixed.values()))==10828,
                      'Changed counterexample input boundary')
        state.common.save(output/'fixed-inputs.json',fixed)
        script = output/'replay.ys'; replay_model = output/'replay-model'
        script.write_text(replay_script(source/'original-lifted.json',source/'candidate-lifted.json',library,replay_model,fixed))
        execution = state.execute(runtime,script,output,'replay',600)
        state.require(state.outcome(execution['returncode'],(output/'replay.log').read_text())=='COUNTEREXAMPLE_PRESERVED',
                      'Exact original counterexample did not reproduce')
        replay = json.loads(replay_model.with_suffix('.json').read_text())
        meanings = {tag:json.loads((source/(tag+'-obligations.json')).read_text()) for tag in modules}
        report = differences(replay,modules['original'],modules['candidate'],fixed,meanings)
        state.require(report['compared_bits']==34321,'Incomplete full boundary replay')
        state.common.save(output/'differences.json',report)
        for name,pin in MEMBERS.items(): state.common.verify_file(source/name,pin)
        for name,expected in inputs.items():
            state.common.verify_file({'liberty':library,'runtime':runtime,'artifact':archive}[name],expected)
        for name,expected in lock['files'].items(): state.common.verify_file(bundle/name,expected)
        for name,expected in methods.items(): state.common.verify_file(output/'methods'/name,expected)
        row.update(status='DIAGNOSTIC_REPLAY_REPRODUCED_FAILED_RELATION',execution=execution,
                   input_bits=10828,compared_output_bits=34321,differing_bits=report['differing_bits'],
                   differences_by_port=report['by_port'],all_pins_rechecked=True)
    except BaseException as exc:
        row.update(status='DIAGNOSTIC_FAILED_OR_INCOMPLETE',error=repr(exc)); raise
    finally:
        row['immutable_inputs']=inputs
        row['outputs']={str(p.relative_to(output)):state.archived.pin(p) for p in sorted(output.rglob('*'))
                        if p.is_file() and p != output/'result.json'}
        state.common.save(output/'result.json',row)
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args();print(run(args.output.resolve(),args.work.resolve())['status'])


if __name__=='__main__':main()
