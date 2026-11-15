import pathlib,subprocess,json,re,hashlib
root=pathlib.Path.cwd();out=root/'lcrc-equivalence';out.mkdir()
ref=root/'formal/lcrc_upper_compare/reference.v';src=root/'hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v';crc=root/'hw/soc/rtl/pcie/soc_pcie_crc32_byte.v'
s=ref.read_text();assert s.count('module soc_pcie_lcrc_rx_ref #(')==1
(out/'gold.v').write_text(s.replace('module soc_pcie_lcrc_rx_ref #(','module gold #('))
s=src.read_text();assert s.count('module soc_pcie_lcrc_rx #(')==1
(out/'gate.v').write_text(s.replace('module soc_pcie_lcrc_rx #(','module gate #('));(out/'crc.v').write_bytes(crc.read_bytes())
recipe='read_verilog -sv -DSYNTHESIS -DSOC_PCIE_SEQ_RX_REG gold.v crc.v; read_verilog -sv -DSYNTHESIS -DSOC_PCIE_SEQ_RX_REG -DSOC_PCIE_CRC_UPPER_COMPARE_REG gate.v; proc; memory_map; opt; flatten; clk2fflogic; opt; equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple; equiv_induct -seq 4; equiv_status -assert'
(out/'proof.ys').write_text(recipe);(out/'version.txt').write_bytes(subprocess.check_output(['yosys','-V']))
error=None;code=None
try:
    with (out/'proof.log').open('w') as log:
        p=subprocess.run(['yosys','-Q','-T','-s','proof.ys'],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
    code=p.returncode
except subprocess.TimeoutExpired as exc:
    error=str(exc)
s=(out/'proof.log').read_text();counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',s)
passed=code==0 and bool(counts) and int(counts[-1][0])>0 and int(counts[-1][1])==0 and 'Equivalence successfully proven!' in s
(out/'result.json').write_text(json.dumps(dict(passed=passed,returncode=code,error=error,counts=counts,scope='Default 8DW full LCRC module equivalence with SEQ_RX_REG on both, UPPER_COMPARE_REG on candidate; explicit clock/reset events via clk2fflogic, all matched equivalence points must prove. Not physical timing or full PCIe compliance',outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()}),indent=2))
assert passed,error or s[-2000:]
