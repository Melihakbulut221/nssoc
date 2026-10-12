#!/usr/bin/env python3
"""Reproduce the isolated ACK candidate proof and port tests on hosted CI."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-ack-result'
CAPSULE = ROOT / 'docs/evidence/pcie-ack-delta-candidate-methods-20261012.tar.gz'
DIGEST = '41702ae4f4eed01b2571543f573501159f2a22fbcbd0068d7c109b630e818f7b'
PREFIX = 'hw/soc/out/pcie-ack-delta-lookahead-20261012/'


def main():
    OUT.mkdir(exist_ok=False)
    record = dict(status='RUNNING', adopted=False, proof=[], tests=[],
                  scope='Combinational identity and isolated port tests only; no timing, routing, PHY or chip closure.')
    def save():
        (OUT / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    save()
    try:
        assert hashlib.sha256(CAPSULE.read_bytes()).hexdigest() == DIGEST
        candidate = OUT / 'input'
        with tarfile.open(CAPSULE) as tar:
            for member in tar:
                if not member.name.startswith(PREFIX):
                    raise ValueError('Unexpected capsule prefix')
                relative = Path(member.name.removeprefix(PREFIX))
                if relative.is_absolute() or '..' in relative.parts or not member.isfile():
                    raise ValueError('Unsafe capsule member')
                target = candidate / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(member).read())
        record['capsule_sha256'] = DIGEST
        # Bind standalone miter to the exact expression used in candidate RTL.
        rtl = (candidate / 'candidate01/soc_pcie_replay_tx.v').read_text()
        miter = (candidate / 'miter01.v').read_text()
        expression = miter[miter.index('    // Independent'):miter.index(' assign ok=')]
        assert expression in rtl
        yosys = shutil.which('yosys')
        assert yosys
        for name in ('miter', 'carry4_zero', 'carry8_zero'):
            script = OUT / (name + '.ys')
            script.write_text(f'read_verilog -sv {candidate / (name + "01.v")}\nprep -top ack_delta_miter -flatten\nsat -prove ok 1 -verify -show-inputs -show-outputs\n')
            log = OUT / (name + '.log')
            with log.open('w') as stream:
                rc = subprocess.call([yosys, '-s', str(script)], stdout=stream, stderr=subprocess.STDOUT)
            text = log.read_text()
            assert (rc == 0 and 'SUCCESS!' in text) if name == 'miter' else (rc != 0 and 'proof did fail' in text)
            record['proof'].append(dict(name=name, returncode=rc, expected_proof=name == 'miter'))
            save()
        for top in ('soc_pcie_replay_tx', 'soc_pcie_reliable_packets'):
            output = OUT / top
            command = [sys.executable, str(ROOT / 'scripts/check_pcie_replay.py'), '--top', top,
                       '--out', str(output), '--rtl-dir', str(candidate / 'candidate01'),
                       '--iverilog-dir', str(Path(shutil.which('iverilog')).parent)]
            with (OUT / (top + '.log')).open('w') as log:
                rc = subprocess.call(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            result = json.loads((output / 'result.json').read_text())
            record['tests'].append(dict(top=top, returncode=rc, result=result))
            save()
            assert rc == 0 and result['status'] == 'PASS_PORT_ONLY_PCIE_REPLAY'
            assert result['tests']['passed'] == result['expected_tests'] > 0
            assert result['tests']['failed'] == result['tests']['skipped'] == 0
        record['status'] = 'PASS_PROOF_AND_REPLAY_PORTS_NOT_PHYSICAL_CLOSURE'
    except BaseException as error:
        record['status'] = 'FAIL_OR_ERROR'
        record['error'] = repr(error)
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
