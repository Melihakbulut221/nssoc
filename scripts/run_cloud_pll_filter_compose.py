#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind the new native pump devices and actual fresh wire RC to one physical model."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
from run_cloud_pll_filter_rc import unpack
from run_cloud_tx_layout_repair import fetch,sha
from build_pcie_local_vco_hybrid_v6 import MODEL_PINS
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-pll-filter-compose'
SOURCE=ROOT/'hw/soc/out/cloud-pll-filter-rc'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'
PDK='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
METHODS={
 'pcie-pump-rhi140-binding-20261012/build_devices01.py':'cf62b3b5f892942a4253e314c8c72b4289edca1abd4d1fe18cd00f2402852427',
 'pcie-pump-rhi140-wire-20261012/compose02.py':'16894a0dbc7bc1710cb02f96e2dd439d78546774a025d6ca481d99b987a7be9d',
 'pcie-pump-rhi140-current-20261012/check-compose03.py':'59e219d235f60ca2ec39a3458aa3e8badf9b06a6b5e25919c1979f4e3f78c8f8',
}
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';assert not SOURCE.exists();OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,full_serial_phy_complete=False,parent_model_composed=False,electrical_acquisition_passed=False,
        scope='Actual nine-micrometer capacitor, all30native devices and all84R155C freshly extracted wire records. Strict native terminal/parameter and actual six-corruption composition checks. No845parent model, substrate spreading, RF qualification or electrical/PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(command,label):
        log=OUT/(label+'.log')
        with log.open('w') as stream:code=subprocess.call([str(x) for x in command],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        result.setdefault('commands',[]).append(dict(label=label,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-14000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        stem='pll-filter-rc-9-38853877930-1';base=BASE+'cloud-results-38853877930-1-pll-filter-rc-9/'
        summary_sha='3d7f1ddd048ec3440eda2b3efe059470fe240edf1b347fc46486fe14573386b0';parts_sha='76e67891b5591edefab68d6002367db72ea3b4fda6702b6c93f4c2f8f9b6106d';archive_sha='954a9fdf95bf0683f1f89087e6865f31774a2dcb420192a9bc95dd32bb44686c'
        fetch(base+stem+'.summary.json',summary_sha,OUT/'source-summary.json');fetch(base+stem+'.parts.json',parts_sha,OUT/'source-parts.json')
        prior=json.loads((OUT/'source-summary.json').read_text());parts=json.loads((OUT/'source-parts.json').read_text())
        assert prior['status']=='PASS_ACTUAL_C9_PUMP_NATIVE_WIRE_RC_AND_CONTROLS_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE'
        assert prior['audit']['actual_exported_resistors']==84 and prior['audit']['actual_exported_capacitors']==155
        assert prior['actual_capacitor']['parameters']==dict(w=9.,l=9.,A=81.,P=36.,m=1.)
        assert len(prior['controls']['cases'])==13
        assert parts['parts']==[dict(index=0,name=stem+'.tar.gz.part0000',bytes=5921475,sha256=archive_sha)]
        assert parts['bytes']==5921475 and parts['sha256']==archive_sha
        packed=OUT/'rc.tar.gz';fetch(base+parts['parts'][0]['name'],archive_sha,packed);assert packed.stat().st_size==5921475
        unpack(packed,SOURCE.parent,'cloud-pll-filter-rc')
        assert sha(SOURCE/'result.json')==summary_sha and all(sha(SOURCE/n)==v for n,v in prior['outputs'].items())
        result['physical_rc_source']=dict(run=38853877930,summary_sha256=summary_sha,parts_sha256=parts_sha,archive_sha256=archive_sha,gds_sha256=prior['source_evidence']['gds_sha256']);save()
        for n in ('devices01.json','anchors03.json','native-mutations01.json'):shutil.copyfile(SOURCE/n,OUT/n)
        pdk=ROOT/'pdk'
        for path,digest in MODEL_PINS.items():
            target=pdk/path;target.parent.mkdir(parents=True,exist_ok=True)
            fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+PDK+'/ihp-sg13g2/'+path,digest,target)
        frozen=OUT/'frozen';frozen.mkdir();records=json.loads((SOURCE/'recovered-methods.json').read_text())['methods'];adaptations={}
        for suffix,digest in METHODS.items():
            item=records['hw/soc/out/'+suffix];data=item['text'].encode();assert hashlib.sha256(data).hexdigest()==digest==item['sha256'] and len(data)==item['bytes']
            name=Path(suffix).name;(frozen/name).write_bytes(data);text=data.decode();edits=[]
            if name=='build_devices01.py':
                replacements=[("Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2')","R/'pdk'"),("R/'hw/soc/out/pcie-pump-rhi140-20261012/native03/lvs'","R/'hw/soc/out/cloud-pll-filter-rc/source/physical/lvs'")]
            elif name=='compose02.py':
                replacements=[("R/'hw/soc/out/pcie-pump-rhi140-binding-20261012'","B"),("wire=B/'rc01/wires.spice'","wire=R/'hw/soc/out/cloud-pll-filter-rc/rc01/wires.spice'")]
            else:
                replacements=[("R/'hw/soc/out/pcie-pump-rhi140-binding-20261012'","B"),("B.parent/'pcie-pump-rhi140-wire-20261012/rc01/wires.spice'","R/'hw/soc/out/cloud-pll-filter-rc/rc01/wires.spice'")]
            for old,new in replacements:
                count=text.count(old);assert count>0,(name,old);text=text.replace(old,new);edits.append(dict(before=old,after=new,count=count))
            target=OUT/name;target.write_text(text);adaptations[name]=dict(original_sha256=digest,adapted_sha256=sha(target),edits=edits)
        result['method_adaptations']=adaptations;save()
        run([sys.executable,'-m','py_compile',*[OUT/n for n in adaptations]],'compile-adapted-methods')
        run([sys.executable,OUT/'build_devices01.py'],'bind-native-devices')
        tech=pdk/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json'
        run([sys.executable,ROOT/'scripts/check_pcie_pump30_binding.py','--devices',OUT/'devices01.json','--native',SOURCE/'source/physical/lvs/extracted.cir','--compact',OUT/'pump30-compact01.spice','--technology',tech,'--out',OUT/'independent-binding.json'],'independent-native-binding')
        run([sys.executable,OUT/'compose02.py'],'compose-fresh-physical-model')
        run([sys.executable,OUT/'check-compose03.py'],'independent-composition-and-faults')
        result['binding']=json.loads((OUT/'independent-binding.json').read_text());assert result['binding']['status']=='PASS_NATIVE30_TERMINALS_AND_PARAMETERS'
        result['composition']=json.loads((OUT/'composition01.json').read_text())
        result['composition_controls']=json.loads((OUT/'composition-controls01.json').read_text());assert len(result['composition_controls']['actual_rejected_mutants'])==6
        assert result['composition_controls']['status']=='PASS_NATIVE30_AND_ALL239_WIRE_RECORDS_WITH_EXPLICIT_REFERENCES'
        assert all(sha(SOURCE/n)==v for n,v in prior['outputs'].items()) and all(sha(pdk/n)==v for n,v in MODEL_PINS.items())
        result['source_unchanged']=True;result['status']='PASS_ACTUAL_C9_PUMP_PHYSICAL_MODEL_AND_FAULTS_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
