#!/usr/bin/env python3
"""SAT for address factorization, plus source guards for capture control.
This is NOT a full sequential proof of the replay protocol or timing signoff.
"""
import hashlib,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1]
out=root/'out';out.mkdir(exist_ok=True)
s=(root/'hw/soc/rtl/pcie/soc_pcie_replay_tx.v').read_text()
assert s.count("write_group<=0;")==3
assert s.count("write_group<={{(WRITE_GROUPS-1){1'b0}},1'b1} << (capture_address >> 4);")==2
assert s.count("write_low<=16'b1 << capture_address[3:0];")==1
assert 'if(write_group[write_byte/16] && write_low[write_byte%16])' in s
# Every existing write_valid update must have exactly its corresponding
# group update immediately following; neither condition nor latency changes.
import re
updates=re.findall(r'write_valid<=([01]);\n`ifdef SOC_PCIE_REPLAY_WRITE_PREDECODE\n            write_group<=([^;]+);\n`endif',s)
assert len(updates)==5 and len(re.findall(r'write_valid\s*<=',s))==5
rows=[]
for count in (36,44,76,152,608,32768):
    aw=(count-1).bit_length();groups=(count+15)//16
    # Arbitrary selected byte instead of enumerating 32768 outputs.
    # Out-of-range addresses must never select a real byte.
    for mutation in (False,True):
        text=f"""module m(input [{aw-1}:0] a,i,input v,output ok);
wire reference=v && a==i && i<{count};
wire candidate=v && (a >> 4)==(i >> 4) && a[3:0]==(i[3:0] ^ 4'd{int(mutation)}) && i<{count};
assign ok=reference==candidate;
endmodule
"""
        stem=f'factor-{count}-{int(mutation)}'
        path=out/(stem+'.v');path.write_text(text)
        command=['yosys','-Q','-T','-p',f'read_verilog {path}; prep -top m; flatten; sat -verify -prove ok 1 -show a,i,v']
        r=subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
        (out/(stem+'.log')).write_text(r.stdout)
        if mutation: assert r.returncode!=0 and 'proof did fail' in r.stdout
        else: assert r.returncode==0 and 'SUCCESS' in r.stdout
        rows.append(dict(bytes=count,mutation=mutation,expected_verdict_observed=True,log_sha256=hashlib.sha256(r.stdout.encode()).hexdigest()))
(out/'factorization.json').write_text(json.dumps(dict(status='PASS',scope='Boolean factorization and five source-update guards only; sequential behavior tested separately',rtl_sha256=hashlib.sha256(s.encode()).hexdigest(),cases=rows),indent=2)+'\n')
