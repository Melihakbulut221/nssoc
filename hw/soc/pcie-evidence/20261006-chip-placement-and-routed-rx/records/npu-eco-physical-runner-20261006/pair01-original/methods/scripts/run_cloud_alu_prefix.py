#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh ALU proof and opt-in matched current-C10-profile synthesis on cloud.

The proof changes one combinational addition and adds no state or latency.
Synthesis remains a separate measurement: no native boot, physical timing or
whole-chip equivalence acceptance is inherited from the historical experiment.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile

sys.dont_write_bytecode = True
import bootstrap_oss
import prepare_alu_prefix as prefix
import run_cloud_timing_experiment as common

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'hw/soc/pnr/alu-prefix-c10-input.lock.json'
MANIFEST = 'docs/evidence/timing-cloud-input-20260930.json'
PROFILE = dict(CORE_REQ_REG=1, CORE_WB_STAGE=1, SYNPRE=1, MEM_RDREG=1, REQ_REG=1, WAKE_GNT=1)
SOURCES = ('scripts/run_cloud_alu_prefix.py', 'scripts/prepare_alu_prefix.py',
           'scripts/run_cloud_timing_experiment.py', 'scripts/bootstrap_oss.py', LOCK, MANIFEST,
           '.github/workflows/timing-alu-prefix.yml')


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(path):
    return dict(bytes=path.stat().st_size, sha256=common.sha(path))


def validate_lock(lock):
    require(lock.get('schema') == 1 and lock.get('source_parameters') == PROFILE, 'C10 profile changed')
    for name, entry in lock['files'].items():
        common.safe_relative(name)
        common.pin(entry)
    require(lock['files'][lock['original_alu']]['sha256'] == prefix.ORIGINAL_SHA, 'C10 ALU source changed')
    common.safe_relative(lock['archive']['path'])
    common.pin(lock['archive'])
    for name, entry in lock['tracked_sources'].items():
        common.safe_relative(name)
        require(lock['files']['repo/'+name] == entry, 'Tracked source pin differs from snapshot')
    return lock


def restore(archive, directory, lock):
    common.verify_file(archive, lock['archive'])
    directory.mkdir()
    seen = set()
    with tarfile.open(archive, 'r:xz') as incoming:
        for member in incoming:
            name = str(common.safe_relative(member.name))
            require(member.isfile() and not member.issparse() and name in lock['files']
                    and name not in seen and member.size == lock['files'][name]['bytes'], 'Unsafe snapshot member')
            p = directory/name
            p.parent.mkdir(parents=True, exist_ok=True)
            with incoming.extractfile(member) as source, p.open('xb') as sink:
                shutil.copyfileobj(source, sink)
            common.verify_file(p, lock['files'][name])
            p.chmod(0o444)
            seen.add(name)
    require(seen == set(lock['files']), 'Incomplete source snapshot')
    receipt = json.loads((directory/'recipe/c10-source-receipt.json').read_text())
    require(receipt['source_parameters'] == PROFILE and
            common.sha(directory/'recipe/c10-source-receipt.json') == lock['source_receipt_sha256'],
            'Snapshot C10 synthesis receipt differs')
    for name, entry in lock['origins'].items():
        require(receipt['input_sha256'][entry['original']] == lock['files'][name]['sha256'],
                'Snapshot no longer matches original C10 synthesis input')
    require(common.sha(directory/'recipe/c10.ys') == receipt['output_sha256'][
            lock['original_synthesis']+'/soc_top_syn.ys'], 'Original C10 recipe differs')
    require(lock['baseline_netlist_sha256'] == receipt['output_sha256'][
            lock['original_synthesis']+'/soc_top.netlist.v'], 'Baseline netlist identity differs')


def synthesis_recipe(template, bundle, output, alu, lock):
    """Only relocate paths and, for the candidate, substitute one ALU source."""
    original_input = lock['original_repo']+'/hw/soc/gen/ibex_alu.v'
    require(template.count(original_input) == 1, 'ALU source selection is ambiguous')
    for name, value in PROFILE.items():
        module = 'ibex_register_file_ff' if name == 'SYNPRE' else 'soc_top'
        require(template.splitlines().count(f'chparam -set {name} {value} {module}') == 1,
                'Synthesis parameter differs: '+name)
    require('SOC_LGPL_INTERFACES' in template and 'SOC_SRAM_MBIST' in template
            and 'SOC_ETH_MBIST' in template, 'Full-interface/MBIST profile missing')
    replacements = {original_input: str(alu), lock['original_synthesis']: str(output),
                    lock['original_repo']: str(bundle/'repo'), lock['original_pdk']: str(bundle/'pdk')}
    # Substitute once, longest prefix first. A destination beneath the historical
    # checkout must never itself be interpreted as another old input prefix.
    pattern = '|'.join(re.escape(p) for p in sorted(replacements, key=len, reverse=True))
    text = re.sub(pattern, lambda match: replacements[match.group()], template)
    require('abc -liberty ' in text and ' -D 20\n' in text, 'Original ABC target changed')
    return text


