#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh wire extraction from the real 9 um pump; never old RC relabeled as new."""
import hashlib,json,os,subprocess,sys,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-filter-rc'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'
TOP='nssoc_pump_filter13_rhi140_c9_v1'
GDS_SHA='abbe380e4aaeeacfa9074d594f8cbf572a82717386c7d15725b7619876235a78'
METHODS={
 'pcie-pump-rhi140-binding-20261012/export01.py':'91732468f861b45d560a17390fd68d283f00159b87120b4d28a07bae4dcc1ed7',
 'pcie-pump-rhi140-wire-20261012/probe01.py':'25c9addbae4eed9d60dee956c06a3a1e08009c624a29351629a06fc5465f38d6',
 'pcie-pump-rhi140-wire-20261012/locate01.py':'39486707507c81d1c61070746068e9f7c34733b3304f07967ec4891a6db02ad7',
 'pcie-pump-rhi140-wire-20261012/anchors03.py':'94807b90dce0d07f0d579bf6fc584c3c94a1e67496faab022f897a65471513ac',
 'pcie-pump-rhi140-wire-20261012/run-rc01.py':'e9e15ff0b7bfec170f19295a78988e50df81fda98738ca5338be66b41b172fde',
 'pcie-pump-rhi140-wire-20261012/audit-rc02.py':'41051fb749e4842fe39a63541afef9f3e489f2cf0f9b7d79ae03c755c4586627',
 'pcie-pump-rhi140-wire-20261012/mutations01.py':'ac0589d27fcef0884c613b9b2734724e4b08a26539345855549b86e94774c617',
}
def unpack(packed,destination,prefix=None):
    with tarfile.open(packed) as tar:
        members=tar.getmembers();assert len(members)==len({m.name for m in members})
        for m in members:
            path=Path(m.name);assert not path.is_absolute() and '..' not in path.parts
            assert m.isfile() or m.isdir()
            if prefix is not None:assert path.parts[0]==prefix
        tar.extractall(destination,filter='data')
    packed.unlink()

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,full_serial_phy_complete=False,parent_model_composed=False,
        scope='Fresh actual 9 um pump metal/via geometry and native30-device terminal binding, 59 physical reference points, native Magic wire RC and thirteen raw-corruption controls. Intrinsic body/well spreading, qualified RF extraction, complete845-parent model and electrical acquisition are separate requirements.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label):
        path=OUT/(label+'.log')
        with path.open('w') as log:code=subprocess.call([str(x) for x in command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(label=label,returncode=code,log_sha256=sha(path)));save()
        if code:print(path.read_text(errors='replace')[-14000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        stem='pll-filter-layout-9-38848309907-1';base=BASE+'cloud-results-38848309907-1-pll-filter-layout-9/'
        summary_sha='ae90bac4182e79be42f41aedea9605ade46d2f80b5a127c7f38f7b25534ba0ad'
        parts_sha='f52d7d03da41475095a6067b958c99d629a959da9829e58e6915148d297e525b'
        archive_sha='2a8e067beb6b2598a3eab4bc88d79acf0b5a5e8cb4a2f26a214a36c0629297cf'
        fetch(base+stem+'.summary.json',summary_sha,OUT/'source-summary.json')
        fetch(base+stem+'.parts.json',parts_sha,OUT/'source-parts.json')
        prior=json.loads((OUT/'source-summary.json').read_text());manifest=json.loads((OUT/'source-parts.json').read_text())
        assert prior['size_um']==9 and prior['source_head']=='8380558b46bbc150b7d3e459e8f47be2fd260313'
        assert prior['status']=='FAIL_OR_ERROR' and prior['error'].startswith('FileNotFoundError(')
        assert prior['physical']['status']=='PASS_NATIVE_PUMP_FILTER_DRC_LVS_AND_FAULT_CONTROLS'
        assert {k:v['status'] for k,v in prior['physical']['steps'].items()}=={k:('PASS' if k in ('drc','lvs','lvs_flat') else 'REJECTED_EXPECTED_FAULT') for k in ('drc','lvs','lvs_flat','wrong_width','missing_well','vctrl_open','rail_short','offgrid')}
        assert manifest['parts']==[dict(index=0,name=stem+'.tar.gz.part0000',bytes=248708,sha256=archive_sha)]
        assert manifest['sha256']==archive_sha and manifest['bytes']==248708
        packed=OUT/'source.tar.gz';fetch(base+manifest['parts'][0]['name'],archive_sha,packed)
        assert packed.stat().st_size==248708
        unpack(packed,OUT,'cloud-pll-filter-layout');(OUT/'cloud-pll-filter-layout').rename(OUT/'source')
        source=OUT/'source';assert sha(source/'result.json')==summary_sha
        assert all(sha(source/n)==v for n,v in prior['outputs'].items())
        assert sha(source/'layout'/(TOP+'.gds'))==GDS_SHA
        result['source_evidence']=dict(run=38848309907,summary_sha256=summary_sha,parts_sha256=parts_sha,archive_sha256=archive_sha,gds_sha256=GDS_SHA,physical_status=prior['physical']['status']);save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==prior['runtime_sha256'];result['runtime_sha256']=sha(app)
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text())
        rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'magic.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed);assert packed.stat().st_size==runtime['receipt']['bytes']
        unpack(packed,rt);magic_manifest=json.loads((rt/'manifest.json').read_text());assert all(sha(rt/n)==v['sha256'] for n,v in magic_manifest['files'].items())
        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser']
        raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';raw.parent.mkdir(parents=True,exist_ok=True);fetch(rawspec['url'],rawspec['sha256'],raw)
        recovered=OUT/'recovered-methods.json'
        fetch(BASE+'cloud-results-38851306875-1-pll-pump-methods/pll-pump-methods-38851306875-1.summary.json','2ec9c5c63bbe89e4b3ebf2d79b54aa487a40c749457d87b854ea9ac0c9755fc3',recovered)
        records=json.loads(recovered.read_text());assert records['status']=='COMPLETE_SOURCE_BOUND_PUMP_METHOD_RECOVERY_NOT_NEW_EXTRACTION'
        frozen=OUT/'frozen';frozen.mkdir();adaptations={}
        for suffix,digest in METHODS.items():
            row=records['methods']['hw/soc/out/'+suffix];data=row['text'].encode()
            assert hashlib.sha256(data).hexdigest()==digest==row['sha256'] and len(data)==row['bytes']
            name=Path(suffix).name;(frozen/name).write_bytes(data);text=data.decode();edits=[]
            replacements=[]
            if name=='export01.py':
                replacements=[("R/'hw/soc/out/pcie-pump-rhi140-20261012/native03/lvs'","B/'source/physical/lvs'"),('nssoc_pump_filter13_rhi140_v1',TOP)]
            elif name in ('probe01.py','locate01.py','anchors03.py'):
                replacements=[("R/'hw/soc/out/pcie-pump-rhi140-20261012'","B/'source'"),('layout02/','layout/'),('native03/lvs','physical/lvs'),('nssoc_pump_filter13_rhi140_v1',TOP)] if name!='anchors03.py' else [("R/'hw/soc/out/pcie-pump-rhi140-20261012'","B/'source'"),('layout02/','layout/'),('native03/lvs','physical/lvs'),('nssoc_pump_filter13_rhi140_v1',TOP)]
                if name=='probe01.py':replacements.append(('08d8368099459f93eec3fbd2800d44f3052b2cfad2e7dcab275500e84cccd2ee',GDS_SHA))
            elif name=='run-rc01.py':
                replacements=[("Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')","B/'magic-cloud/runtime/lib'"),("Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')","B/'magic-cloud/tech'")]
            for old,new in replacements:
                count=text.count(old);assert count>0,(name,old);text=text.replace(old,new);edits.append(dict(before=old,after=new,count=count))
            target=OUT/name;target.write_text(text);adaptations[name]=dict(original_sha256=digest,adapted_sha256=sha(target),edits=edits)
        result['method_adaptations']=adaptations;result['magic_runtime']=runtime;save()
        run([sys.executable,'-m','py_compile',*[OUT/n for n in adaptations]],'compile-adapted-methods')
        for name in ('export01.py','probe01.py','locate01.py','anchors03.py'):
            run([app,'python',OUT/name],name.removesuffix('.py'))
        devices=json.loads((OUT/'devices01.json').read_text())
        caps=[d for d in devices['devices'] if d['model']=='cap_cmim'];assert len(caps)==1
        params={k.lower():v for k,v in caps[0]['parameters'].items()};assert params['w']==params['l']==9.0,params
        result['actual_capacitor']=caps[0]
        result['wire_geometry']=json.loads((OUT/'native01/result.json').read_text())
        result['terminal_anchors']=json.loads((OUT/'anchors03.json').read_text());save()
        run([sys.executable,OUT/'run-rc01.py'],'native-rc')
        result['native']=json.loads((OUT/'rc01/result.json').read_text());save()
        assert result['native']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT' and result['native']['returncode']==0
        run([sys.executable,OUT/'audit-rc02.py',OUT/'rc01',OUT/'anchors03.json',OUT/'rc-audit.json'],'audit-rc')
        result['audit']=json.loads((OUT/'rc-audit.json').read_text());save();assert result['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        run([sys.executable,OUT/'mutations01.py'],'raw-corruption-controls')
        result['controls']=json.loads((OUT/'native-mutations01.json').read_text());assert result['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
        assert all(sha(source/n)==v for n,v in prior['outputs'].items())
        assert all(sha(rt/n)==v['sha256'] for n,v in magic_manifest['files'].items())
        assert sha(raw)==rawspec['sha256']
        result['status']='PASS_ACTUAL_C9_PUMP_NATIVE_WIRE_RC_AND_CONTROLS_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
