import json,os,pathlib,subprocess,time,sys
R=pathlib.Path.cwd();B=R/'hw/soc/out/resume-20261007';O=B/'ci-fixed';O.mkdir(exist_ok=True)
names=[*(f'soc_pcie_gen3_rx_events_v{x}' for x in range(1,6)), 'soc_pcie_gen3_dllp_consumer_v5','soc_pcie_gen3_dllp_consumer_v6','soc_pcie_gen3_dllp_consumer_compare_v5','soc_pcie_gen3_dllp_consumer_forwarding_v5','soc_pcie_gen3_recovered_events_v1','soc_pcie_gen3_recovered_events_v2']
env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','PYTHONEXECUTABLE')};env['PATH']=str(R/'hw/soc/tools/cocotb-venv/bin')+os.pathsep+env['PATH']
rows=[]
for name in names:
 out=O/name;out.mkdir();start=time.monotonic()
 command=['make','-f',str(R/'hw/soc/tb/cocotb'/('Makefile.'+name)),'SIM_BUILD='+str(out/'sim'),'COCOTB_RESULTS_FILE='+str(out/'results.xml')]
 with (out/'simulation.log').open('w') as f:
  try: p=subprocess.run(command,cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180);rc=p.returncode
  except subprocess.TimeoutExpired:rc=124
 row=dict(name=name,returncode=rc,seconds=time.monotonic()-start)
 if (out/'results.xml').exists():
  import xml.etree.ElementTree as E
  tests=list(E.parse(out/'results.xml').getroot().iter('testcase'));row.update(tests=len(tests),failures=sum(x.find('failure') is not None for x in tests),skips=sum(x.find('skipped') is not None for x in tests))
 rows.append(row);(O/'result.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
 if rc:sys.exit(1)