def validate_recipe_inputs(recipe, bundle, output, alu):
    """All read inputs must exist in the immutable snapshot or prepared outputs."""
    roots = [bundle.resolve(), output.resolve(), alu.parent.resolve()]
    inputs = []
    for line in recipe.splitlines():
        if not line.startswith(('read_verilog ', 'read_liberty ')):
            continue
        for token in shlex.split(line)[1:]:
            if token.startswith('-I'):
                path = Path(token[2:]).resolve()
                require(path.is_dir() and any(path.is_relative_to(r) for r in roots),
                        'Missing or escaped synthesis include directory')
            elif not token.startswith('-'):
                path = Path(token).resolve()
                require(path.is_file() and any(path.is_relative_to(r) for r in roots),
                        'Missing or escaped synthesis input: '+token)
                inputs.append(path)
    require(inputs.count(alu.resolve()) == 1, 'Recipe must select exactly one prepared ALU')
    return {str(p): pin(p) for p in inputs}


def execute(command, output, name):
    env = os.environ.copy()
    for key in ('PYTHONPATH', 'PYTHONHOME', 'GH_TOKEN', 'GITHUB_TOKEN'):
        env.pop(key, None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    with (output/(name+'.log')).open('w') as stream:
        result = subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT,
                                env=env, stdin=subprocess.DEVNULL, check=False)
    row = dict(command=list(map(str, command)), returncode=result.returncode)
    common.save(output/(name+'-execution.json'), row)
    return row


def validate_proof_log(code, text, negative=False):
    if negative:
        require(code != 0 and 'proof did fail' in text, 'Wrong-sum negative control did not produce a real counterexample')
    else:
        require(code == 0 and 'SAT proof finished - no model found: SUCCESS!' in text,
                'Complete ALU all-output proof failed/incomplete')


