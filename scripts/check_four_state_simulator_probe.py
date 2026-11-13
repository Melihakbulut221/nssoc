# SPDX-License-Identifier: Apache-2.0
import json,pathlib,re,subprocess,time,hashlib
out=pathlib.Path('out');out.mkdir(exist_ok=True)
source=pathlib.Path('hw/soc/tb/tb_four_state_simulator_probe.v').resolve()
engines={'icarus':['iverilog','-g2005','-s','tb','-o','probe.vvp',str(source)],'cvc':['/tmp/cvc/build64/cvc64',str(source)]}
records={}
for name,compile_cmd in engines.items():
    folder=out/name;folder.mkdir()
    commands=[compile_cmd,(['vvp','probe.vvp'] if name=='icarus' else ['./cvcsim'])]
    for i,cmd in enumerate(commands):
        start=time.monotonic();p=subprocess.run(cmd,cwd=folder,capture_output=True,text=True,timeout=120)
        text=p.stdout+p.stderr;(folder/('compile.log' if i==0 else 'run.log')).write_text(text)
        assert p.returncode==0,(name,cmd,p.returncode,text)
    matches=re.findall(r'^PROBE_RESULT checks=(\d+) errors=(\d+)$',text,re.M)
    assert matches==[('21','0')] and not re.search(r'^FAIL',text,re.M),(name,matches,text)
    records[name]={'trace':re.findall(r'^TRACE .*$',text,re.M),'verdict':matches,'simulation_seconds':time.monotonic()-start}
assert records['icarus']['trace']==records['cvc']['trace'] and len(records['cvc']['trace'])==21
record=dict(passed=True,scope='21 finite four-state/UDP/resolution/flop/memory probes only; not SoC equivalence or performance qualification',cvc_source='1c5e043ec33ef6f1fdbf38565501c944893a83cf',bench_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),engines=records)
(out/'result.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
