#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Isolated, source-bound PMP magnitude-comparator candidate and all-output proof.

Changes only two unsigned comparison expressions in the exact C10 PMP source.
No permissions, address masks, state, parameters or default RTL are changed.
Formal scope is all binary inputs at C10's granularity=0, regions=4, channels=3.
Mapped and routed timing and whole-SoC acceptance are separate requirements.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import shutil
import subprocess
import time

SOURCE_SHA = 'f6e1ecd2a4dae38a50585a7735dcd25f015f0a3781d95af36a2e988ec039e4c7'
ANCHOR = '\tgenvar _gv_r_1;\n'
FUNCTION = '''
    // Unsigned most-significant-difference reduction; each level doubles span.
    localparam NSSOC_PMP_WIDTH = 32 - PMPGranularity;
    function automatic nssoc_pmp_gt;
        input [NSSOC_PMP_WIDTH-1:0] left, right;
        reg [NSSOC_PMP_WIDTH-1:0] eq_bits, greater_bits;
        reg [NSSOC_PMP_WIDTH-1:0] next_eq, next_greater;
        integer span, bit_index;
        begin
            eq_bits = ~(left ^ right);
            greater_bits = left & ~right;
            for (span = 1; span < NSSOC_PMP_WIDTH; span = span * 2) begin
                next_eq = eq_bits;
                next_greater = greater_bits;
                for (bit_index = span; bit_index < NSSOC_PMP_WIDTH; bit_index = bit_index + 1) begin
                    next_greater[bit_index] = greater_bits[bit_index] |
                        (eq_bits[bit_index] & greater_bits[bit_index-span]);
                    next_eq[bit_index] = eq_bits[bit_index] & eq_bits[bit_index-span];
                end
                eq_bits = next_eq;
                greater_bits = next_greater;
            end
            nssoc_pmp_gt = greater_bits[NSSOC_PMP_WIDTH-1];
        end
    endfunction
'''


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def transform(raw):
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError('Expected exact C10 generated PMP source')
    text = raw.decode('ascii')
    if text.count(ANCHOR) != 1 or 'nssoc_pmp_gt' in text:
        raise ValueError('Unexpected PMP insertion point')
    edits = []
    for name, operator in [('gt', '>'), ('lt', '<')]:
        pattern = r'(?m)^(\s*assign region_match_' + name + r'\[\(c \* PMPNumRegions\) \+ r\] = )([^\n]+);$'
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            raise ValueError('Expected unique PMP comparison: ' + name)
        match = matches[0]
        parts = match[2].split(' ' + operator + ' ')
        if len(parts) != 2:
            raise ValueError('Unexpected comparison operands')
        left, right = parts if name == 'gt' else reversed(parts)
        replacement = match[1] + f'nssoc_pmp_gt({left}, {right});'
        edits.append(dict(before=match[0], after=replacement))
        text = text[:match.start()] + replacement + text[match.end():]
    text = text.replace(ANCHOR, FUNCTION + ANCHOR)
    # Exact reversal proves the candidate has no hidden source changes.
    restored = text.replace(FUNCTION, '', 1)
    for edit in reversed(edits):
        restored = restored.replace(edit['after'], edit['before'], 1)
    if restored.encode('ascii') != raw:
        raise ValueError('Unexpected source change outside two comparisons')
    return text.encode('ascii'), edits


