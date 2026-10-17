#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resume exact boot-proven CTS, measure all corners, repair electrical loads."""
import hashlib,json,math,os,subprocess,tarfile,time
from pathlib import Path
from bootstrap_flow import verify
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-corrpre-postcts-electrical'
SOURCE=ROOT/'hw/soc/out/cloud-corrpre-mbist-placement'
TAG='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-39007378877-1-corrpre-mbist-placement/'
STEM='corrpre-mbist-placement-39007378877-1'
CORNERS=['nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C']

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source_run=39007378877,
        accepted=False,final_timing_complete=False,full_phy_accepted=False,qualified_pex=False,
        scope='Exact CORRPRE/PCIe/20SRAM MBIST CTS. Fresh separate-corner placement-estimate STA before/after native electrical repair. No rerun of boot/synthesis/placement/CTS. Not routed or final signoff; equivalence and later physical checks required before adoption.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        receipt=OUT/'source-summary.json'
        fetch(TAG+STEM+'.summary.json','fe4691dfb059e11e5ae3a2f72c4af3c588572383a35f667583dd51bde234a6bb',receipt)
        previous=json.loads(receipt.read_text())
        assert previous['status']=='COMPLETE_NATIVE_CORRPRE_MBIST_CTS_REQUIRES_ROUTING_AND_ALL_SIGNOFF_GATES'
        assert previous['source_head']=='8581b34b8524d3fc65ceb15c81c6f42fc37c5525'
        packed=OUT/'source.tar.gz'
        fetch(TAG+STEM+'.tar.gz.part0000','dc7576bf8d37466f64fffedf578bb926a04936b982eec4f2ea64069665c87442',packed)
        assert packed.stat().st_size==267678211
        assert not SOURCE.exists()
        with tarfile.open(packed)as archive:
            for member in archive.getmembers():
                p=Path(member.name)
                assert not p.is_absolute() and '..'not in p.parts and p.parts[0]==SOURCE.name
                assert member.isdir() or member.isfile(),'No archive links'
            archive.extractall(SOURCE.parent,filter='data')
        packed.unlink()
        assert all(sha(SOURCE/p)==v for p,v in previous['outputs'].items())
        assert sha(SOURCE/'result.json')==sha(receipt)
        state_path=SOURCE/'run/27-openroad-cts/state_out.json'
        assert sha(state_path)=='bf2f62de4f501fd49e5a10ce647b4d510d2df165178b02ae525c990878664535'
        state=json.loads(state_path.read_text())
        assert sha(state['odb'])=='25abfb1825f2ef8b04c373f925c432c8ad4f8bc79439352c94b2d04375932f3e'
        # Metrics accumulated before CTS are deliberately not evidence for this DB.
        result['discarded_inherited_metric_count']=len(state['metrics'])
        state['metrics']={}
        initial=OUT/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
        config_path=SOURCE/'prepared/config.json'
        assert sha(config_path)=='d6841477025808ac44bfe6a54b8b638c5ca285fcdfa57408a29c4e57012ff108'
        config=json.loads(config_path.read_text())
        assert config['TIME_DERATING_CONSTRAINT']==5.0 and config['CLOCK_PERIOD']==20
        assert config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
        # Preserve existing CTS/port buffer trees. The trial repairs internal
        # fanout/slew/cap loads; it never removes synthesis or clock buffers.
        overrides=dict(DESIGN_REPAIR_REMOVE_BUFFERS=False,DESIGN_REPAIR_BUFFER_INPUT_PORTS=False,
                       DESIGN_REPAIR_BUFFER_OUTPUT_PORTS=False,DESIGN_REPAIR_TIE_FANOUT=False)
        config.update(overrides)
        config['TIME_DERATING_CONSTRAINT']=5.0
        trial=OUT/'trial-config.json';trial.write_text(json.dumps(config,indent=2)+'\n')
        result['config_changes']=overrides
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        flow=ROOT/'hw/soc/pnr/corrpre_postcts_flow.py'
        protected={str(p):sha(p)for p in [Path(__file__),flow,ROOT/'hw/soc/flow/check_timing_derate.tcl',config_path,SOURCE/'prepared/physical.sdc',Path(state['odb']),trial,initial]}
        assert sha(SOURCE/'prepared/physical.sdc')=='6a7e48e7e204e62aad937ce598071c80bccecd0a88c957f51dd18b442ab23b6b'
        run=OUT/'run';run.mkdir()
        command=[str(app),'python',str(flow),'--flow','CorrpreElectricalTrial','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(run),'--with-initial-state',str(initial),str(trial)]
        result.update(status='RUNNING_NATIVE_BEFORE_REPAIR_AFTER',protected_inputs=protected,command=command);save()
        start=time.monotonic()
        with (OUT/'native.log').open('w')as log:code=subprocess.call(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        result.update(returncode=code,elapsed_s=time.monotonic()-start);save()
        if code:print((OUT/'native.log').read_text(errors='replace')[-20000:],flush=True)
        assert code==0,'Native flow failed; original and trial evidence retained'
        assert all(sha(p)==v for p,v in protected.items())
        measurements={}
        for phase in ['before','after']:
            measurements[phase]={}
            for name,corner in zip(['slow','typical','fast'],CORNERS,strict=True):
                dirs=list(run.glob('*-nssoc-corrpre'+phase+name));assert len(dirs)==1,dirs
                folder=dirs[0];cfg=json.loads((folder/'config.json').read_text())
                assert 'c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c' in cfg['PDK_ROOT']
                assert not (folder/'unpropagated.rpt').read_text().strip(),'Clock not propagated'
                data=json.loads((folder/'state_out.json').read_text())
                metrics={k:v for k,v in data['metrics'].items()if k.endswith('__corner:'+corner)}
                for key in ['timing__setup__ws','timing__hold__ws','timing__setup_vio__count','timing__hold_vio__count']:
                    assert math.isfinite(float(metrics[key+'__corner:'+corner]))
                for name2 in ['max.rpt','min.rpt','checks.rpt','violator_list.rpt','high-fanout.rpt','clock.rpt','ws.max.rpt','ws.min.rpt']:
                    assert (folder/name2).is_file(),name2
                measurements[phase][corner]=dict(metrics=metrics,directory=str(folder.relative_to(OUT)))
        repaired=list(run.glob('*-nssoc-corrpreelectricalpostcts/state_out.json'));assert len(repaired)==1
        repaired_state=json.loads(repaired[0].read_text())
        result.update(status='COMPLETE_NATIVE_CORRPRE_POSTCTS_ELECTRICAL_TRIAL_REQUIRES_REVIEW_EQUIVALENCE_ROUTING_SIGNOFF',measurements=measurements,
            repaired_state=str(repaired[0].relative_to(OUT)),repaired_odb_sha256=sha(repaired_state['odb']),sources_unchanged=True)
    except BaseException as e:
        result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
