# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent full-byte quarantine-source inverse and finite test-design peer."""
from pathlib import Path
import ast,hashlib,itertools,json,re
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze03.json').read_text());assert pin(B/'source-freeze03.json')==dict(bytes=2241,sha256='59652fa3023ac56765644368d95e602470a48dc900419480fd6d2649d49443e6')
assert len(f['files'])==9 and f['files']=={n:pin(R/n) for n in f['files']}
oldp=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v17.v';newp=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v19.v'
assert pin(oldp)['sha256']=='7aeb0b29e6b56978bed7f83a48b14e8e11a005bf16342cfd8b616225ba9d8160'
old=oldp.read_text();new=newp.read_text();a=old.index('           slot_data[(write_ptr+w)&(RING_DWORDS-1)]<=');z=old.index('           if(verdict_enable[w])',a);original=old[a:z];assert len(original.splitlines())==7
start=new.index(' // BEGIN V19 SEVEN QUARANTINED RING CONTENT WRITES\n');end=new.index(' // END V19 SEVEN QUARANTINED RING CONTENT WRITES\n',start)+len(' // END V19 SEVEN QUARANTINED RING CONTENT WRITES\n');writer=new[start:end]
marker='           // V19 only ring content writes moved to the step writer.\n';assert new.count(marker)==1
inverse=(new[:start]+new[end:]).replace(marker,original).replace('integrity_v19','integrity_v17');assert inverse==old
assert re.sub(r'\bw\b','slot_content_lane',original) in writer
fields=['data','keep','sop','eop','dllp','sequence','tag']
assert writer.count('always @(posedge clk_i)')==1 and writer.count('if(step) begin')==1
for field in fields:
 assert new.count(f'slot_{field}[(write_ptr+slot_content_lane)&(RING_DWORDS-1)]<=')==1
 assert f'slot_{field}[(write_ptr+w)&(RING_DWORDS-1)]<=' not in new
for stem in ['hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_','hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_','scripts/check_pcie_gen3_continuous_rx_integrity_']:
 suffix='.v' if stem.startswith('hw/soc/rtl') else '.py' if stem.startswith('scripts') else ''
 assert (R/(stem+'v19'+suffix)).read_text().replace('_v19','_v17')==(R/(stem+'v17'+suffix)).read_text()
for expression in [
 'wire enabled=rst_ni && !flush_i && !stream_start_i && !stream_abort_i;',
 'wire ring_overflow_now=enabled && active_o && !ending && current_valid && capacity_overflow;',
 'wire step=enabled && active_o && !ending && current_valid && !ring_overflow_now;',
 'wire fault_now=ring_overflow_now || bad_block_now || (step && token_failure);',
 'if(step && !fault_now) slot_verdict[cache_slot]<=next_value;',
 'write_ptr<=0;read_ptr<=0;commit_ptr<=0;error_pulse<=1;active_o<=0;halted_o<=1;',
 'state<=TOKEN;current_valid<=0;next_valid<=0;output_valid<=0;ending<=0;']:
 assert expression in old and expression in new
# Independent finite Boolean gate check, deliberately not a reachability proof.
combos=extras=0
for rst,flush,start_i,abort,active,ending,current,capacity,badblock,token in itertools.product([False,True],repeat=10):
 enabled=rst and not(flush or start_i or abort)
 overflow=enabled and active and not ending and current and capacity
 step=enabled and active and not ending and current and not overflow
 fault=overflow or badblock or (step and token)
 oldwrites=rst and not(flush or start_i) and not((abort and active) or fault) and active and step
 assert oldwrites==(step and not fault)
 if step and not oldwrites:
  extras+=1;assert fault and (badblock or token) and not overflow and enabled and active and not ending
 combos+=1
bench17=(R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v17.py').read_text();bench19=(R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v19.py').read_text();assert bench19.startswith(bench17)
bench_ast=ast.parse(bench19);cases=[n.name for n in bench_ast.body if isinstance(n,ast.AsyncFunctionDef) and n.decorator_list];assert len(cases)==14 and len(set(cases))==14
assert cases[-1]=='fault_quarantine_restart_wrap_and_backpressure'
assert 'bytes(64 + (fault_index + 1) * 4)' in bench19
assert 'for recovery in range(4):' in bench19 and 'assert epochs == 16 and held_faults > 0' in bench19
assert 'assert faulted_steps >= 16 and invalid_differences >= 16' in bench19
assert 'assert not int(d.overflow_o.value)' in bench19
assert 'for j in range(max(128, RING * 2)):' in bench19
miter=(R/'sw/tests/test_pcie_gen3_integrity_v19_miter.py').read_text();literal=(R/'sw/tests/test_pcie_gen3_integrity_v19_slots.py').read_text()
for text in [miter,literal]:ast.parse(text)
for token in ['PCIE_CYCLE_MITER_OUTPUT_MISMATCH','PCIE_OCCUPIED_SLOT_MISMATCH','PCIE_COMMITTED_SLOT_VERDICT_MISMATCH','PCIE_RING_CONTROL_MISMATCH','PCIE_PREDECODE_COMPANION_MISMATCH','V19_FAULT_QUARANTINE_NOT_ATOMIC']:
 assert token in miter
