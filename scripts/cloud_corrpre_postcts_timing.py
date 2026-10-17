#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Continue actual electrical-trial DB with unchanged setup/hold timing repair."""
import hashlib,json,math,os,subprocess,tarfile,time
from pathlib import Path
from bootstrap_flow import verify
from run_cloud_tx_layout_repair import fetch
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-corrpre-postcts-timing'
SPECS=[dict(run=39007378877,group='corrpre-mbist-placement',root='cloud-corrpre-mbist-placement',summary='fe4691dfb059e11e5ae3a2f72c4af3c588572383a35f667583dd51bde234a6bb',archive='dc7576bf8d37466f64fffedf578bb926a04936b982eec4f2ea64069665c87442',size=267678211),dict(run=39009508522,group='corrpre-postcts-electrical',root='cloud-corrpre-postcts-electrical',summary='5bae45ef0aed7f38078eef42b9d69c396f881c1630237020f2c2d16756cfebde',archive='47fb2f3d4030592ef98065ecd96d6ead1735db7118072ac28b32c7f9e539f0b7',size=121328718)]
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def restore(spec):
    stem=spec['group']+'-'+str(spec['run'])+'-1'
    url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-'+str(spec['run'])+'-1-'+spec['group']+'/'
    receipt=OUT/(spec['group']+'.summary.json');fetch(url+stem+'.summary.json',spec['summary'],receipt)
    report=json.loads(receipt.read_text());packed=OUT/(spec['group']+'.tar.gz')
    fetch(url+stem+'.tar.gz.part0000',spec['archive'],packed);assert packed.stat().st_size==spec['size']
    target=ROOT/'hw/soc/out'/spec['root'];assert not target.exists()
    with tarfile.open(packed)as t:
        for m in t.getmembers():
            p=Path(m.name);assert not p.is_absolute()and '..'not in p.parts and p.parts[0]==spec['root']
            assert m.isdir()or m.isfile()
        t.extractall(target.parent,filter='data')
    packed.unlink();assert sha(target/'result.json')==spec['summary']
    assert all(sha(target/p)==v for p,v in report['outputs'].items())
    return target,report

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,qualified_pex=False,
        scope='Continue exactCORRPRE/PCIe/system+EthernetMBIST CTS/electrical trial. Native setup100/hold1000 bounded search with unchanged acceptance limits, fresh separate-corner propagated STA. Requires equivalence, routing/extractedSTA and signoff before adoption.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        original,original_report=restore(SPECS[0]);source,prior=restore(SPECS[1])
        assert original_report['status']=='COMPLETE_NATIVE_CORRPRE_MBIST_CTS_REQUIRES_ROUTING_AND_ALL_SIGNOFF_GATES'
        assert prior['status']=='COMPLETE_NATIVE_CORRPRE_POSTCTS_ELECTRICAL_TRIAL_REQUIRES_REVIEW_EQUIVALENCE_ROUTING_SIGNOFF'and prior['sources_unchanged']
        assert prior['source_head']=='74585b18c46e122618a52bd7182b605ba2a67eff'
        state_path=source/prior['repaired_state'];state=json.loads(state_path.read_text())
        assert sha(state['odb'])==prior['repaired_odb_sha256']=='0543c55882a4f399dbcafd1d2d9b9f36e6c45165e073764c082231ca943da085'
        state['metrics']={};initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
        config=source/'trial-config.json';assert sha(config)=='f68af4b087700cc9c112b38db64c74202cdbcd054eebff7b70531c3a748729c0'
        cfg=json.loads(config.read_text());assert cfg['TIME_DERATING_CONSTRAINT']==5.0 and cfg['CLOCK_PERIOD']==20
        assert cfg['SETUP_VIOLATION_CORNERS']==cfg['HOLD_VIOLATION_CORNERS']==['*']
        assert sha(original/'prepared/physical.sdc')=='6a7e48e7e204e62aad937ce598071c80bccecd0a88c957f51dd18b442ab23b6b'
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');flow=ROOT/'hw/soc/pnr/corrpre_postcts_flow.py'
        protected={str(p):sha(p)for p in [Path(__file__),flow,ROOT/'hw/soc/pnr/interface_flow.py',ROOT/'hw/soc/flow/check_timing_derate.tcl',config,original/'prepared/physical.sdc',Path(state['odb']),initial]}
        run=OUT/'run';run.mkdir()
        command=[str(app),'python',str(flow),'--flow','CorrpreTimingTrial','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(run),'--with-initial-state',str(initial),str(config)]
        result.update(status='RUNNING_NATIVE_SETUP_HOLD_REPAIR',source_specs=SPECS,before=prior['measurements']['after'],protected_inputs=protected,command=command);save();start=time.monotonic()
        with (OUT/'native.log').open('w')as log:code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        result.update(returncode=code,elapsed_s=time.monotonic()-start);save()
        if code:print((OUT/'native.log').read_text(errors='replace')[-20000:],flush=True)
        assert code==0,'Native repair failed; completed checkpoints and diagnostics retained'
        assert all(sha(p)==v for p,v in protected.items())
        measurements={}
        for name,corner in [('slow','nom_slow_1p08V_125C'),('typical','nom_typ_1p20V_25C'),('fast','nom_fast_1p32V_m40C')]:
            dirs=list(run.glob('*-nssoc-corrpretimingafter'+name));assert len(dirs)==1,dirs
            folder=dirs[0];assert not (folder/'unpropagated.rpt').read_text().strip()
            c=json.loads((folder/'config.json').read_text());assert 'c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'in c['PDK_ROOT']
            d=json.loads((folder/'state_out.json').read_text());m={k:v for k,v in d['metrics'].items()if k.endswith('__corner:'+corner)}
            for key in ['timing__setup__ws','timing__hold__ws','timing__setup_vio__count','timing__hold_vio__count']:assert math.isfinite(float(m[key+'__corner:'+corner]))
            measurements[corner]=dict(directory=str(folder.relative_to(OUT)),metrics=m)
        states=list(run.glob('*-openroad-resizertimingpostcts/state_out.json'));assert len(states)==1
        repaired=json.loads(states[0].read_text())
        result.update(status='COMPLETE_NATIVE_CORRPRE_SETUP_HOLD_REPAIR_TRIAL_REQUIRES_EQUIVALENCE_ROUTING_SIGNOFF',after=measurements,
            repaired_state=str(states[0].relative_to(OUT)),repaired_odb_sha256=sha(repaired['odb']),sources_unchanged=True)
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
