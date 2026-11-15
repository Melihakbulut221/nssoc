import pathlib,subprocess,json,hashlib,tempfile
root=pathlib.Path.cwd();out=root/'formal-result';out.mkdir(exist_ok=True)
files=['hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v','formal/lcrc_upper_compare/reference.v','formal/lcrc_upper_compare/miter.v','hw/soc/rtl/pcie/soc_pcie_crc32_byte.v']
sources={f:(root/f).read_text() for f in files}
with tempfile.TemporaryDirectory() as td:
    work=pathlib.Path(td)
    for f,s in sources.items():
        if f.endswith(('soc_pcie_lcrc_rx.v','reference.v')):
            marker=');\n    localparam integer CAP='
            assert s.count(marker)==1
            s=s.replace(marker,',output wire [2+3*$clog2(MAX_TLP_DWORDS*4+7)+32+2*MAX_TLP_DWORDS*4+16+8*MAX_TLP_DWORDS*4-1:0] formal_state_o\n'+marker)
            marker='endmodule'
            assert s.count(marker)==1
            instrumentation="""
    localparam integer FORMAL_PREFIX=2+3*CW+32+2*CAP+16;
    assign formal_state_o[FORMAL_PREFIX-1:0]={state,received,length,index,crc,write_at,cursor,write_data,out_byte};
    genvar formal_byte;
    generate for(formal_byte=0;formal_byte<CAP;formal_byte=formal_byte+1) begin: formal_bytes
        assign formal_state_o[FORMAL_PREFIX+formal_byte*8+:8]=bytes[formal_byte];
    end endgenerate
"""
            s=s.replace(marker,instrumentation+marker)
        elif f.endswith('miter.v'):
            marker=' wire ao,bo;';assert s.count(marker)==1
            s=s.replace(marker,marker+'\n wire [387:0] a_state,b_state;')
            assert s.count('a(.clk_i(clk)')==1 and s.count('b(.clk_i(clk)')==1
            s=s.replace('a(.clk_i(clk)','a(.formal_state_o(a_state),.clk_i(clk)').replace('b(.clk_i(clk)','b(.formal_state_o(b_state),.clk_i(clk)')
            marker='  if ($initstate) assume(!rst_n);';assert s.count(marker)==1
            s=s.replace(marker,marker+'\n  assert(a_state==b_state);')
        p=work/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
        (out/(pathlib.Path(f).name)).write_text(s)
    ys='read_verilog -formal -sv -DSOC_PCIE_SEQ_RX_REG hw/soc/rtl/pcie/soc_pcie_crc32_byte.v formal/lcrc_upper_compare/reference.v; read_verilog -formal -sv -DSOC_PCIE_SEQ_RX_REG -DSOC_PCIE_CRC_UPPER_COMPARE_REG hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v formal/lcrc_upper_compare/miter.v; prep -top lcrc_compare_formal -flatten; async2sync; memory_map; opt; sat -seq 2 -tempinduct -maxsteps 8 -set-assumes -set-init-zero -prove-asserts -verify'
    (out/'command.ys').write_text(ys)
    (out/'version.txt').write_bytes(subprocess.check_output(['yosys','-V']))
    with (out/'proof.log').open('w') as log:
        p=subprocess.run(['yosys','-Q','-T','-p',ys],cwd=work,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
    log=(out/'proof.log').read_text()
    success=p.returncode==0 and 'Induction step proven: SUCCESS!' in log
    (out/'result.json').write_text(json.dumps(dict(success=success,returncode=p.returncode,method='Assert all common sequential state equality in addition to unchanged boundary properties and CRC upper flag invariant; no added assumptions',scope='Default MAX_TLP_DWORDS=8, initial reset and zero-initialized memories, no arbitrary power-up or physical timing claim',source_sha256={f:hashlib.sha256(s.encode()).hexdigest() for f,s in sources.items()},outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}),indent=2))
    assert success,log[-3000:]
assert all((root/f).read_text()==s for f,s in sources.items())