def run(phase, output, work):
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Native ALU and SoC work is cloud-only')
    output, work = common.fresh_directory(output), common.fresh_directory(work)
    row = dict(schema=1, status='PREPARING', phase_requested=phase,
               github_source_commit=os.environ.get('GITHUB_SHA'), candidate_adopted=False,
               timing_accepted=False, manufacturing_approval=False, full_soc_functional_accepted=False,
               caveat='Historical original RTL-to-mapped comparison has an unconstrained unique-case '
                      'overlapping-control counterexample. This fresh original-vs-prefix all-output '
                      'proof does not erase it or establish full-SoC mapped equivalence.')
    common.save(output/'result.json', row)
    try:
        methods = {}
        for name in SOURCES:
            target = output/'methods'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, target)
            methods[name] = pin(target)
        lock = validate_lock(json.loads((output/'methods'/LOCK).read_text()))
        manifest = common.validate_manifest(json.loads((output/'methods'/MANIFEST).read_text()))
        require(common.sha(output/'methods'/MANIFEST) == lock['c10_manifest_sha256'], 'C10 physical input identity differs')
        for name, expected in lock['tracked_sources'].items():
            common.verify_file(ROOT/name, expected)
        row.update(methods=methods, profile=PROFILE, current_tracked_sources_verified=lock['tracked_sources'],
                   source_snapshot=lock['archive'])
        bundle = work/'inputs'
        restore(ROOT/lock['archive']['path'], bundle, lock)
        original = bundle/lock['original_alu']
        candidate, negative = prefix.prepare(original.read_bytes())
        prepared = output/'prepared'
        prepared.mkdir()
        for name, data in [('original', original.read_bytes()), ('candidate', candidate), ('negative', negative)]:
            (prepared/(name+'.v')).write_bytes(data)
        runtime = work/'runtime.AppImage'
        common.download(manifest['runtime'], runtime)
        runtime.chmod(0o755)
        version = execute([runtime, 'yosys', '-V'], output, 'proof-runtime-version')
        require(version['returncode'] == 0 and 'Yosys 0.62 ' in
                (output/'proof-runtime-version.log').read_text(), 'Unexpected proof Yosys runtime')
        row.update(status='PROVING_COMPLETE_ALU', runtime=manifest['runtime'], proof_cases=[])
        common.save(output/'result.json', row)
        for name in ('candidate', 'negative'):
            script = output/(name+'-proof.ys')
            script.write_text(prefix.miter(prepared/'original.v', prepared/(name+'.v')))
            execution = execute([runtime, 'yosys', '-Q', '-T', '-s', script], output, name+'-proof')
            text = (output/(name+'-proof.log')).read_text()
            validate_proof_log(execution['returncode'], text, name == 'negative')
            row['proof_cases'].append(dict(name=name, **execution, log=pin(output/(name+'-proof.log'))))
            common.save(output/'result.json', row)
        row['status'] = 'PASS_WHOLE_ALU_RTL_AND_WRONG_SUM_REJECTED'
        if phase == 'synthesis':
            row['status'] = 'SYNTHESIZING_MATCHED_C10_PROFILE'
            common.save(output/'result.json', row)
            toolroot = bootstrap_oss.install(work/'oss-cad-suite')
            yosys = toolroot/'bin/yosys'
            require(common.sha(yosys) == lock['synthesis_yosys_sha256'], 'Synthesis Yosys differs from C10')
            row['synthesis_runtime'] = dict(archive_sha256=bootstrap_oss.ARCHIVE_SHA256,
                archive_bytes=bootstrap_oss.ARCHIVE_SIZE, url=bootstrap_oss.URL, yosys=pin(yosys),
                version=subprocess.check_output([str(yosys), '-V'], text=True).strip())
            require('Yosys 0.67+146 ' in row['synthesis_runtime']['version'], 'Unexpected synthesis Yosys version')
            row['synthesis'] = {}
            original_output_relative = Path(lock['original_synthesis']).relative_to(lock['original_repo'])
            for name in ('original', 'candidate'):
                directory = output/('synthesis-'+name)
                directory.mkdir()
                shutil.copytree(bundle/'repo'/original_output_relative/'boot-rom', directory/'boot-rom')
                shutil.copyfile(bundle/'repo'/original_output_relative/'abc.constr', directory/'abc.constr')
                script = directory/'synthesis.ys'
                script.write_text(synthesis_recipe((bundle/'recipe/c10.ys').read_text(), bundle,
                                                    directory, prepared/(name+'.v'), lock))
                common.save(directory/'read-inputs.json', validate_recipe_inputs(
                    script.read_text(), bundle, directory, prepared/(name+'.v')))
                result = execute([yosys, '-s', script], directory, 'synthesis')
                require(result['returncode'] == 0, 'Current-profile '+name+' synthesis failed')
                netlist = directory/'soc_top.netlist.v'
                require(netlist.is_file() and netlist.stat().st_size > 1_000_000, 'Missing full-core synthesized netlist')
                if name == 'original':
                    row['baseline_reproduction'] = dict(observed=pin(netlist),
                        expected_sha256=lock['baseline_netlist_sha256'],
                        scope='Exact emitted bytes required. Path relocation could alter emitted bytes '
                              'independently of function; a mismatch is preserved for diagnosis '
                              'and is never accepted automatically.')
                    common.save(output/'result.json', row)
                    require(common.sha(netlist) == lock['baseline_netlist_sha256'],
                            'Relocated baseline did not reproduce C10 synthesis byte-for-byte')
                row['synthesis'][name] = dict(execution=result, netlist=pin(netlist),
                                              recipe=pin(script), area_report=pin(directory/'area.rpt'))
                common.save(output/'result.json', row)
            row['status'] = 'MATCHED_C10_SYNTHESIS_COMPLETE_REQUIRES_FUNCTIONAL_AND_PHYSICAL_PROOF'
        common.verify_file(runtime, manifest['runtime'])
        for name, entry in lock['files'].items():
            common.verify_file(bundle/name, entry)
        for name, entry in methods.items():
            common.verify_file(output/'methods'/name, entry)
        row['next_required'] = ['Fresh current-profile native full-interface boot/MBIST',
            'Mapped original-versus-prefix functional correspondence', 'Independent SRAM replacement mapping',
            'Fresh physical placement/routing and all-corner timing, RC, DRC/LVS']
    except Exception as error:
        row.update(status='FAILED_PRESERVED', error=f'{type(error).__name__}: {error}')
        raise
    finally:
        row['outputs'] = {str(p.relative_to(output)): pin(p) for p in sorted(output.rglob('*'))
                          if p.is_file() and p != output/'result.json'}
        common.save(output/'result.json', row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('proof', 'synthesis'), default='proof')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    run(args.phase, args.output.resolve(), args.work.resolve())


if __name__ == '__main__':
    main()
