from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent
old=R/'sw/tests/test_pcie_gen3_integrity_v22_miter.py'
s=old.read_text().replace('_v22','_NEW').replace('_v21','_v22').replace('_NEW','_v23').replace('V22_','V23_').replace('v21_v22','v22_v23')
s=s.replace('"passed": 17','"passed": 18').replace('PASS_SEVENTEEN_','PASS_EIGHTEEN_')
s=s.replace('integer v22_scan,v22_diff;reg v22_fault_edge=0;','integer v22_scan,v22_diff;reg v22_fault_edge=0;reg v23_before_cache[0:RING_DWORDS-1];')
s=s.replace('if(v22_fault_edge===1\'b1) v22_fault_step_events=v22_fault_step_events+1;', '''if(v22_fault_edge===1'b1) begin
  v22_fault_step_events=v22_fault_step_events+1;
  for(v22_scan=0;v22_scan<RING_DWORDS;v22_scan=v22_scan+1)
    v23_before_cache[v22_scan]=candidate.framer.slot_verdict[v22_scan];
 end''')
s=s.replace('candidate.framer.slot_verdict[v22_scan] !== reference.framer.slot_verdict[v22_scan]','candidate.framer.slot_verdict[v22_scan] !== v23_before_cache[v22_scan]')
# The former V22-vs-V21 invalid cache differential becomes actual same-edge
# before/after writes; V23-vs-V22 caches are intentionally byte identical.
s=s.replace('    wrapper = "\\n".join(', '    compare += HEADER_OBSERVER\n    wrapper = "\\n".join(',1)
s=s.replace('    elif fault is not None:\n', '''    elif fault in HEADER_FAULTS:
        p = directory / (NEW_FRAMER + ".v")
        text = p.read_text()
        before, after = HEADER_FAULTS[fault]
        assert text.count(before) == 1
        p.write_text(text.replace(before, after))
    elif fault is not None:
''')
s=s.replace('        "fault_keeps_ring_owner",\n    ],','        "fault_keeps_ring_owner",\n        *HEADER_FAULTS,\n    ],')
s=s.replace('        else "sustained_minimum_packets_exceed_every_buffer",','        else "adjacent_header_all_positions_and_bank_boundaries"\n        if fault in HEADER_FAULTS else "sustained_minimum_packets_exceed_every_buffer",')
s=s.replace('            "V23_FAULT_QUARANTINE_NOT_ATOMIC",','            "V23_FAULT_QUARANTINE_NOT_ATOMIC",\n            "V23_HEADER_BANK_RELATION",\n            "V23_FIRST_HEADER_RELATION",\n            "V23_CARRIED_HEADER_RELATION",')
s=s.replace('test_only_quarantined_cache_edits_to_frozen_sources','test_only_registered_header_edits_to_frozen_sources').replace('test_pcie_gen3_integrity_v23_cache.py','test_pcie_gen3_integrity_v23_header.py')
observer=(B/'header_observer01.vh').read_text()
faults={
 'header_wrong_predecessor':('predecessor=decoded[(index-1)*32+19+:13];','predecessor=decoded[index*32+19+:13];'),
 'header_current_input_tail':('if(index==0) predecessor=previous_encoded;','if(index==0) predecessor=decoded[15*32+19+:13];'),
 'header_shift_wrong':("current_header_relation<={4'b1111,current_header_relation[15:4]};","current_header_relation<={4'b1111,current_header_relation[11:0]};"),
 'header_promote_stale':('current_header_relation<=next_header_relation;','current_header_relation<=current_header_relation;'),
 'header_carried_invert':('packet_header_mismatch_n=current_header_relation[j];','packet_header_mismatch_n=~current_header_relation[j];'),
 'header_carried_always_bad':('current_header_relation[0] : packet_header_mismatch;','current_header_relation[0] : 1\'b1;'),
}
pos=s.index('\n\ndef pin(');s=s[:pos]+'\n\nHEADER_FAULTS = '+repr(faults)+'\n\nHEADER_OBSERVER = '+repr(observer)+s[pos:]
(R/'sw/tests/test_pcie_gen3_integrity_v23_miter.py').write_text(s)
p=R/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v23.py';s=p.read_text();s=s.replace('len(cases) == 17','len(cases) == 18').replace('"passed": 17','"passed": 18')
s=s.replace('end else if((stream_abort_i && active_o) || fault_now) begin\\n       retire_valid', 'end else if((stream_abort_i && active_o) || fault_now) begin\\n       packet_header_mismatch<=0;\\n       retire_valid')
p.write_text(s)
