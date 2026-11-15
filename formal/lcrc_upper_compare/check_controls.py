import hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path.cwd()
OUT=ROOT/'formal-result'
OUT.mkdir(exist_ok=True)
RTL='hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v'
files=[RTL,'hw/soc/rtl/pcie/soc_pcie_crc32_byte.v','formal/lcrc_upper_compare/reference.v','formal/lcrc_upper_compare/miter.v']
original={f:(ROOT/f).read_text() for f in files}
rows=[]
mutants=[('baseline',None,None),('wrong_upper_flag',"crc_upper_ok<=crc_next[31:8]==24'h00be26;","crc_upper_ok<=crc_next[31:8]!=24'h00be26;"),('inverted_ready','assign rx_ready_o=rst_ni && state!=EMIT;','assign rx_ready_o=!(rst_ni && state!=EMIT);')]
for name,old,new in mutants:
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        for f,text in original.items():
            if f==RTL and old is not None:
                assert text.count(old)==1
                text=text.replace(old,new)
            p=root/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        ys='read_verilog -formal -sv -DSOC_PCIE_SEQ_RX_REG hw/soc/rtl/pcie/soc_pcie_crc32_byte.v formal/lcrc_upper_compare/reference.v; read_verilog -formal -sv -DSOC_PCIE_SEQ_RX_REG -DSOC_PCIE_CRC_UPPER_COMPARE_REG '+RTL+' formal/lcrc_upper_compare/miter.v; prep -top lcrc_compare_formal -flatten; async2sync; memory_map; opt; sat -seq 4 -set-assumes -set-init-zero -prove-asserts -verify'
        p=subprocess.run(['yosys','-Q','-T','-p',ys],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
        log=p.stdout.decode(errors='replace');(OUT/(name+'.log')).write_text(log)
        passed=p.returncode==0 and 'SAT proof finished - no model found: SUCCESS!' in log
        rejected=p.returncode!=0 and 'ERROR: Called with -verify and proof did fail!' in log
        rows.append(dict(case=name,returncode=p.returncode,baseline_pass=passed,mutation_rejected=rejected,log_sha256=hashlib.sha256(p.stdout).hexdigest()))
        (OUT/'controls.json').write_text(json.dumps(dict(scope='Four-step bounded baseline plus negative controls; NOT induction or full protocol proof',cases=rows),indent=2))
        assert passed if old is None else rejected, (name,p.returncode,log[-1000:])
assert all((ROOT/f).read_text()==text for f,text in original.items())
print(json.dumps(rows))
