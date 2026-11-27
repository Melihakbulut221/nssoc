#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Preserve packet type with each ordered event, including CRC-discard events."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'soc_pcie_gen3_dllp_consumer_v5.v':'734cce5b4b37b5d1f8ec4751deecdd3fda8934e32dbc1b7570b2ee2492cd72b4',
 'soc_pcie_gen3_recovered_events_v1.v':'840863872ae5a06e2f6d8fed642e28b14da58faea3c581445e221ae5caef370c',
}
CONSUMER_CHANGES=[
 ('module soc_pcie_gen3_dllp_consumer_v5(', 'module soc_pcie_gen3_dllp_consumer_v6('),
 (' output wire [3:0] event_valid_o,input wire event_ready_i,',' output wire [3:0] event_valid_o,input wire event_ready_i,\n output wire [3:0] event_packet_dllp_o,'),
 (' reg [15:0] event_kind,event_kind_n;',' reg [15:0] event_kind,event_kind_n;\n reg [3:0] event_packet_dllp,event_packet_dllp_n;'),
 (' assign event_kind_o=event_valid_o!=0?event_kind:0;',' assign event_kind_o=event_valid_o!=0?event_kind:0;\n assign event_packet_dllp_o=event_valid_o & event_packet_dllp;'),
 ('   event_kind_n=event_kind;','   event_packet_dllp_n=event_packet_dllp;\n   event_kind_n=event_kind;'),
 ('     event_count_n=0;event_owner_n=0;','     event_packet_dllp_n=0;\n     event_count_n=0;event_owner_n=0;'),
 ('         if(nb[a]) event_kind_n[j*4+:4]=1;','         event_packet_dllp_n[j]=nk[a];\n         if(nb[a]) event_kind_n[j*4+:4]=1;'),
 ('     event_kind<=0;event_raw<=0;','     event_packet_dllp<=0;\n     event_kind<=0;event_raw<=0;'),
 ('       event_kind<=event_kind_n;','       event_packet_dllp<=event_packet_dllp_n;\n       event_kind<=event_kind_n;'),
]
WRAPPER_CHANGES=[
 ('module soc_pcie_gen3_recovered_events_v1 #(', 'module soc_pcie_gen3_recovered_events_v2 #('),
 (' output wire [3:0] event_valid_o,input wire event_ready_i,',' output wire [3:0] event_valid_o,input wire event_ready_i,\n output wire [3:0] event_packet_dllp_o,'),
 (' soc_pcie_gen3_dllp_consumer_v5 consumer(', ' soc_pcie_gen3_dllp_consumer_v6 consumer('),
 (' .event_valid_o(event_valid_o),.event_ready_i(event_ready_i),', ' .event_packet_dllp_o(event_packet_dllp_o),\n .event_valid_o(event_valid_o),.event_ready_i(event_ready_i),'),
]

def apply_changes(name, text, changes):
    for old,new in changes:
        assert text.count(old)==1,(name,old,text.count(old))
        text=text.replace(old,new)
    return text


def candidate(name,changes):
    current=(ROOT/'hw/soc/rtl/pcie'/name).read_bytes()
    if hashlib.sha256(current).hexdigest()==SOURCES[name]:
        return apply_changes(name,current.decode(),changes)

    # The Icarus loop repair was applied independently to both versions.
    # Authenticate both generations before replaying the same sideband edit.
    assert name=='soc_pcie_gen3_dllp_consumer_v5.v', 'Frozen baseline changed'
    evidence=ROOT/'hw/soc/pcie-evidence/20261007-ci-resume'
    original=(evidence/'before'/name).read_bytes()
    assert hashlib.sha256(original).hexdigest()==SOURCES[name], 'Frozen baseline changed'
    old_target=apply_changes(name,original.decode(),changes).encode()
    assert hashlib.sha256(old_target).hexdigest()=='263d91fb910ab27e5ac3e2efe49b4e93366aff2d47a498afc483dfd587c679dc'
    assert old_target==(evidence/'before/soc_pcie_gen3_dllp_consumer_v6.v').read_bytes()
    tested=evidence/'tested-source/hw/soc/rtl/pcie'
    assert hashlib.sha256(current).hexdigest()=='f530b043f79880258c67596bf4a98eeeccc1845038d0ceb9d476e1dfa8245b9d'
    assert current==(tested/name).read_bytes()
    result=apply_changes(name,current.decode(),changes)
    assert hashlib.sha256(result.encode()).hexdigest()=='276d2869efdefae58072bf819319537834707825f9bcd3e0cbfce615e33a4b85'
    assert result.encode()==(tested/'soc_pcie_gen3_dllp_consumer_v6.v').read_bytes()
    return result

if __name__=='__main__':
    for name,new,changes in [('soc_pcie_gen3_dllp_consumer_v5.v','soc_pcie_gen3_dllp_consumer_v6.v',CONSUMER_CHANGES),('soc_pcie_gen3_recovered_events_v1.v','soc_pcie_gen3_recovered_events_v2.v',WRAPPER_CHANGES)]:
        (ROOT/'hw/soc/rtl/pcie'/new).write_text(candidate(name,changes))
