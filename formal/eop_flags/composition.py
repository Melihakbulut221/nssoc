import subprocess,pathlib,json,hashlib,tempfile
# Re-prove the actual flags and mutation controls before any substitution.
subprocess.run(['python3','formal/eop_flags/prove.py'],check=True)
out=pathlib.Path('eop-flag-proof');source=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v').read_text()
assert hashlib.sha256(source.encode()).hexdigest()=='a83699c6311ba0ac6414060f68699ee29510bf5ed99fee64f92168546bf16223'
lemma=json.loads((out/'result.json').read_text());assert len(lemma['cases'])==6 and all(r['passed']for r in lemma['cases'])
candidate=source
a='assign out_eop_o=select_dllp ? eop_dllp_q : eop_tlp_q;'
b="assign out_eop_o=select_dllp ? (output_index+1'b1)==CW'(dllp_length) : output_index==head_last;"
assert candidate.count(a)==1;candidate=candidate.replace(a,b)
assert {(r['dw'],r['slots'],r['mutation']) for r in lemma['cases']}=={(dw,slots,m)for dw,slots in [(8,2),(4,1)]for m in ['none','tlp','dllp']}
reference=pathlib.Path('formal/eop_flags/reference.v').read_text()
assert hashlib.sha256(reference.encode()).hexdigest()=='865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5'
flags='-DSYNTHESIS -DSOC_PCIE_RX_READ2 -DSOC_PCIE_RESET_COPIES -DSOC_PCIE_RX_COMMIT_COPIES -DSOC_PCIE_RX_CURSOR_LOCAL_RESET -DSOC_PCIE_RX_LOCAL_LANE_NEXT -DSOC_PCIE_RX_DLLP_LAST_COMPARE'
rows=[]
for dw,slots in [(8,2),(4,1)]:
 name=f'dw{dw}-s{slots}-composition'
 with tempfile.TemporaryDirectory()as td:
  wd=pathlib.Path(td);(wd/'gold.v').write_text(reference);(wd/'gate.v').write_text(candidate)
  parts=[]
  for role in ('gold','gate'):
   parts.append('read_verilog -sv '+flags+(' -DSOC_PCIE_RX_EOP_FLAGS'if role=='gate'else'')+' '+role+'.v; setattr -mod -unset keep_hierarchy; chparam -set MAX_TLP_DWORDS '+str(dw)+' -set SLOTS_PER_CLASS '+str(slots)+' -set COMPLETER_ONLY 1 soc_pcie_rx_credit; prep -top soc_pcie_rx_credit -flatten; memory_map; opt; clk2fflogic; opt; rename soc_pcie_rx_credit '+role+'; design -stash '+role)
  parts+=['design -copy-from gold -as gold gold','design -copy-from gate -as gate gate','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple','equiv_induct -seq 4','equiv_status','equiv_status -assert']
  recipe='; '.join(parts);(out/(name+'.ys')).write_text(recipe)
  with(out/(name+'.log')).open('w')as log:r=subprocess.run(['yosys','-Q','-T','-p',recipe],cwd=wd,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
  text=(out/(name+'.log')).read_text();passed=r.returncode==0 and 'Equivalence successfully proven!'in text
  rows.append(dict(dw=dw,slots=slots,passed=passed,returncode=r.returncode))
  (out/'composition.json').write_text(json.dumps(dict(cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest(),reference_sha256=hashlib.sha256(reference.encode()).hexdigest(),scope='Composition: freshly proven actual EOP state invariants with arbitrary next-head value substituted only in temporary candidate predicate reads; full queue module equivalence under exact mapped optional switches, DW8/S2 and DW4/S1. Initial reset/zero initialization inherited from lemma, predicates proven outside reset/init only; no arbitrary power-up or physical timing claim.'),indent=2))
  assert passed,(name,text[-2000:])
assert pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v').read_text()==source
