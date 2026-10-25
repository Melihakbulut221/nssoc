"""Independent saved-source review; no producer imports, compilation or controls."""
import ast,hashlib,json,difflib
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;P=R/'hw/soc/out/pcie-integrity-v21-20261005'
def pin(p):
 b=Path(p).read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
f=json.loads((B/'source-freeze02.json').read_text());assert all(pin(R/p)==v for p,v in f['sources'].items())
old=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v21.v';new=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v22.v'
a=old.read_text();b=new.read_text();assert pin(old)['sha256']=='740757e328072118e57a775cf7987f942bd44c2f4e411484f9f1aeac8310ae78'
changes=[('if(step && !fault_now) slot_verdict[cache_slot]<=next_value;','if(step) slot_verdict[cache_slot]<=next_value; // V22 invalid cache content is quarantined.'),('matching verdict updates. Faulted/aborted steps cannot update either array.','matching verdict updates. V22 permits cache-only writes in a fault-invalidated epoch.')]
x=a
for before,after in changes:assert x.count(before)==1;x=x.replace(before,after)
x=x.replace('integrity_v21','integrity_v22');assert x==b
x=b.replace('integrity_v22','integrity_v21')
for before,after in reversed(changes):assert x.count(after)==1;x=x.replace(after,before)
assert x==a
bridges={}
for n in ['hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v21.v','hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v21','scripts/check_pcie_gen3_continuous_rx_integrity_v21.py']:
 p=R/n;q=R/n.replace('_v21','_v22');assert q.read_text().replace('_v22','_v21')==p.read_text();bridges[n]={'old':pin(p),'new':pin(q)}
