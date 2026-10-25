"""Independent corrected focused-harness review; no HDL/native rerun."""
from pathlib import Path
import ast,hashlib,json,runpy,datetime
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
public=json.loads((B/'source-public-freeze01.json').read_text());files=public['files'].copy()
for n,v in files.items():assert pin(R/n)==v
focused=R/'sw/tests/test_pcie_gen3_integrity_v18_commit.py';H=runpy.run_path(str(focused));oldpath=B/'commit-controls01-source.py';old=runpy.run_path(str(oldpath))
current_ast=ast.parse(focused.read_text());prior_ast=ast.parse(oldpath.read_text());fn=lambda m:next(n for n in m.body if isinstance(n,ast.FunctionDef) and n.name=='test_exact_generated_inverse_and_wrapper_bridge')
assert ast.dump(fn(current_ast),include_attributes=False)==ast.dump(fn(prior_ast),include_attributes=False)
helper=ast.get_source_segment(focused.read_text(),fn(current_ast));assert hashlib.sha256(helper.encode()).hexdigest()==public['frozen_inverse_helper']['sha256']
for k,v in H['FAULTS'].items():
 if k!='literal_z_to_x':assert v==old['FAULTS'][k]
assert H['FAULTS']['literal_z_to_x']==('else commit_n=commit_ptr;',"else commit_n=commit_ptr|{PW{1'b0}};")
# Evaluate only the text generator, then compare exact existing native input.
bench=H['parser_miter']();raw=Path('/dev/shm/nssoc-integrity-v18-commit-controls02/test_actual_complete_parser_ar0/tb.v');assert raw.read_text()==bench
assert 'f_state=trial%4;' not in bench and 'f_state=(trial>>12)&3;' in bench
assert 'f_ending=(trial>=16384 && trial%19==0);' in bench
assert 'if(trial%17==0) words[j]=$random;' not in bench
assert 'if(trial>=16384 && trial%17==0) words[j]=$random;' in bench
# Independent arithmetic enumeration proves the actual first-half selector
# indexes, rather than inferring coverage from a descriptive comment.
seen={(trial>>12&3,tuple(trial>>(3*j)&7 for j in range(4))) for trial in range(16384)}
assert len(seen)==4*8**4
assert len(H['REFERENCE']['PARSER_OUTPUTS'])==28 and 'commit_n' in H['REFERENCE']['PARSER_OUTPUTS']
assert all('gold.'+name in bench and 'gate.'+name in bench for name in H['REFERENCE']['PARSER_OUTPUTS'])
assert 'force gold.current_predecode=f_current_predecode;' in bench and 'force gate.current_predecode=f_current_predecode;' in bench
files[str(focused.relative_to(R))]=pin(focused)
f=dict(utc=datetime.datetime.now(datetime.UTC).isoformat(),files=files,baseline=dict(path='hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v17.v',**pin(R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v17.v')),inherited_public_freeze=pin(B/'source-public-freeze01.json'),scope='Final nine sources: immutable V18 product/public sources plus corrected focused harness. Public13 predicates already complete and exact inversehelper unchanged. Corrected focused actual run stillpending; no native launch until its independent positive+six meaningful mutants PASS.')
assert not (B/'source-freeze.json').exists();(B/'source-freeze.json').write_text(json.dumps(f,indent=2)+'\n')
r=dict(status='PASS_V18_FINAL_SOURCE_AND_CORRECTED_FOCUSED_HARNESS_PEER',reviewer='/root/pll_integrity_resume',findings=[],source_freeze=pin(B/'source-freeze.json'),method=pin(Path(__file__)),product_source_peer=pin(B/'source-only-peer-pll01.json'),existing_positive_native_bench=dict(path=str(raw),**pin(raw)),reference_harness=dict(path=str(R/'sw/tests/test_pcie_gen3_integrity_v3_crc.py'),**pin(R/'sw/tests/test_pcie_gen3_integrity_v3_crc.py')),checks=['Eight product/public source pins and inversehelper unchanged; fullV17 inverse established by earlierindependentpeer.', 'Actual generated nativebench equals reviewedtext. First16384 indices form bijection between four states and8^4token tuples; nofirsthalfending or randomword replacement/unknown injections.', 'Second16384 cases exercise unknown state, pointer, header, remaining and literal X/Z controls; both actualparser bodies use same realpredecode companion.', 'Comparison includes28total parser outputs:commit_n and27other outputs, withfourstateinequality. No Python copyofnewreduction.', 'Fiveexistingpriority/fallback/offsetmutants unchanged. Zconversion now targets originalcommit_ptr fallback where literalZcanremainobservable; upperarithmeticvalueequivalentnegative retained inoriginalsupersededcampaign.', 'Initial correlatedbench campaign remains explicitlysuperseded; its earlierpositive/fourdetectedfaults are retained withoutclaiming missinglook/Zcontrols passed. Correctedactualcontrols are pending andremainnativegate.'],native_or_HDL_rerun=False,physical_acceptance=False)
(B/'source-only-peer-pll02.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'freeze':pin(B/'source-freeze.json'),'peer':pin(B/'source-only-peer-pll02.json')}))
