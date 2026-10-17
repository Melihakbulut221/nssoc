from pathlib import Path
import ast
R=Path.cwd();B=Path(__file__).resolve().parent
observer=(B/'context_observer01.vh').read_text()
p=R/'sw/tests/test_pcie_gen3_integrity_v24_miter.py';s=p.read_text();a='\ndef pin(p):';assert s.count(a)==1
s=s.replace(a,'\nCONTEXT_OBSERVER = '+repr(observer)+'\n'+a)
s=s.replace('    compare += HEADER_OBSERVER','    compare += HEADER_OBSERVER\n    compare += CONTEXT_OBSERVER')
s=s.replace('    (out / "miter-scope.json").write_text(','''    text = (out / "simulation.log").read_text()
    fields = re.search(r"V24_CONTEXT_WITNESSES current=(\\d+) next=(\\d+) shifts=(\\d+) promotions=(\\d+) changed=(\\d+) concurrent=(\\d+) modes=(\\d+) carry=(\\d+)/(\\d+)/(\\d+)/(\\d+) eds=(\\d+)", text)
    assert fields and all(int(fields.group(i))>0 for i in (1,3,7,8,9,10,11,12)), "Actual consumed/context/carry/EDS witnesses required"
    (out / "miter-scope.json").write_text(''')
p.write_text(s);ast.parse(s)
p=R/'sw/tests/test_pcie_gen3_integrity_v24_block_burst.py';s=p.read_text()
s=s.replace('import zlib','import zlib\nimport pytest')
faults={
 'context_capture_zero':('current_token_context<=input_token_context;','current_token_context<=0;'),
 'context_next_uses_current':('next_token_context<=input_token_context;','next_token_context<=current_token_context;'),
 'context_shift_wrong':('current_token_context<={empty_token_context[95:0],current_token_context[383:96]};','current_token_context<={empty_token_context[95:0],current_token_context[287:0]};'),
 'context_promote_stale':('current_token_context<=next_token_context;','current_token_context<=current_token_context;'),
}
s=s.replace('\n\ndef pin(path):','\n\nCONTEXT_FAULTS = '+repr(faults)+'\n\ndef pin(path):')
a='    lines += [f"reg [511:0] blocks[0:{len(blocks)-1}];",';assert s.count(a)==1
s=s.replace(a,'''    observer = runpy.run_path(str(ROOT / "sw/tests/test_pcie_gen3_integrity_v24_miter.py"))["CONTEXT_OBSERVER"]
    lines.append(observer.replace("candidate.framer.", "candidate.").replace("reference.framer.", "reference."))
'''+a)
a=' $display("PASS_V24_FRAMER_BURST';assert s.count(a)==1
s=s.replace(a,''' if(v24_context_current_checks<1 || v24_context_next_checks<1 || v24_context_shifts<1 ||
    v24_context_promotions<2 || v24_context_changed_promotions<1 || v24_context_concurrent<1 ||
    v24_context_mode_checks<1 || v24_context_final_eds<1)
   $fatal(1,"V24_CONTEXT_BURST_WITNESS");
'''+a)
s=s.replace('assert fault in (None, "header_promote_stale")','assert fault in (None, "header_promote_stale", *CONTEXT_FAULTS)')
s=s.replace('            old, new = module["HEADER_FAULTS"][fault]','            old, new = CONTEXT_FAULTS[fault] if fault in CONTEXT_FAULTS else module["HEADER_FAULTS"][fault]')
s=s.replace('assert result.returncode != 0 and "V24_FRAMER_PROMOTION_RELATION" in text','assert result.returncode != 0 and ("V24_CONTEXT_BANK" in text if fault in CONTEXT_FAULTS else "V24_FRAMER_PROMOTION_RELATION" in text)')
s += '''\n\n@pytest.mark.parametrize("fault", list(CONTEXT_FAULTS))
def test_actual_context_bank_fault_detected(tmp_path, fault):
    run_burst(tmp_path/"burst", fault)
'''
p.write_text(s);ast.parse(s)
print('Added independent reference-bank/context/actual-mode observer, mandatory carry/EDS witnesses and four real full-framer bank mutants. No HDL executed.')