assert 'slot_writer_skips_step' in miter and "if(1'b0) begin" in miter
assert 'for(n=0;n<4096;n=n+1)' in literal
assert 'known_updates!=1024||unknown_holds!=2048||wraps!=48' in literal
assert '[None, *["lose_" + f for f in FIELDS], "rotate_data", "ignore_step"]' in literal
# Confirm both additive pre-execution harness edits are the declared one-site
# differences; all product bytes remain untouched across the three freezes.
f1=json.loads((B/'source-freeze01.json').read_text());f2=json.loads((B/'source-freeze02.json').read_text())
for n in f['files']:
 if n!='sw/tests/test_pcie_gen3_integrity_v19_miter.py':assert f1['files'][n]==f2['files'][n]
 if n!='hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v19.py':assert f2['files'][n]==f['files'][n]
oldbench=(B/'freeze02-public-bench-original.py').read_text();assert oldbench.replace('bytes((fault_index + 1) * 4)','bytes(64 + (fault_index + 1) * 4)')==bench19
r=dict(status='PASS_SOURCE_ONLY_V19_QUARANTINED_SLOTS',findings=[],freeze=pin(B/'source-freeze03.json'),method=pin(__file__),source_pins=f['files'],baseline=pin(oldp),whole_framer_inverse_byte_exact=True,seven_field_writer_exact_rhs_and_indices=True,unchanged_complete_wrapper_checker_makefile=True,unchanged_first13_public_cases=True,finite_boolean_gate_relations=combos,extra_fault_gate_assignments=extras,planned_public_cases=14,planned_fault_restart_epochs=16,planned_literal_cases=4096,planned_literal_mutants=9,actual_new_functional_execution=False,review=[
 'Exact full-byte inverse restores V17 after removing only the seven-field step writer and restoring its original statements. Verdict/cache, parser, capacity/ending, pointers, reset/fault/abort/public priority and read tree are untouched.',
 'For reset-initialized binary lifecycle operation, extra writes require step and fault; exact step still suppresses reset/start/flush/abort/ending/overflow. Same-edge original fault clears owner pointers, current/next valid, output valid and ending, deactivating and halting the epoch.',
 'Invalid data/tag contents may differ. Capacity and pointer rules prevent overwriting live slots, and each later write-pointer advance writes all four contents before visibility. On reuse, unchanged cache effective_tag and cache_write_old_verdict initialization use the new write tag before applying same-cycle verdict broadcasts; stale invalid tags do not establish visible ownership.',
 'Fourteen-case oracle and V17/V19 miter retain all prior13 cases. New four malformations times four recovery routes exercise faulted steps, actual invalid-content divergence, atomic empty/halt, held prior output, halted drain requests, mixed TLP/DLLP ring wrap, stalls and EDS drain. Witnesses are assertions to be measured, not presumed PASS.',
 'Literal actual-HDL design covers seven complete arrays at4096 trials, all128 extended pointers,1024known writes,2048X/Zstep holds and48wrap writes; seven missing fields plus rotated payload and ignored step are nine meaningful component faults.',
 'Before any HDL, public if1 mutant was replaced by definite if0 missing-slot writes; separate literal if1 control remains meaningful. Added64idle bytes places later fault below64-slot capacity while permitting prior output to be held. Earlier source snapshots and notes are retained.',
 'The old quarantine-relation01 coverage-plan line describing public all-step broadening is superseded by negative-stimulus-correction02 and stimulus-strengthening03; current executable tests use if0. No prior failed/incomplete run is converted to success.'
],required_next='Actual immutable functional controls under CPU6 and2GiB inherited limit, including14direct+14miter cases and16fault/restart witnesses. Native mapping/timing requires all controls and final source hashes PASS first; keep originalMAX150/4ns constraints. This review does not authorize classifying invalid storage as equivalent or claiming exhaustive reachability/formal/physical closure.')
assert not (B/'source-only-peer-rx.json').exists();(B/'source-only-peer-rx.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(B/'source-only-peer-rx.json'))
