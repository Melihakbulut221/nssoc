#!/usr/bin/env python3
"""Export and read back a provisional core boundary while detailed route runs."""
import json,os,subprocess
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,restore_mapping,restore_cts,qualify_sources,current_path
from cloud_core_only_clock_probe import restore_cts8
from cloud_core_only_clock_refine import restore_clock_split,restore_previous
from cloud_core_only_detailed_route import restore_refinement
OUT=ROOT/'hw/soc/out/core-only-boundary-probe'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,
           final_routed_core=False,physical_timing_complete=False,full_chip_integrated=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        qualify_sources();mapping,mapmeta=restore_mapping()
        cts,ctsmeta,config,initial=restore_cts()
        assert cts['source_binding']['netlist_sha256']==mapping['outputs']['synthesis/soc_top.netlist.v']
        cts8,cts8meta,config,initial=restore_cts8(config)
        split,splitmeta,initial=restore_clock_split()
        previous,prevmeta,initial=restore_previous()
        refined,refmeta,initial=restore_refinement()
        r['source_binding']=dict(refinement_run=44259265143,refinement_head='572c3eb98392b0f56351d5aaf4f256499b4b8d9f',
            artifacts=mapmeta+ctsmeta+[cts8meta,splitmeta,prevmeta]+refmeta)
        data=json.loads(config.read_text());assert data['CLOCK_PERIOD']==20 and data['TIME_DERATING_CONSTRAINT']==5.0
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        flow=ROOT/'hw/soc/pnr/core_only_boundary_flow.py';audit=ROOT/'scripts/audit_core_only_boundary.py'
        odb_path=current_path(json.loads(initial.read_text())['odb'])
        contract=ROOT/'hw/soc/core-only-chip-io-contract.json'
        protected={str(p):sha(p)for p in [Path(__file__),flow,audit,config,initial,odb_path,contract]}
        r['protected_inputs']=protected
        directory=OUT/'views';directory.mkdir()
        command=[str(app),'python',str(flow),'--flow','CoreOnlyBoundaryProbe','--pdk-root',
            str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell',
            '--force-run-dir',str(directory),'--with-initial-state',str(initial),str(config)]
        r.update(status='EXPORTING_PROVISIONAL_VIEWS',command=command);save()
        with (OUT/'export.log').open('w')as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        states=list(directory.glob('*-openroad-writeviews/state_out.json'));assert len(states)==1
        state=json.loads(states[0].read_text());views={}
        for key in ['openroad_lef','pnl','nl','def','odb']:
            p=current_path(state[key]);assert directory in p.parents
            views[key]=dict(path=str(p),sha256=sha(p))
        spec=dict(odb=dict(path=str(odb_path),sha256=sha(odb_path)),lef=views['openroad_lef'],
                  contract=dict(path=str(contract),sha256=sha(contract)),output=str(OUT/'pin-readback.json'))
        manifest=OUT/'audit-inputs.json';manifest.write_text(json.dumps(spec,indent=2)+'\n')
        with (OUT/'pin-readback.log').open('w')as log:
            subprocess.run([str(app),'openroad','-exit','-python',str(audit)],
                env=dict(os.environ,NSSOC_BOUNDARY_INPUTS=str(manifest)),stdout=log,stderr=subprocess.STDOUT,check=True)
        pins=json.loads((OUT/'pin-readback.json').read_text());assert pins['source_unchanged']and not pins['accepted']
        assert all(sha(p)==h for p,h in protected.items())
        r.update(status='PROVISIONAL_CORE_BOUNDARY_EXPORTED_AND_READ_BACK_REQUIRES_FINAL_ROUTE_REBIND',
                 views=views,pin_readback={k:v for k,v in pins.items()if k!='pins'},sources_unchanged=True,
                 scope='Authenticated pre-DRT clock-refine geometry only. Native LEF and powered netlist export; no final DRT, GDS, timing, CDC, full-chip route or manufacturing acceptance.')
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