p=R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v21.py';q=R/str(p.relative_to(R)).replace('_v21','_v22');normal=q.read_text().replace('_v22','_v21').replace('V22_','V21_');assert normal.startswith(p.read_text())
orig=[n.name for n in ast.parse(p.read_text()).body if isinstance(n,ast.AsyncFunctionDef) and n.decorator_list];cases=[n.name for n in ast.parse(q.read_text()).body if isinstance(n,ast.AsyncFunctionDef) and n.decorator_list];assert len(orig)==16 and len(cases)==17 and cases[:16]==orig
public=R/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v22.py';saved=B/'pre-execution-source01/sw/tests/test_pcie_gen3_continuous_rx_integrity_v22.py';assert saved.exists();s=saved.read_text();t=public.read_text();assert s.count('assert len(cases) == 16')==1;assert s.replace('assert len(cases) == 16','assert len(cases) == 17')==t
# Extract data literals directly from test AST; never import producer modules.
m=R/'sw/tests/test_pcie_gen3_integrity_v22_miter.py';ma=ast.parse(m.read_text());defs={n.targets[0].id:ast.literal_eval(n.value) for n in ma.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('INPUTS','OUTPUTS')};assert len(defs['INPUTS'])==7 and len(defs['OUTPUTS'])==17
mt=m.read_text();required=['PCIE_CYCLE_MITER_OUTPUT_MISMATCH','PCIE_RING_CONTROL_MISMATCH','PCIE_OCCUPIED_SLOT_MISMATCH','V22_OCCUPIED_SLOT_VERDICT_MISMATCH','V22_DESCRIPTOR_OWNERSHIP_MISMATCH','V22_OWNED_DESCRIPTOR_PAYLOAD_MISMATCH','V22_FAULT_QUARANTINE_NOT_ATOMIC','PCIE_VALID_INGRESS_SLOT_MISMATCH','PCIE_PREDECODE_COMPANION_MISMATCH'];assert all(x in mt for x in required)
assert 'v22_fault_edge = candidate.framer.step && candidate.framer.fault_now;' in mt
assert 'wire enabled=rst_ni && !flush_i && !stream_start_i && !stream_abort_i;' in b
assert 'if(flush_i || stream_start_i)' in b and 'else if((stream_abort_i && active_o) || fault_now)' in b
assert 'write_ptr<=0;read_ptr<=0;commit_ptr<=0;error_pulse<=1;active_o<=0;halted_o<=1;' in b
assert 'if(verdict_enable[w]) verdict[verdict_tags[w*PW+:PW]]<=verdict_value[w];' in b
assert 'observed_fault > 0 and observed_diff > 0' in q.read_text() and "for recovery in ('start', 'flush', 'reset', 'abort')" in q.read_text()
# Compare complete launch bodies using literal substitutions for all intentional differences.
la=(P/'launch_controls03.py').read_text();lb=(B/'launch_controls02.py').read_text();la=la.replace('V21','V22').replace('v21','v22').replace('source-freeze03','source-freeze02').replace('c7ff40ed5045e9265a40fe8aa27fc073b335649f9fd65579372f22b3eaaa4e97',pin(B/'source-freeze02.json')['sha256']).replace('source-only-peer-rx03','source-only-peer-vco02').replace('REGISTERED_RETIRE','QUARANTINED_CACHE').replace('integrity_v22_pipeline.py','integrity_v22_cache.py').replace('integrity_v22_nominal.py','integrity_v22_miter.py')
a_scope='Separate V22 registered retire architecture from V17; explicit changed internal latency, independent public-byte oracle and restricted ready-one relation; original4ns and2GiB fixed.'
b_scope='Separate V22 cache writer qualification fromV21; same latency, allpublic cyclemiter and cachefault quarantine; original4ns and2GiB fixed.'
assert a_scope in la;la=la.replace(a_scope,b_scope);assert la==lb
# Detached wrapper differences are frozen identity pins, peer/version and selected filename only.
da=(P/'detach_controls03.py').read_text();db=(B/'detach_controls02.py').read_text();da=da.replace('V21','V22').replace('v21','v22').replace('launch_controls03','launch_controls02').replace('source-freeze03','source-freeze02').replace('source-only-peer-rx03','source-only-peer-vco02').replace('REGISTERED_RETIRE','QUARANTINED_CACHE');da=da.replace(str(pin(P/'launch_controls03.py')),str(pin(B/'launch_controls02.py'))).replace(str(pin(P/'source-freeze03.json')),str(pin(B/'source-freeze02.json')));assert da==db
lf=json.loads((B/'launch-source-freeze02.json').read_text());assert lf['freeze']==pin(B/'source-freeze02.json')
for n,v in lf['support'].items():assert pin(B/n)==v
for n,v in lf['exact_lifecycle_parent'].items():assert pin(P/n)==v
result=dict(status='PASS_SOURCE_ONLY_V22_QUARANTINED_CACHE',freeze=pin(B/'source-freeze02.json'),findings=[],source_pins=f['sources'],method=pin(__file__),launch_freeze=pin(B/'launch-source-freeze02.json'),relation=pin(B/'quarantine-relation01.json'),retained_finding=pin(B/'source-only-peer-vco01-findings.json'),entire_framer_forward_inverse=True,wrapper_makefile_checker_bridges=bridges,original_oracle_cases=orig,new_oracle_cases=cases,public_case_inventory_correction='Only saved16->17 assertion; no RTL or bench edit.',lifecycle='Complete launcher/detacher reconstructed independently from reviewedV21; identical ProcessOwner wait/check/post-context checks, CPU6/2GiB, no healthy timeout. Immediate detached launch with exclusive once marker; progress separately required.',temporal_argument=['Enabled step excludes reset/flush/start/abort. Only a known fault-qualified step can add cache writes versusV21. Same unchanged fault branch clears ring pointers/retire+output validity and halts/deactivates at that edge.','All parser/main verdict/slot tag/content ownership writers are byte-identical. Differences are quarantined in unowned cache slots. Fresh slot ownership computes effective new tag from same write tags, initializes from common main verdict then same last-writer ordered four broadcasts.','Nonempty occupied-slot cache and owned descriptor payload compared in full old/new miter together with all17 public output ports; no invalid state equality or arbitrary-X control equivalence claimed.'],mandatory_control_review=['4096 actual literal cache trials include step0/1/X/Z, selected X/Z payload, overlapping last-writer and actual fault-cache changes; six targeted mutants require semantic trial failure.','New fullproduct case pre-fills cache with badDLLP verdict0, goodDLLP and malformed token same step creates witnessed cache divergence and atomic cancellation; both token kinds x four recovery modes, wrap and stalls.','Miter actual6mutants and inherited12public mutants require named semantic failures and compiledsim; the current source count fix permits full17-case XML inventory.'],expected_selected_pytest=29,excluded_MAX4118=2,native_or_controls_executed_by_peer=False,limits='Source-only; actual RTL controls still mandatory before native mapping. No formal proof, timing, fullPHY, or unrestrictedX control equivalence claim.')
(B/'source-only-peer-vco02.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],pin(B/'source-only-peer-vco02.json'))