def prepare(source, output):
    raw = source.read_bytes()
    candidate, edits = transform(raw)
    output.mkdir(parents=True, exist_ok=False)
    (output/'original.v').write_bytes(raw)
    (output/'candidate.v').write_bytes(candidate)
    old = b'nssoc_pmp_gt = greater_bits[NSSOC_PMP_WIDTH-1];'
    if candidate.count(old) != 1:
        raise ValueError('Negative-control target is ambiguous')
    (output/'negative.v').write_bytes(candidate.replace(old, old.replace(b'= ', b'= ~'), 1))
    result = dict(status='PREPARED_NOT_ADOPTED', original_sha256=SOURCE_SHA,
        edits=edits, profile=dict(PMPGranularity=0, PMPNumRegions=4, PMPNumChan=3),
        sources={n:sha(output/n) for n in ('original.v','candidate.v','negative.v')},
        candidate_adopted=False, timing_accepted=False, manufacturing_approval=False)
    (output/'preparation.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def proof_script(directory, variant):
    if variant not in ('candidate','negative'):
        raise ValueError('Unsupported proof variant')
    def load(name, renamed):
        filename = json.dumps(str((directory/(name+'.v')).resolve()))
        return f'''read_verilog {filename}
chparam -set PMPGranularity 0 -set PMPNumRegions 4 -set PMPNumChan 3 ibex_pmp
prep -top ibex_pmp -flatten
rename ibex_pmp {renamed}
design -stash {renamed}
'''
    return load('original','gold') + load(variant,'gate') + '''design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
miter -equiv -flatten gold gate miter
hierarchy -top miter
memory_map
opt_clean
sat -verify -prove trigger 0 -show-inputs -show-outputs -timeout 120
'''


def verify_prepared(directory):
    receipt = json.loads((directory/'preparation.json').read_text())
    candidate, edits = transform((directory/'original.v').read_bytes())
    if (candidate != (directory/'candidate.v').read_bytes() or edits != receipt['edits']
            or receipt['sources'] != {n:sha(directory/n) for n in ('original.v','candidate.v','negative.v')}
            or receipt['profile'] != dict(PMPGranularity=0,PMPNumRegions=4,PMPNumChan=3)):
        raise ValueError('Prepared experiment changed')
    expected = candidate.replace(b'nssoc_pmp_gt = greater_bits[NSSOC_PMP_WIDTH-1];',
                                b'nssoc_pmp_gt = ~greater_bits[NSSOC_PMP_WIDTH-1];', 1)
    if (directory/'negative.v').read_bytes() != expected:
        raise ValueError('Negative control differs')
    return receipt


def prove(directory, command):
    receipt = verify_prepared(directory)
    output = directory/'proof'; output.mkdir(exist_ok=False)
    version = subprocess.check_output([*command,'-V'],text=True).strip()
    executable=Path(shutil.which(command[0]) or command[0]).resolve()
    method_pins={str(Path(__file__).resolve()):sha(__file__),str(executable):sha(executable)}
    result = dict(status='RUNNING',yosys_version=version,profile=receipt['profile'],
        command=command,method_and_executable_sha256=method_pins,
        source_sha256=receipt['sources'],cases=[],candidate_adopted=False,
        timing_accepted=False,manufacturing_approval=False)
    def save():
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def limit():
        resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    try:
        save()
        for variant in ('candidate','negative'):
            script=output/(variant+'.ys'); script.write_text(proof_script(directory,variant))
            start=time.monotonic()
            with (output/(variant+'.log')).open('x') as log:
                process=subprocess.run([*command,'-Q','-T','-s',str(script.resolve())],
                    stdout=log,stderr=subprocess.STDOUT,timeout=180,preexec_fn=limit)
            text=(output/(variant+'.log')).read_text()
            result['cases'].append(dict(name=variant,returncode=process.returncode,
                elapsed_seconds=time.monotonic()-start,script_sha256=sha(script),
                log_sha256=sha(output/(variant+'.log'))));save()
            verify_prepared(directory)
            if any(sha(path)!=digest for path,digest in method_pins.items()):
                raise ValueError('Proof method or executable changed during execution')
            if variant=='candidate':
                passed=process.returncode==0 and 'SAT proof finished - no model found: SUCCESS!' in text
            else:
                passed=process.returncode!=0 and 'proof did fail' in text
            if not passed: raise ValueError('Unexpected formal result: '+variant)
        result['status']='PASS_ALL_PMP_OUTPUTS_AND_REJECT_WRONG_COMPARISON'
        result['scope']='All binary inputs at the unchanged C10 PMP profile; no internal-name matching, assumptions, permissions changes, timing or physical acceptance.'
    except BaseException as exc:
        result.update(status='ERROR_OR_INCOMPLETE_PROOF',error=str(exc));raise
    finally:
        save()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='mode',required=True)
    p=sub.add_parser('prepare');p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('prove');p.add_argument('--directory',type=Path,required=True);p.add_argument('--command',nargs='+',required=True)
    args=parser.parse_args()
    result=prepare(args.source,args.output) if args.mode=='prepare' else prove(args.directory,args.command)
    print(result['status'])


if __name__=='__main__': main()
