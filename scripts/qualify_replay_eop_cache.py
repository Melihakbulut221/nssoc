import subprocess,json,hashlib
from pathlib import Path
out=Path('out');out.mkdir(exist_ok=True)
rtl=Path('hw/soc/rtl/pcie/soc_pcie_replay_tx.v');original=rtl.read_bytes();rows=[]
variants=[['SOC_PCIE_REPLAY_EOP_CACHE'],['SOC_PCIE_REPLAY_AHEAD','SOC_PCIE_REPLAY_INBANK','SOC_PCIE_RESET_COPIES','SOC_PCIE_REPLAY_WRITE_PREDECODE','SOC_PCIE_REPLAY_EOP_CACHE']]
try:
 for index,flags in enumerate(variants):
  for mutant in [False,True]:
   text=original.decode()
   if mutant:
    old="replay_read_increment=read_pos+1'b1";assert text.count(old)==1
    text=text.replace(old,"replay_read_increment=read_pos+BW'(2)")
   rtl.write_text(text)
   folder=out/f'case-{index}-mutation-{int(mutant)}'
   cmd=['bash','scripts/check_pcie_replay_ahead.sh',str(folder.resolve()),'300000',*flags]
   result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=900)
   (out/f'case-{index}-mutation-{int(mutant)}.log').write_text(result.stdout)
   logs=sorted(folder.glob('d*_seed*.log'));assert len(logs)==6
   if mutant:assert result.returncode!=0 and all('MISMATCH' in p.read_text() for p in logs)
   else:assert result.returncode==0 and all('RESULT PASS' in p.read_text() and 'MISMATCH' not in p.read_text() for p in logs)
   rows.append(dict(flags=flags,mutation=mutant,returncode=result.returncode,expected_verdict_observed=True,source_sha256=hashlib.sha256(text.encode()).hexdigest(),logs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in logs}))
finally:
 rtl.write_bytes(original)
 (out/'qualification.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(original).hexdigest(),cases=rows,full_phy_accepted=False,physical_timing_accepted=False),indent=2))
assert len(rows)==4
