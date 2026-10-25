import sys,json,pathlib,time
sys.path.insert(0,'scripts')
import run_npu_eco_physical as f
b=f.ROOT/'hw/soc/out/npu-eco-physical-runner-20261006'
m=f.common.validate_manifest(json.loads((f.ROOT/f.physical.MANIFEST).read_text()))
x={'status':'PREPARING_EXACT_LOCAL_PHYSICAL_INPUTS_NO_EDA','started':f.common.now(),'native_executed':False}
try:
 runtime=f.ROOT/'hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage'
 f.common.verify_file(runtime,m['runtime']);x['runtime']={'path':str(runtime),**f.pin(runtime)}
 archive=b/'source01.tar.gz';f.common.download(m['archive'],archive);x['archive']=f.pin(archive)
 bundle=b/'bundle01';f.common.restore(archive,bundle,m['files']);assert f.verify_bundle(bundle,runtime)==m
 x.update(status='PASS_COMPLETE_PINNED_LOCAL_INPUT_BUNDLE_NO_EDA',bundle=str(bundle),members=len(m['files']),completed=f.common.now())
except BaseException as e:
 x.update(status='FAILED_PRESERVED',error=repr(e));raise
finally:
 f.common.save(b/'bundle-preparation01.json',x)
