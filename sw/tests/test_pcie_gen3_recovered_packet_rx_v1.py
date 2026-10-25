# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual serialized packet path and interface faults, no internal signal oracle."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
RTL=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_recovered_packet_rx_v1.v'
SCRIPT=ROOT/'scripts/check_pcie_gen3_recovered_packet_rx_v1.py'


def run(tmp_path,source=RTL,case=None):
    command=[sys.executable,str(SCRIPT),'--out',str(tmp_path/'capture'),'--rtl',str(source),'--iverilog-dir',str(ROOT/'hw/soc/tools/oss-cad-suite/bin')]
    if case:command+=['--test',case]
    with (tmp_path/'producer.log').open('w') as log:
        p=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    return p.returncode,json.loads((tmp_path/'capture/result.json').read_text()),(tmp_path/'capture/simulation.log').read_text()


def test_actual_serial_records_to_integrity_qualified_packets(tmp_path):
    rc,r,log=run(tmp_path)
    assert rc==0,log
    assert r['tests']=={'passed':15,'failed':0,'skipped':0}


CLEAN='actual_packet_context_skp_resume_and_payload_eds'
FAULTS={
 'normal_end_guard_lost':('epoch_fault=front_fault && !stopped_q','epoch_fault=front_fault', 'normal_end_drain_survives_later_transport_fault','Unexpected raw-to-packet epoch fault'),
 'eds_disconnected':('.decision_eds_i(eds)',".decision_eds_i(1'b0)",CLEAN,'Unexpected raw-to-packet epoch fault'),
 'decision_disconnected':('.decision_valid_i(decision)',".decision_valid_i(1'b0)",CLEAN,'Unexpected raw-to-packet epoch fault'),
 'stream_stop_lost':('.stream_stop_i(stream_stop_o)',".stream_stop_i(1'b0)",CLEAN,'Bounded raw x4 deskew scenario did not complete'),
 'wrong_headers':(".headers_i(8'haa)",".headers_i(8'hab)",CLEAN,'Unexpected raw-to-packet epoch fault'),
 'blocks_reversed':('.payload_i(block_data)', '.payload_i({block_data[127:0],block_data[255:128],block_data[383:256],block_data[511:384]})',CLEAN,'Unexpected raw-to-packet epoch fault'),
 'packet_backpressure_lost':('.ready_i(ready_i)',".ready_i(1'b1)",'packet_output_stalls_and_independent_lane_skew','Held packet beat changed'),
 'parser_reset_lost':('.rst_ni(por_ni && !reset_i)', '.rst_ni(por_ni)','coordinated_reset_recovers_after_framing_abort','Coordinated reset did not clear parser state'),
}


@pytest.mark.parametrize('name',FAULTS)
def test_actual_packet_interface_fault_rejected(tmp_path,name):
    old,new,case,diagnostic=FAULTS[name];text=RTL.read_text()
    assert text.count(old)==1
    mutant=tmp_path/'mutant.v';mutant.write_text(text.replace(old,new))
    rc,r,log=run(tmp_path,mutant,case)
    assert rc!=0 and r['status']=='FAIL',log
    assert 'Running on Icarus Verilog' in log and 'TESTS=1' in log and diagnostic in log,log
