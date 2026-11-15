import pathlib,subprocess,json,re,hashlib,tempfile
root=pathlib.Path.cwd();out=root/'lcrc-composition';out.mkdir()
src=root/'hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v';ref=root/'formal/lcrc_upper_compare/reference.v';crc=root/'hw/soc/rtl/pcie/soc_pcie_crc32_byte.v'
original=src.read_text();reference=ref.read_text();crc_text=crc.read_text();rows=[]
def save():
    (out/'result.json').write_text(json.dumps(dict(cases=rows,scope='Compositional proof: actual candidate invariant under initial reset/zero initialization, then full-module equivalence with only that proven predicate substituted. Default8DW/SEQ_RX_REG; no physical or arbitrary power-up qualification',source_sha256=hashlib.sha256(original.encode()).hexdigest(),reference_sha256=hashlib.sha256(reference.encode()).hexdigest(),outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()and p.name!='result.json'}),indent=2))
def run(name,files,recipe,expect):
    with tempfile.TemporaryDirectory()as td:
        wd=pathlib.Path(td)
        for f,s in files.items():(wd/f).write_text(s);(out/(name+'-'+f)).write_text(s)
        (out/(name+'.ys')).write_text(recipe)
        code=None;error=None
        try:
            with(out/(name+'.log')).open('w')as log:p=subprocess.run(['yosys','-Q','-T','-p',recipe],cwd=wd,stdout=log,stderr=subprocess.STDOUT,timeout=900)
            code=p.returncode
        except subprocess.TimeoutExpired as exc:error=str(exc)
        log=(out/(name+'.log')).read_text()
        if expect=='induction':passed=code==0 and 'Induction step proven: SUCCESS!' in log
        elif expect=='reject':passed=code is not None and code!=0 and 'ERROR: Called with -verify and proof did fail!' in log
        else:passed=code==0 and 'Equivalence successfully proven!'in log
        rows.append(dict(case=name,expect=expect,passed=passed,returncode=code,error=error));save()
        assert passed,(name,error,log[-1500:])
(out/'version.txt').write_bytes(subprocess.check_output(['yosys','-V']))
wrapper='module lemma(input clk,rst_n,input[7:0] data,input sop,eop,error,valid,ready);\nsoc_pcie_lcrc_rx dut(.clk_i(clk),.rst_ni(rst_n),.rx_data_i(data),.rx_sop_i(sop),.rx_eop_i(eop),.rx_error_i(error),.rx_valid_i(valid),.tlp_ready_i(ready));\nalways @* if($initstate) assume(!rst_n);\nendmodule\n'
old="always @* if (rst_ni) assert(crc_upper_ok==(crc[31:8]==24'h00be26));"
assert original.count(old)==1
lemma=original.replace(old,old.replace('if (rst_ni) ',''))
recipe='read_verilog -formal -sv -DSOC_PCIE_SEQ_RX_REG -DSOC_PCIE_CRC_UPPER_COMPARE_REG candidate.v crc.v wrapper.v; prep -top lemma -flatten; clk2fflogic; memory_map; opt; sat -seq 3 -tempinduct -maxsteps 4 -set-assumes -set-init-zero -prove-asserts -verify'
run('invariant',{'candidate.v':lemma,'crc.v':crc_text,'wrapper.v':wrapper},recipe,'induction')
mutation="crc_upper_ok<=crc_next[31:8]==24'h00be26;";assert lemma.count(mutation)==1
bad=lemma.replace(mutation,mutation.replace('==','!='))
run('wrong_flag',{'candidate.v':bad,'crc.v':crc_text,'wrapper.v':wrapper},recipe.replace('-tempinduct -maxsteps 4 ',''),'reject')
# Substitute ONLY after the exact candidate invariant and its negative control pass.
old='!rx_sop_i && crc_upper_ok &&';assert original.count(old)==1
rewritten=original.replace(old,"!rx_sop_i && (crc[31:8]==24'h00be26) &&")
assert rewritten.count('module soc_pcie_lcrc_rx #(')==1 and reference.count('module soc_pcie_lcrc_rx_ref #(')==1
files={'gate.v':rewritten.replace('module soc_pcie_lcrc_rx #(','module gate #('),'gold.v':reference.replace('module soc_pcie_lcrc_rx_ref #(','module gold #('),'crc.v':crc_text}
recipe='read_verilog -sv -DSYNTHESIS -DSOC_PCIE_SEQ_RX_REG gold.v crc.v; read_verilog -sv -DSYNTHESIS -DSOC_PCIE_SEQ_RX_REG -DSOC_PCIE_CRC_UPPER_COMPARE_REG gate.v; proc; memory_map; opt; flatten; clk2fflogic; opt; equiv_make gold gate equiv; hierarchy -top equiv; equiv_simple; equiv_induct -seq 4; equiv_status; equiv_status -assert'
run('full_module',files,recipe,'equivalence')
assert src.read_text()==original and ref.read_text()==reference
save()
