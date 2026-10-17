#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Expose pinned native device-binding sources for the new XOR RC composition."""
import hashlib,json,os,subprocess,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-cdr-binding-inputs'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,composition_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-xor-parent-rc-pass-20261017.json').read_text())
        raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(pin['summary_asset']),'-H','Accept: application/octet-stream'])
        assert hashlib.sha256(raw).hexdigest()==pin['summary_sha256'];prior=json.loads(raw);assert prior==pin['report']and prior['sources_unchanged']
        assert prior['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'and len(prior['controls']['cases'])==13
        r['rc_source']=dict(run=pin['run'],summary_sha256=pin['summary_sha256'],parts_sha256=pin['parts_sha256'])
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-composition-input-20261013.json').read_text());packed=OUT/'binding.tar.gz'
        fetch(spec['binding_archive']['url'],spec['binding_archive']['sha256'],packed);assert packed.stat().st_size==spec['binding_archive']['bytes']
        r['methods']={}
        with tarfile.open(packed)as tar:
            for name,digest in spec['binding_methods'].items():
                m=tar.getmember(name);assert m.isfile();data=tar.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==digest
                p=OUT/Path(name).name;assert not p.exists();p.write_bytes(data);r['methods'][p.name]=dict(sha256=digest,text=data.decode())
        packed.unlink();r['status']='COMPLETE_PINNED_NATIVE_BINDING_METHOD_REVIEW_INPUTS_NOT_COMPOSITION'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
