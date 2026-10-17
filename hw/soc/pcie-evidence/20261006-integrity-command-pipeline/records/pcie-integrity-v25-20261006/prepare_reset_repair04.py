from pathlib import Path
import hashlib,json,difflib,runpy
R=Path.cwd();B=Path(__file__).resolve().parent
f=json.loads((B/'source-freeze03.json').read_text())
def pin(p):return dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
for n,v in f['product_sources'].items():assert pin(R/n)==v,n
changes={}
def write(p,s):
 old=p.read_text()
 if old!=s:
  changes[str(p.relative_to(R))]=dict(before=pin(p),before_body=old,after_body=s,full_diff=''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True))))
  p.write_text(s);changes[str(p.relative_to(R))]['after']=pin(p)
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
p=R/'scripts/generate_pcie_integrity_command_v25.py';s=p.read_text()
s=once(s,'   if(step) begin\n     command_address','   if(rst_ni && step) begin\n     command_address')
s=once(s,'     if(enabled) begin\n       command_valid<=0;','     if(rst_ni && enabled) begin\n       command_valid<=0;')
s=once(s,'       if(enabled && command_valid) begin','       if(rst_ni && enabled && command_valid) begin')
s=once(s,'if(enabled && active_o && command_valid) slot_verdict','if(rst_ni && enabled && active_o && command_valid) slot_verdict')
s=once(s,' // owner overwrites every field. A bubble consumes the old command only once.',' // owner overwrites every field. A bubble consumes the old command only once.\n // Direct reset checks also prevent stale derived-enable writes at 1-to-X/Z\n // asynchronous reset transitions; they are redundant for known controls.')
write(p,s)
api=runpy.run_path(str(p));actual,ledger=api['generate']();write(api['TARGET'],actual)
for name in ('sw/tests/test_pcie_gen3_integrity_v25_command.py','sw/tests/test_pcie_gen3_integrity_v25_architecture.py'):
 p=R/name;s=p.read_text()
 s=s.replace("'if(enabled && command_valid)","'if(rst_ni && enabled && command_valid)")
 s=s.replace("'if(enabled && command_valid &&", "'if(rst_ni && enabled && command_valid &&")
 if name.endswith('_command.py'):
  s=once(s,"'if(enabled) begin\\n       command_valid<=0;'","'if(rst_ni && enabled) begin\\n       command_valid<=0;'")
  s=once(s,' reg [4:0] held_commit;',' reg [4:0] held_commit;\n reg [297:0] held_command;')
  bundle='{dut.command_address,dut.command_commit,dut.command_data,dut.command_keep,dut.command_sop,dut.command_eop,dut.command_dllp,dut.command_sequence,dut.command_tags,dut.command_verdict_enable,dut.command_verdict_tags,dut.command_verdict_value}'
  s=once(s,'   held_commit=dut.visible_commit_ptr;',f'   held_commit=dut.visible_commit_ptr;held_command={bundle};')
  s=once(s,'    $fatal(1,"V25_COMMAND_UNKNOWN_CONTROL_HOLD kind=%0d",t);','    $fatal(1,"V25_COMMAND_UNKNOWN_CONTROL_HOLD kind=%0d",t);\n   if('+bundle+' !== held_command)\n     $fatal(1,"V25_COMMAND_UNKNOWN_CONTROL_PAYLOAD_HOLD kind=%0d",t);')
  s=once(s,"    ('verdict_priority_reversed',", "    ('reset_apply_guard_removed', 'if(rst_ni && enabled && command_valid) begin', 'if(enabled && command_valid) begin', 'V25_COMMAND_UNKNOWN_CONTROL_WRITES'),\n    ('verdict_priority_reversed',")
 write(p,s)
p=R/'sw/tests/test_pcie_gen3_integrity_v25_block_burst.py';s=p.read_text()
s=once(s,'    blocks, expected, packets = stimulus(minimum or pending_faults)','    # Pending-fault prelude uses the already passing normal ring64/stall stream.\n    # The separate 128-packet ring16/ready1 cadence and explicit ready0 overflow\n    # boundary remain unchanged; a dense unbounded stalled prelude can overflow.\n    blocks, expected, packets = stimulus(minimum)')
write(p,s)
(B/'reset-repair-source-supplement04.json').write_text(json.dumps(dict(status='V25_DIRECT_RESET_COMMAND_GATES_AND_FAULT_PRELUDE_CORRECTION_REQUIRES_PEER',parent_freeze=pin(B/'source-freeze03.json'),failed_capture=pin(B/'failed-controls01/validation.json'),changes=changes,whole_framer_ledger=ledger,diagnostics={n:pin(B/n/'result.json') for n in ('burst-diagnostic01','burst-baseline-diagnostic02','component-diagnostic01')},scope='Known-state behavior unchanged by four direct rst_ni qualifiers. Explicit asynchronous nontrue-reset command hold repair; not full legacy unknown-state equivalence. Existing strict 10 X/Z hold/resume cases unchanged, pending bundle assertion and actual apply-guard-removal negative added. Entire functional suite must rerun because RTL changed. Dense ring16 ready1 and intended badblock/capacity/restart gates retained.'),indent=2)+'\n')
print({n:v['after'] for n,v in changes.items()})
