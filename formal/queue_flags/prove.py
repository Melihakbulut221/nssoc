import pathlib,subprocess,json,hashlib,tempfile
root=pathlib.Path.cwd();out=root/'queue-flag-proof';out.mkdir()
p=root/'hw/soc/rtl/pcie/soc_pcie_rx_credit.v';original=p.read_text();rows=[]
source=original
replacements={
 '    wire commit=|commit_slot;':'    (* anyseq *) reg commit;',
 '    wire remove=waiting && (packet_accepted_i || packet_duplicate_i || packet_rejected_i);':'    (* anyseq *) reg remove;',
 '    reg count_empty_q,count_one_q,count_room_q;':"    reg count_empty_q,count_one_q,count_room_q;\n    always @* assert({count_empty_q,count_one_q,count_room_q}=={qcount==0,qcount==1,32'(qcount)<SLOTS});"}
for a,b in replacements.items():assert source.count(a)==1;source=source.replace(a,b)
flags='-DSYNTHESIS -DSOC_PCIE_RX_COUNT_FLAGS -DSOC_PCIE_RX_READ2 -DSOC_PCIE_RESET_COPIES -DSOC_PCIE_RX_COMMIT_COPIES -DSOC_PCIE_RX_CURSOR_LOCAL_RESET -DSOC_PCIE_RX_LOCAL_LANE_NEXT -DSOC_PCIE_RX_DLLP_LAST_COMPARE'
(out/'version.txt').write_bytes(subprocess.check_output(['yosys','-V']))
for dw,slots in [(8,2),(4,1)]:
    wrapper=f"""module lemma(input clk,rst_n,rst_copy_n,link,training,initialized,input[7:0] data,input sop,eop,valid,dllp,error,ready,accepted,duplicate,rejected);
soc_pcie_rx_credit #(.MAX_TLP_DWORDS({dw}),.SLOTS_PER_CLASS({slots}),.COMPLETER_ONLY(1)) dut(.clk_i(clk),.rst_ni(rst_n),.rst_copy_ni(rst_copy_n),.link_up_i(link),.training_i(training),.initialized_i(initialized),.rx_data_i(data),.rx_sop_i(sop),.rx_eop_i(eop),.rx_valid_i(valid),.rx_dllp_i(dllp),.rx_error_i(error),.out_ready_i(ready),.packet_accepted_i(accepted),.packet_duplicate_i(duplicate),.packet_rejected_i(rejected));
always @* if($initstate) assume(!rst_n);
endmodule
"""
    for mutant in (False,True):
        name=f'dw{dw}-s{slots}-'+('wrong-empty' if mutant else 'positive')
        candidate=source
        if mutant:
            old='count_empty_q<=count_next==0;';assert candidate.count(old)==1;candidate=candidate.replace(old,'count_empty_q<=count_next!=0;')
        with tempfile.TemporaryDirectory()as td:
            wd=pathlib.Path(td);(wd/'candidate.v').write_text(candidate);(wd/'wrapper.v').write_text(wrapper)
            (out/(name+'-candidate.v')).write_text(candidate);(out/(name+'-wrapper.v')).write_text(wrapper)
            recipe='read_verilog -formal -sv '+flags+' candidate.v wrapper.v; prep -top lemma -flatten; clk2fflogic; memory_map; opt; sat -seq 4 '+(''if mutant else '-tempinduct -maxsteps 4 ')+'-set-assumes -set-init-zero -prove-asserts -verify'
            (out/(name+'.ys')).write_text(recipe);code=None;error=None
            try:
                with(out/(name+'.log')).open('w')as log:run=subprocess.run(['yosys','-Q','-T','-p',recipe],cwd=wd,stdout=log,stderr=subprocess.STDOUT,timeout=900)
                code=run.returncode
            except subprocess.TimeoutExpired as exc:error=str(exc)
            log=(out/(name+'.log')).read_text()
            passed=(code is not None and code!=0 and 'ERROR: Called with -verify and proof did fail!'in log)if mutant else(code==0 and 'Induction step proven: SUCCESS!'in log)
            rows.append(dict(dw=dw,slots=slots,mutation=mutant,passed=passed,returncode=code,error=error))
            (out/'result.json').write_text(json.dumps(dict(cases=rows,source_sha256=hashlib.sha256(original.encode()).hexdigest(),scope='Three queue count predicates from actual RTL; commit/remove abstracted to independent anyseq in both original count updates and flag updates, a behavioral superset including wrap and simultaneous operations. Initial reset/zero initialization, explicit clock/reset events. NOT full queue equivalence or physical timing.',outputs={f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in out.iterdir()if f.is_file()and f.name!='result.json'}),indent=2))
            assert passed,(name,error,log[-1200:])
assert p.read_text()==original
