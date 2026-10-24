#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only candidate PCell inventory with the exact existing native runtime."""
import hashlib,json,os,subprocess,tarfile,traceback
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-candidate-pcells'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_phy_accepted=False,
           candidate_macro_generated=False,extracted_diffusion_parameters_proven=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        method=ROOT/'scripts/cdr-candidate-pcell-method.json'
        pins=json.loads(method.read_text())['protected']
        for p,h in pins.items():assert sha(ROOT/p)==h,p
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        r['runtime_source']=spec
        packed=OUT/'runtime.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink()
        manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        for p,h in pins.items():assert sha(ROOT/p)==h,p
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']
        r['runtime_sha256']=sha(app);r['runtime_manifest_sha256']=sha(ROOT/'manifest.json');save()
        command=[str(app),'python',str(ROOT/'scripts/cdr_candidate_pcell_inventory.py'),'--pdk',str(ROOT/'pdk'),'--out',str(OUT/'inventory')]
        with (OUT/'generation.log').open('w')as log:
            code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r['returncode']=code;save()
        if code:print((OUT/'generation.log').read_text()[-15000:],flush=True)
        assert code==0,'Native PCell inventory failed; retain evidence'
        result=json.loads((OUT/'inventory/result.json').read_text())
        assert result['sources_unchanged']and len(result['native_cells'])==17
        assert not result['candidate_macro_generated']and not result['extracted_diffusion_parameters_proven']
        for p,h in pins.items():assert sha(ROOT/p)==h,p
        r.update(status=result['status'],inventory=result,sources_unchanged=True,method_sha256=sha(method))
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
