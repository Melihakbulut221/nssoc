#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run the real descriptor tests, then require functional failures in RTL mutants."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from cocotb_results import count_results

ROOT = Path(__file__).resolve().parents[1]
RTL = 'hw/soc/rtl/pcie/soc_pcie_tlp_regs.v'
BENCH = ROOT/'hw/soc/tb/cocotb'
MUTATIONS = {
    'zero_length_count': ('dw1[15:8],1,addr[6:0]);', 'dw1[15:8],4,addr[6:0]);'),
    'bar_decode': ('wire target_ok=addr[31:12]==bar0[31:12]',
                   "wire target_ok=1'b1"),
    'byte_strobes': ("pstrb_o<=has_data ? first_be : 4'b0;",
                     "pstrb_o<=has_data ? 4'hf : 4'b0;"),
    'abort_status': ('complete(3\'d4,0,0,completer,requester,tag,0,0);',
                     'complete(3\'d1,0,0,completer,requester,tag,0,0);'),
    'completion_tag': ('cid,status,1\'b0,bytes_left,rid,req_tag,1\'b0,low_addr,32\'b0}',
                       'cid,status,1\'b0,bytes_left,rid,8\'b0,1\'b0,low_addr,32\'b0}'),
}
STREAM_MUTATIONS = {
    'header_width': ('header_size<=rx_data_i[29] ? 4 : 3;', 'header_size<=3;'),
    'actual_payload_count': ("payload_count<=payload_count+1'b1;", 'payload_count<=1;'),
    'integrity_error': ('end else if (rx_error_i) begin', "end else if (1'b0) begin"),
    'early_submission': ('if (rx_eop_i) state<=SUBMIT;', 'state<=SUBMIT;'),
    'output_backpressure': ('end else if (tx_busy && tx_ready_i) begin', 'end else if (tx_busy) begin'),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--top', choices=('soc_pcie_tlp_regs', 'soc_pcie_tlp_stream'), default='soc_pcie_tlp_regs')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or not out.is_relative_to(ROOT/'hw/soc/out'):
        parser.error('Use a fresh output directory below hw/soc/out')
    out.mkdir(parents=True)
    rtl_path = ROOT/f'hw/soc/rtl/pcie/{args.top}.v'
    files = [rtl_path, BENCH/f'test_{args.top}.py',
             BENCH/f'Makefile.{args.top}', Path(__file__).resolve(),
             ROOT/'scripts/cocotb_results.py']
    is_stream = args.top == 'soc_pcie_tlp_stream'
    if is_stream:
        files.append(ROOT/RTL)
    original = {str(p.relative_to(ROOT)): sha(p) for p in files}
    record = {'status': 'FAIL', 'top': args.top, 'scope': 'Transaction-layer RTL controls, no link or PHY',
              'inputs': original, 'runs': {}}
    source = rtl_path.read_text()
    mutations = STREAM_MUTATIONS if is_stream else MUTATIONS
    try:
        for name, mutation in [('baseline', None), ('timeout_1', None), ('timeout_256', None), *mutations.items()]:
            target = out/name
            target.mkdir()
            text = source
            if mutation:
                assert text.count(mutation[0]) == 1, 'Mutation location drifted: '+name
                text = text.replace(*mutation)
            rtl = target/f'{args.top}.v'
            rtl.write_text(text)
            xml = target/'results.xml'
            command = ['make', '-C', str(BENCH), '-f', 'Makefile.'+args.top,
                       'VERILOG_SOURCES='+str(rtl)+(' '+str(ROOT/RTL) if is_stream else ''), 'SIM_BUILD='+str(target/'sim'),
                       'COCOTB_RESULTS_FILE='+str(xml),
                       'PCIE_APB_TIMEOUT='+({'timeout_1': '1', 'timeout_256': '256'}.get(name, '8'))]
            log = target/'driver.log'
            with log.open('x') as stream:
                result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=60)
            counts = count_results([xml])
            if mutation is None:
                assert result.returncode == 0 and counts == (6, 0, 0), 'Baseline not clean'
            else:
                assert sum(counts) == 6 and counts[1] > 0 and counts[2] == 0, 'No functional counterexample: '+name
                assert 'AssertionError' in log.read_text(), 'Not a functional assertion failure: '+name
            record['runs'][name] = {'counts': counts, 'returncode': result.returncode,
                                   'log_sha256': sha(log), 'xml_sha256': sha(xml),
                                   'rtl_sha256': sha(rtl)}
        assert original == {str(p.relative_to(ROOT)): sha(p) for p in files}, 'Inputs changed'
        record['status'] = 'PASS'
    except (AssertionError, OSError, ValueError, subprocess.SubprocessError) as error:
        record['error'] = str(error)
    (out/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    print(record['status'], 'three timeout baselines and five functional mutation controls')
    return int(record['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
