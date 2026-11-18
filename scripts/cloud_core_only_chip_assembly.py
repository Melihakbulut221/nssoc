#!/usr/bin/env python3
"""Build provisional chip ODB from verified shell, ring and core boundary views."""
import base64,hashlib,json,os,subprocess
from pathlib import Path
from cloud_core_only_postgrt import archive,completed,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-assembly'
REV='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,final_core_route=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        inputs={};sources=[]
        specs=[('shell',44268658068,'8e3e1d4192178ebce2eb83ec4a7430a0bb80bac5','core-only-shell-map-',14410678768,'8bda874049c1183108258285d4b3dbd8782c6df175d3c5faa2875691058a0d15','core-only-shell-map/'),
          ('boundary',44271378140,'ba7a53efac94da34d323d33ad8ce97a4125864d2','core-only-boundary-probe-native-',14412881780,'e482e38c10b0f029ad3432c82f9c63d29c23b0f8c7a661815a3e1d0f22131005',''),
          ('ring',44262963332,'3e3ee37fb0c610ccd3e24ee9be8885c465d63c46','core-only-io-floorplan-',14408393294,'4815f361b0e732e9fdc3df7cad38f78a71d940a0f0aeda9a3121f7a83cdff9d9','')]
        reports={}
        for label,rid,head,prefix,aid,digest,folder in specs:
            run=completed(rid,head);z,meta=archive(run,prefix+str(rid));assert meta['id']==aid and meta['digest']=='sha256:'+digest
            report=json.loads(z.read(folder+'result.json'));assert report['source_head']==head and report['sources_unchanged']and not report['accepted']
            for p,h in report['outputs'].items():assert hashlib.sha256(z.read(folder+p)).hexdigest()==h
            sources.append(meta);reports[label]=report
            if label=='shell':key='mapped';data=z.read(folder+'nssoc_chip.mapped.json');name='shell.json'
            elif label=='boundary':
                assert report['pin_readback']['signal_pins']==269 and set(report['pin_readback']['supply_pins'])=={'VPWR','VGND'}
                key='core_lef';name='soc_top.lef';entry=report['views']['openroad_lef'];relative=entry['path'].split('/core-only-boundary-probe/',1)[1];data=z.read(relative);assert hashlib.sha256(data).hexdigest()==entry['sha256']
            else:key='placements';name='placements.json';data=(json.dumps(report['placement']['placements'],indent=2)+'\n').encode()
            path=OUT/name;path.write_bytes(data);inputs[key]=dict(path=str(path),sha256=sha(path))
        for key,relative,digest in [('tech','libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef','e3470344dfac5347b176fb3f8e0f0548d17a66b8f433626a8987dcb2ae4828b6'),
            ('std','libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef','c7575039af0b124e1834c407bfb9ac7a2db576d1e3533d98474dad3fbc2af589'),
            ('io','libs.ref/sg13g2_io/lef/sg13g2_io.lef','8b3dc3960960c08e07a1cde3dd9cd0484f5b12df07c4628726fff551bb775c0c')]:
            row=json.loads(subprocess.check_output(['gh','api','repos/IHP-GmbH/IHP-Open-PDK/contents/ihp-sg13g2/'+relative+'?ref='+REV]));data=base64.b64decode(row['content']);assert hashlib.sha256(data).hexdigest()==digest
            path=OUT/(key+'.lef');path.write_bytes(data);inputs[key]=dict(path=str(path),sha256=digest)
        r['artifacts']=sources;r['inputs']=inputs
        script=ROOT/'scripts/assemble_core_only_chip_native.py';app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        protected={str(p):sha(p)for p in [Path(__file__),script]};r['protected_inputs']=protected
        manifest=OUT/'inputs.json';manifest.write_text(json.dumps(dict(inputs=inputs,output=str(OUT)),indent=2)+'\n')
        r['status']='ASSEMBLING_PROVISIONAL_DATABASE';save()
        with (OUT/'native.log').open('w')as log:
            subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_ASSEMBLY_INPUTS=str(manifest)),stdout=log,stderr=subprocess.STDOUT,check=True)
        result=json.loads((OUT/'native-result.json').read_text());assert result['source_unchanged']and result['odb_readback_equal']and not result['accepted']
        assert all(sha(p)==h for p,h in protected.items())
        r.update(status=result['status'],native_result=result,sources_unchanged=True,
            scope='Provisional LEF macro for pre-DRT core, fixed native ring, real mapped shell cells with exact connectivity. Shell cells unplaced, no supply/signal routing, clock/CDC/timing/DRC/LVS/ESD or manufacturing acceptance.')
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
