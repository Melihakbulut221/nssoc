# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real serial traffic and unchanged procedural fault decisions for V30."""
from pathlib import Path
import json
import re
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT/'hw/soc/rtl/pcie'
EXPRESSION = '(token_failures[0]|token_failures[1])|\n                    (token_failures[2]|token_failures[3])'
FAULTS = {
    'require_all_words_bad': ('&token_failures','malformed_tokens_and_headers_never_release_quarantine'),
    'ignore_first_three': ('token_failures[3]','malformed_tokens_and_headers_never_release_quarantine'),
    'reject_good_words': ('(|token_failures) | (|control_active)','sustained_minimum_packets_exceed_every_buffer'),
}


def prepare(directory, fault=None):
    base = runpy.run_path(str(ROOT/'sw/tests/test_pcie_gen3_integrity_v28_payload.py'))
    base['prepare'](directory)
    s = (RTL/'soc_pcie_gen3_framer_rx_integrity_v30.v').read_text()
    assert s.count(EXPRESSION) == 1
    if fault:
        s = s.replace(EXPRESSION,FAULTS[fault][0])
    s = s.replace('module soc_pcie_gen3_framer_rx_integrity_v30 #(',
                  'module soc_pcie_gen3_framer_rx_integrity_v27 #(')
    (directory/'soc_pcie_gen3_framer_rx_integrity_v26.v').write_text(s)
    p = directory/'soc_pcie_gen3_continuous_rx_integrity_v26.v'
    observer = r'''
integer v30_checked=0,v30_faults=0;
reg [3:0] v30_seen=0;
always @(posedge clk_i) begin
 if(rst_ni===1'b1 && framer.enabled===1'b1 && framer.active_o===1'b1) begin
   if(framer.token_failure !== reference.framer.token_failure)
     $fatal(1,"V30_PREEDGE_FAULT_DECISION");
   if((^framer.token_failures)===1'bx) $fatal(1,"V30_UNKNOWN_PROCEDURAL_FLAG");
   v30_checked=v30_checked+1;
   if(framer.step && framer.token_failure) begin
     v30_faults=v30_faults+1;v30_seen=v30_seen|framer.token_failures;
   end
 end
end
final $display("V30_FAULT_WITNESS checked=%0d faults=%0d lanes=%0h",v30_checked,v30_faults,v30_seen);
'''
    p.write_text(p.read_text().replace('endmodule',observer+'\nendmodule',1))
    return directory


def test_exact_v30_inverse():
    g = runpy.run_path(str(ROOT/'scripts/generate_pcie_integrity_fault_v30.py'))
    text,edits = g['generate']()
    assert len(edits) == 4 and text == (RTL/'soc_pcie_gen3_framer_rx_integrity_v30.v').read_text()


@pytest.mark.parametrize('fault',[None,*FAULTS],ids=['positive',*FAULTS])
def test_actual_balanced_fault(tmp_path, fault):
    h = runpy.run_path(str(ROOT/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v26.py'))
    result,record,_,out = h['run'](tmp_path,rtl=prepare(tmp_path/'rtl',fault),case=FAULTS[fault][1] if fault else None)
    log = (out/'simulation.log').read_text()
    if fault:
        assert result.returncode != 0 and record['status'] == 'FAIL'
        assert 'V30_PREEDGE_FAULT_DECISION' in log
        assert 'syntax error' not in log.lower()
    else:
        assert result.returncode == 0 and record['tests'] == dict(passed=19,failed=0,skipped=0),record
        m = re.search(r'V30_FAULT_WITNESS checked=(\d+) faults=(\d+) lanes=([0-9a-f]+)',log)
        assert m
        checked,faults,lanes = int(m[1]),int(m[2]),int(m[3],16)
        assert checked > 1000 and faults >= 8 and lanes > 0
        cycles = re.search(r'V27_FRONTIER_WITNESS cycles=(\d+)',log)
        assert cycles and int(cycles[1]) > 1000
        (out/'fault-witness.json').write_text(json.dumps(dict(checked=checked,faults=faults,
            lanes=lanes,public_cycles=int(cycles[1])),indent=2)+'\n')
