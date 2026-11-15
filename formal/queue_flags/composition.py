import subprocess,pathlib,json,hashlib,tempfile
# Re-prove the actual flags and mutation controls before any substitution.
subprocess.run(['python3','formal/queue_flags/prove.py'],check=True)
out=pathlib.Path('queue-flag-proof');source=pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v').read_text()
assert hashlib.sha256(source.encode()).hexdigest()=='ea123da56f450bdde9183b43083ca6c8df3086494feff54be7bf9a201ecbc391'
lemma=json.loads((out/'result.json').read_text());assert len(lemma['cases'])==4 and all(r['passed']for r in lemma['cases'])
candidate=source
for a,b in [('wire queue_room=count_room_q;',"wire queue_room=32'(qcount)<SLOTS;"),('wire queue_empty=count_empty_q;','wire queue_empty=qcount==0;'),('wire queue_one=count_one_q;','wire queue_one=qcount==1;')]:
 assert candidate.count(a)==1;candidate=candidate.replace(a,b)
reference=pathlib.Path('formal/queue_flags/reference.v').read_text()
flags='-DSYNTHESIS -DSOC_PCIE_RX_READ2 -DSOC_PCIE_RESET_COPIES -DSOC_PCIE_RX_COMMIT_COPIES -DSOC_PCIE_RX_CURSOR_LOCAL_RESET -DSOC_PCIE_RX_LOCAL_LANE_NEXT -DSOC_PCIE_RX_DLLP_LAST_COMPARE'
rows=[]
for dw,slots in [(8,2),(4,1)]:
 name=f'dw{dw}-s{slots}-composition'
 with tempfile.TemporaryDirectory()as td:
  wd=pathlib.Path(td);(wd/'gold.v').write_text(reference);(wd/'gate.v').write_text(candidate)
  parts=[]
  for role in ('gold','gate'):
   parts.append('read_verilog -sv '+flags+(' -DSOC_PCIE_RX_COUNT_FLAGS'if role=='gate'else'')+' '+role+'.v; setattr -mod -unset keep_hierarchy; chparam -set MAX_TLP_DWORDS '+str(dw)+' -set SLOTS_PER_CLASS '+str(slots)+' -set COMPLETER_ONLY 1 soc_pcie_rx_credit; prep -top soc_pcie_rx_credit -flatten; memory_map; opt; clk2fflogic; opt; rename soc_pcie_rx_credit '+role+'; design -stash '+role)
  parts+=['design -copy-from gold -as gold gold','design -copy-from gate -as gate gate','equiv_make gold gate equiv','hierarchy -top equiv','equiv_simple','equiv_induct -seq 4','equiv_status','equiv_status -assert']
  recipe='; '.join(parts);(out/(name+'.ys')).write_text(recipe)
  with(out/(name+'.log')).open('w')as log:r=subprocess.run(['yosys','-Q','-T','-p',recipe],cwd=wd,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
  text=(out/(name+'.log')).read_text();passed=r.returncode==0 and 'Equivalence successfully proven!'in text
  rows.append(dict(dw=dw,slots=slots,passed=passed,returncode=r.returncode))
  (out/'composition.json').write_text(json.dumps(dict(cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest(),reference_sha256=hashlib.sha256(reference.encode()).hexdigest(),scope='Composition: freshly proven arbitrary-commit/remove count invariants substituted only in temporary candidate predicate reads; full queue module equivalence under exact mapped optional switches, DW8/S2 and DW4/S1. Initial reset/zero initialization inherited from lemma; not arbitrary power-up or physical timing.'),indent=2))
  assert passed,(name,text[-2000:])
assert pathlib.Path('hw/soc/rtl/pcie/soc_pcie_rx_credit.v').read_text()==source
