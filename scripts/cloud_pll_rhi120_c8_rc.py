#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Capture fresh native RC over the entire frozen PLL845 physical metal/MIM graph."""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import check_pll845_whole_rc_capture as checks
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-rhi120-c8-rc'
TOP='nssoc_pll845_divider3p2_rhi120_c8_development'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 generator=ROOT/'scripts/pll_rhi120_c8_rc_inputs_native.py'
 helper=Path(checks.__file__).resolve()
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],
  controller_sha256=sha(Path(__file__)),generator_sha256=sha(generator),checker_sha256=sha(helper),
  accepted=False,qualified_pex=False,full_phy_accepted=False,raw_rc_audit_passed=False,
  full_intrinsic_model_composed=False,closed_loop_accepted=False,
  scope='Whole actual PLL845 metal/via graph and all26 MIM masks.1877 logical points; exact physical coincidences only.235 native conductors. Body/poly/diffusion/salicide access resistance, raw R/C conservation audit, complete intrinsic composition, loaded electrical behavior and qualified PEX remain separate.')
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 def run(cmd,label):
  logpath=OUT/(label+'.log')
  with logpath.open('w')as stream:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
  r.setdefault('commands',[]).append(dict(label=label,returncode=code,log_sha256=sha(logpath)));save()
  if code:print(logpath.read_text(errors='replace')[-15000:],flush=True)
  assert code==0,(label,code)
 save()
 try:
  pin=json.loads((ROOT/'docs/evidence/pll-rhi120-c8-terminals-pass-20261023.json').read_text())
  assert pin['run']==39915871064 and pin['source_head']=='8098380e227c959c39403c33cd309bc1702eb551'
  assert pin['pins']['summary']['sha256']=='558a1d37cb69163ed67d4641b91d56467a8fb998f378e9d2dec6e6370beebe0a'
  selected=['anchors.json','source/parent/integrated/'+TOP+'.gds','source/parent/integrated/result.json',
   'source/parent/physical/lvs_flat/result.lvsdb','source/parent/physical/lvs_flat/audit.json',
   'source/parent/physical/lvs_flat/extracted.cir','source/wire/native05/result.json',
   'source/wire/native05/wires.l2n','source/wire/whole-pll-mim-masks.gds','source/native-mim-geometry.json',
   'npn13G2_code.py','general_derivations.lvs','general_connections.lvs']
  prior,proof=reports.restore_report('pll-rhi120-c8-terminals',pin['run'],pin['pins']['summary']['sha256'],
    pin['pins']['parts']['sha256'],OUT/'source',selected)
  assert prior['source_head']==pin['source_head']and prior['status']==pin['status']and prior['sources_unchanged']
  assert prior['native_returncode']==0 and prior['binding']['counts']==pin['counts']
  assert prior['binding']['negative_controls']==pin['negative_controls']and not prior['binding']['unresolved']
  r['terminal_reference_source']=proof;save()
  app=Path(os.environ['CLOUD_APPIMAGE'])
  assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  run([app,'python',generator,OUT],'native-whole-geometry-and-points')
  r['native_inputs']=json.loads((OUT/'native-inputs.json').read_text());save()
  assert r['native_inputs']['wire_components']==235 and r['native_inputs']['native_mim_devices']==26
  runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text())
  rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'runtime.tar.gz'
  fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed)
  with tarfile.open(packed)as tar:tar.extractall(rt,filter='data')
  packed.unlink();manifest=json.loads((rt/'manifest.json').read_text())
  assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
  pilot=json.loads((ROOT/'docs/evidence/cdr-mim-explicit-model-pilot-pass-20261018.json').read_text())['report']
  patch=pilot['private_ngspice_tech'];original=rt/'tech';private=OUT/'ngspice-mim-tech'
  shutil.copytree(original,private);tech=private/'ihp-sg13g2-extract.tech'
  assert sha(tech)==patch['original_sha256'];text=tech.read_text()
  for line in patch['removed_cdl_device_estimate_lines']:
   assert text.count(line)==1;text=text.replace(line,'')
  tech.write_text(text);assert sha(tech)==patch['private_sha256']
  assert all(sha(private/p.name)==sha(p)for p in original.iterdir()if p.is_file()and p.name!=tech.name)
  r['private_tech']=patch;r['magic_runtime']=runtime;save()
  methods=json.loads((ROOT/'docs/evidence/cdr-v4-rc-inputs-20261017.json').read_text())['report']['original_extraction_methods']
  meta=methods['run-rc01.py'];text=meta['text'];assert hashlib.sha256(text.encode()).hexdigest()==meta['sha256']
  edits=[]
  for before,after in [
   ("Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')","B.parent/'magic-cloud/runtime/lib'"),
   ("Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')","B.parent/'ngspice-mim-tech'"),
   ('(2*1024**3,)*2','(4*1024**3,)*2'),('size>80*1024**2','size>1024*1024**2'),
   ('OWNED_SCRATCH_80MIB_LIMIT','OWNED_SCRATCH_1024MIB_LIMIT')]:
   assert text.count(before)==1;text=text.replace(before,after);edits.append(dict(before=before,after=after))
  method=OUT/'wire/run-rc01.py';method.write_text(text)
  r['native_method']=dict(original_sha256=meta['sha256'],adapted_sha256=sha(method),edits=edits);save()
  run([sys.executable,method],'native-whole-pll-mim-rc')
  capture=json.loads((OUT/'wire/rc03/result.json').read_text());r['capture']=capture;save()
  assert capture['returncode']==0 and capture['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'
  anchors=json.loads((OUT/'wire/anchors08.json').read_text())
  mim=json.loads((OUT/'source/source/native-mim-geometry.json').read_text())
  text=(OUT/'wire/rc03/wires.spice').read_text()
  r['intrinsic_capture_binding']=checks.check_capture(text,anchors,mim);save()
  baseline=checks.parser.statements((OUT/'wire/rc03/baseline.spice').read_text())
  assert len([x for x in baseline if x[0].startswith('X')])==26
  r['capture_controls']=checks.fault_controls(text,anchors,mim)
  assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
  assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
  assert all(sha(Path(n))==digest for n,digest in anchors['inputs'].items())
  assert sha(method)==r['native_method']['adapted_sha256']and sha(tech)==patch['private_sha256']
  assert sha(generator)==r['generator_sha256']and sha(helper)==r['checker_sha256']and sha(Path(__file__))==r['controller_sha256']
  r.update(sources_unchanged=True,status='PASS_PLL845_WHOLE_MIM_NATIVE_CAPTURE_AND8_CONTROLS_REQUIRES_RAW_RC_AUDIT')
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
