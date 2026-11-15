import pathlib,subprocess,json,re,hashlib
root=pathlib.Path.cwd();out=root/'credit-formal';out.mkdir()
ref=root/'formal/credit_sign/reference.v';src=root/'hw/soc/rtl/pcie/soc_pcie_credit_tx.v'
s=src.read_text();assert s.count('module soc_pcie_credit_tx (')==1
(out/'gate.v').write_text(s.replace('module soc_pcie_credit_tx (','module gate ('))
(out/'gold.v').write_bytes(ref.read_bytes())
recipe='read_verilog -sv -DSYNTHESIS gold.v; read_verilog -sv -DSYNTHESIS -DSOC_PCIE_CREDIT_DATA_SIGN_REG gate.v; proc; memory_map; opt; clk2fflogic; opt; equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple; equiv_induct -seq 4; equiv_status -assert'
(out/'proof.ys').write_text(recipe)
(out/'version.txt').write_bytes(subprocess.check_output(['yosys','-V']))
with (out/'proof.log').open('w') as log:
    p=subprocess.run(['yosys','-Q','-T','-s','proof.ys'],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
s=(out/'proof.log').read_text();counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',s)
passed=p.returncode==0 and bool(counts) and int(counts[-1][0])>0 and int(counts[-1][1])==0 and 'Equivalence successfully proven!' in s
(out/'result.json').write_text(json.dumps(dict(passed=passed,returncode=p.returncode,counts=counts,scope='DATA_SIGN_REG versus exact mapped-source credit RTL with CREDIT_PICK disabled on both; explicit clock and async reset events via clk2fflogic. CREDIT_PICK combination separately cosim-tested, not full-chip timing or PHY proof',outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()}),indent=2))
assert passed,s[-2000:]
