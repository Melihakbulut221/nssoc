# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Real raw-port ownership, controller-event ordering and actual RTL faults."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
RTL=ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_recovered_events_v1.v'
SCRIPT=ROOT/'scripts/check_pcie_gen3_recovered_events_v1.py'


def test_owned_pcs_extension_is_exact_and_reversible():
    p=ROOT/'scripts/generate_pcie_owned_pcs_v3.py'
    spec=importlib.util.spec_from_file_location('owned_pcs_generator',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    actual=(ROOT/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_owned_v3.v').read_text()
    assert actual==m.candidate()
    text=actual.removesuffix('`default_nettype wire\n').replace('owned_v3','owned_v2')
    text=text.replace('`default_nettype none\n// Owned CRC parser for complete, descrambled DATA quartets from strict PCS.', '// Fixed aligned/deskewed, already descrambled x4 Data Blocks only.')
    for old,new in reversed(m.CHANGES):
        assert text.count(new)==1
        text=text.replace(new,old)
    assert text==m.SOURCE.read_text()


def run(tmp_path,source=RTL,case=None):
    command=[sys.executable,str(SCRIPT),'--out',str(tmp_path/'capture'),'--rtl',str(source),'--iverilog-dir',str(ROOT/'hw/soc/tools/oss-cad-suite/bin')]
    if case:command+=['--test',case]
    with (tmp_path/'producer.log').open('w') as log:
        p=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    return p.returncode,json.loads((tmp_path/'capture/result.json').read_text()),(tmp_path/'capture/simulation.log').read_text()


def test_actual_recovered_lanes_to_owned_controller_events(tmp_path):
    rc,r,log=run(tmp_path)
    assert rc==0,log
    assert r['tests']=={'passed':11,'failed':0,'skipped':0}


CLEAN='crc_bad_nullified_ack_nak_fc_and_owner_wrap'
FAULTS={
 'body_generation_lost':('.body_owner_i(bo)',".body_owner_i(bo & 24'h7df7df)",CLEAN,'Wrong TLP owner generation'),
 'descriptor_owner_lost':('.descriptor_owner_i(doid)',".descriptor_owner_i(24'b0)",CLEAN,'Unexpected raw-owned-event epoch fault'),
 'crc_discard_descriptor_lost':('.descriptor_crc_bad_i(db)',".descriptor_crc_bad_i(4'b0)",CLEAN,'Unexpected raw-owned-event epoch fault'),
 'event_backpressure_lost':('.event_ready_i(event_ready_i)',".event_ready_i(1'b1)",'independent_tlp_and_event_backpressure','Held ordered event changed'),
 'body_backpressure_lost':('.tlp_ready_i(tlp_ready_i)',".tlp_ready_i(1'b1)",'independent_tlp_and_event_backpressure','Held owned TLP changed'),
 'normal_stop_flushes_events':('.flush_i(stream_start_o || abort_i || upstream_fault)', '.flush_i(stream_start_o || stream_stop_o || abort_i || upstream_fault)','normal_end_keeps_held_events_during_later_lane_fault','Unexpected raw-owned-event epoch fault'),
 'abort_output_mask_lost':('.flush_i(stream_start_o || abort_i || upstream_fault)', '.flush_i(stream_start_o)','explicit_abort_suppresses_held_event_before_edge_and_reset_recovers','Old event can handshake on explicit abort edge'),
 'consumer_drain_count_lost':('(draining || upstream_end) && pending_next==0',"(draining || upstream_end) && 1'b1",'normal_end_waits_for_events_after_body_drains','Stream end preceded ordered event retirement'),
}


@pytest.mark.parametrize('name',FAULTS)
def test_actual_owned_event_wiring_fault_is_rejected(tmp_path,name):
    old,new,case,diagnostic=FAULTS[name];text=RTL.read_text();assert text.count(old)==1
    mutant=tmp_path/'mutant.v';mutant.write_text(text.replace(old,new))
    rc,r,log=run(tmp_path,mutant,case)
    assert rc!=0 and r['status']=='FAIL',log
    assert 'Running on Icarus Verilog' in log and 'TESTS=1' in log and diagnostic in log,log
