# SPDX-License-Identifier: Apache-2.0
"""Recover derived compile settings and file hashes; never export native files."""
import hashlib,io,json,pathlib,tarfile,zipfile
out=pathlib.Path('out');out.mkdir(exist_ok=True)
r={'full_chip_equivalence':False,'manufacturing_approval':False,'artifact_id':14068260482,'expected_routed_source':'ecef9ad7cc9cd38c40b37b2109c2c976c53d1e4b'}
try:
 raw=pathlib.Path('routed.zip').read_bytes();sha=hashlib.sha256(raw).hexdigest();assert sha=='cf6a83685c33cdf4083786f0ab136ef1ea2666b44476521228aed5eed73d0855','routed artifact SHA'
 z=zipfile.ZipFile(io.BytesIO(raw));names=[n for n in z.namelist() if n.endswith('routed.tgz')];assert len(names)==1,'ambiguous native archive'
 configs=[];sources=[];inventory=[]
 with z.open(names[0]) as native:
  with tarfile.open(fileobj=native,mode='r|gz') as tar:
   for m in tar:
    if not m.isfile():continue
    inventory.append({'path':m.name,'bytes':m.size})
    if m.name.endswith(('.v','.sv','.vh')):
     f=tar.extractfile(m);h=hashlib.sha256()
     for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
     sources.append({'path':m.name,'bytes':m.size,'sha256':h.hexdigest()})
    elif 'config' in pathlib.PurePosixPath(m.name).name and m.name.endswith('.json'):
     assert m.size<20_000_000,'unexpected oversized configuration'
     raw_config=tar.extractfile(m).read();c=json.loads(raw_config)
     keys=['DESIGN_NAME','VERILOG_DEFINES','SYNTH_DEFINES','SYNTH_PARAMETERS','VERILOG_FILES','VERILOG_INCLUDE_DIRS','CLOCK_PORT','CLOCK_PERIOD','PNR_SDC_FILE','SIGNOFF_SDC_FILE','STA_CORNERS','RCX_RULESETS']
     configs.append({'path':m.name,'sha256':hashlib.sha256(raw_config).hexdigest(),'selected_settings':{k:c[k] for k in keys if k in c},'all_setting_names':sorted(c)})
 assert any(x['path'].endswith('prepared/config-routed.json') for x in configs),'routed configuration absent'
 r.update(status='DERIVED_SOURCE_CONTRACT_RECOVERED',artifact_sha256=sha,configurations=configs,source_hashes=sources,native_inventory=inventory,scope='Archive identities, selected compiler/clock/corner settings and hashes only. No native file exported. These settings do not by themselves prove actual instance parameters, full-chip equivalence, timing or LVS.')
except Exception as e:r.update(status='ERROR',error=type(e).__name__+': '+str(e))
(out/'source-contract.json').write_text(json.dumps(r,indent=2));print(json.dumps({'status':r['status'],'configurations':len(r.get('configurations',[])),'sources':len(r.get('source_hashes',[])),'error':r.get('error')}));raise SystemExit(0 if r['status']=='DERIVED_SOURCE_CONTRACT_RECOVERED' else 1)
