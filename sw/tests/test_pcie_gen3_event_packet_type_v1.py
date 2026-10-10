# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual sideband association, inverse bridges, raw-lane composition and faults."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import pytest
ROOT=Path(__file__).resolve().parents[2]
LEAF='soc_pcie_gen3_dllp_consumer_v6';RAW='soc_pcie_gen3_recovered_events_v2'

@pytest.mark.parametrize('source,target,changes',[
 ('soc_pcie_gen3_dllp_consumer_v5.v',LEAF+'.v','CONSUMER_CHANGES'),
 ('soc_pcie_gen3_recovered_events_v1.v',RAW+'.v','WRAPPER_CHANGES'),
])
def test_only_declared_sideband_added(source,target,changes):
    p=ROOT/'scripts/generate_pcie_event_type_sideband_v1.py';spec=importlib.util.spec_from_file_location('sideband_generator',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    pairs=getattr(m,changes);actual=(ROOT/'hw/soc/rtl/pcie'/target).read_text();assert actual==m.candidate(source,pairs)
    for old,new in reversed(pairs):
        assert actual.count(new)==1
        actual=actual.replace(new,old)
    assert actual==(ROOT/'hw/soc/rtl/pcie'/source).read_text()

def run(tmp,top,rtl=None,case=None):
    command=[sys.executable,str(ROOT/'scripts'/('check_'+top.removeprefix('soc_')+'.py')),'--out',str(tmp/'capture'),'--iverilog-dir',str(ROOT/'hw/soc/tools/oss-cad-suite/bin')]
    if rtl:command+=['--rtl',str(rtl)]
    if case:command+=['--test',case]
    with (tmp/'launch.log').open('w') as f:
        result=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    r=json.loads((tmp/'capture/result.json').read_text());log=(tmp/'capture/simulation.log').read_text();rows=[x for x in ET.parse(tmp/'capture/results.xml').getroot().iter('testcase') if x.find('skipped') is None]
    return result.returncode,r,log,rows

@pytest.mark.parametrize('top,count',[(LEAF,8),(RAW,11)])
def test_actual_type_sideband_complete_ports(tmp_path,top,count):
    rc,r,log,rows=run(tmp_path,top)
    assert rc==0,log
    assert r['tests']==dict(passed=count,failed=0,skipped=0)
    assert len(rows)==count and all(x.find('failure') is None for x in rows)

BAD='bad_packet_type_survives_stalls_and_owner_wrap'
FAULTS=[
 (LEAF,'event_packet_dllp_n[j]=nk[a];',"event_packet_dllp_n[j]=1'b0;",BAD,'Ordered decode mismatch'),
 (LEAF,'event_packet_dllp_n[j]=nk[a];','event_packet_dllp_n[j]=nk[a] && ng[a];',BAD,'Ordered decode mismatch'),
 (LEAF,'event_valid_o & event_packet_dllp','event_valid_o & descriptor_dllp_i',BAD,'Ordered decode mismatch'),
 (LEAF,'event_valid_o & event_packet_dllp','event_packet_dllp','packet_type_masked_on_flush_and_epoch_change','Packet type escaped flush mask'),
 (RAW,'.event_packet_dllp_o(event_packet_dllp_o)','.event_packet_dllp_o()', 'crc_bad_nullified_ack_nak_fc_and_owner_wrap','ValueError'),
]
@pytest.mark.parametrize('top,old,new,case,diagnostic',FAULTS)
def test_actual_packet_type_wiring_fault_rejected(tmp_path,top,old,new,case,diagnostic):
    s=(ROOT/'hw/soc/rtl/pcie'/(top+'.v')).read_text();assert s.count(old)==1
    p=tmp_path/'mutant.v';p.write_text(s.replace(old,new))
    rc,r,log,rows=run(tmp_path,top,p,case)
    assert rc!=0 and r['status']=='FAIL',log
    assert len(rows)==1 and rows[0].find('failure') is not None
    assert 'Running on Icarus Verilog' in log and diagnostic in log,log
