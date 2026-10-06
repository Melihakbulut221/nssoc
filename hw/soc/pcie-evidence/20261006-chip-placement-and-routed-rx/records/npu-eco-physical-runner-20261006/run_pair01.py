# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One local serial pair; no source change or native elapsed timeout."""
import os,sys,json,pathlib,traceback
R=pathlib.Path(__file__).absolute().parents[4]
os.chdir(R);sys.path.insert(0,str(R/'scripts'))
import run_npu_eco_physical as f
B=pathlib.Path(__file__).absolute().parent
BOOT=R/'hw/soc/out/npu-eco-boot-final-20261006'
state={'status':'PREPARING_LOCAL_SERIAL_PAIR','utc':f.common.now(),'controller':f.owned.identity(os.getpid()),'boot_id':pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'affinity':sorted(os.sched_getaffinity(0)),'native_final_timing_accepted':False}
f.common.save(B/'pair01-status.json',state)
try:
 freeze=json.loads((B/'source-freeze03.json').read_text())
 for table in ('sources','dependencies'):
  for name,expected in freeze[table].items():f.common.verify_file(pathlib.Path(name),expected)
 peer=json.loads((B/'source-only-peer-pll03.json').read_text());f.require(not peer['findings'],'Source peer has findings')
 bootpeer=json.loads((BOOT/'saved-boot-peer-pll01.json').read_text());f.require(not bootpeer['findings'],'Boot peer has findings')
 for variant in ('original','factored'):
  state.update(status='RUNNING_'+variant.upper(),utc=f.common.now(),variant=variant);f.common.save(B/'pair01-status.json',state)
  row=f.run(variant,B/('pair01-'+variant),B/('pair01-'+variant+'-work'),B/'bundle01',R/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage',boot_archive=BOOT/'final01.zip',boot_run=BOOT/'run01.json',boot_artifact=BOOT/'artifact01.json')
  state.setdefault('completed',{})[variant]={'result':f.pin(B/('pair01-'+variant)/'result.json'),'status':row['status']}
 result=f.compare(B/'pair01-original',B/'pair01-factored');f.common.save(B/'pair01-comparison.json',result)
 state.update(status='COMPLETE_MATCHED_ESTIMATES_ONLY',comparison=f.pin(B/'pair01-comparison.json'),utc=f.common.now())
except BaseException as error:
 state.update(status='FAILED_PRESERVED',error=repr(error),utc=f.common.now());raise
finally:
 f.common.save(B/'pair01-status.json',state)
