#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compose exact54 native XOR devices with every fresh4020R/2641C record."""
import hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-xor-composition'
RC=ROOT/'hw/soc/out/cloud-cdr-xor-rc'
TOP='nssoc_cdr_xor_load_parent_v2';COMPACT='nssoc_cdr_xor54_compact_v2';WIRE='nssoc_cdr_xor54_wire_v2'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,full_phy_accepted=False,
        scope='Exact native54LVS devices converted with pinnedPDK models and everyfresh4020R/2641C record attached at native physical terminal planes. Tenpublicports plus separatewire_cref. Full154namedterminal binding/finite27contacts and sixactualcompositionmutations. No loaded transient, substrate spreading/RF qualification, fullCDR/PHY or mainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label):
        log=OUT/(label+'.log')
        with log.open('w')as f:rc=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=rc,log_sha256=sha(log)));save()
        if rc:print(log.read_text(errors='replace')[-14000:],flush=True)
        assert rc==0,(label,rc)
    def restore(receipt,dest):
        packed=OUT/'restore.tar.gz';fetch(receipt['url'],receipt['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(dest,filter='data')
        packed.unlink()
    save()
    try:
        rc_pin=json.loads((ROOT/'docs/evidence/cdr-xor-parent-rc-pass-20261017.json').read_text())
        source,proof=reports.restore_report('cdr-xor-rc',rc_pin['run'],rc_pin['summary_sha256'],rc_pin['parts_sha256'],RC,list(rc_pin['report']['outputs']))
        assert source==rc_pin['report']and source['sources_unchanged']and source['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        assert source['audit']['actual_exported_resistors']==4020 and source['audit']['actual_exported_capacitors']==2641
        assert len(source['controls']['cases'])==13;r['rc_source']=proof
        methodpin=json.loads((ROOT/'docs/evidence/cdr-xor-binding-inputs-20261017.json').read_text())
        methods,methodsproof=reports.restore_report('cdr-binding-inputs',methodpin['run'],methodpin['summary_sha256'],methodpin['parts_sha256'],OUT/'original-binding',list(methodpin['report']['outputs']))
        assert methods==methodpin['report'];r['binding_source']=methodsproof
        layout=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text());restore(layout['receipt'],ROOT)
        manifest=json.loads((ROOT/'manifest.json').read_text());assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        electrical=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-input-20261013.json').read_text());models=OUT/'model-inputs';models.mkdir();restore(electrical['receipt'],models)
        mm=json.loads((models/'manifest.json').read_text());assert all(sha(models/n)==v['sha256']for n,v in mm['files'].items())
        target=ROOT/'pdk/libs.tech/ngspice/models';target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(models/'models',target)
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-composition-input-20261013.json').read_text());helper=ROOT/'hw/soc/out/pcie-tail115-connected570-source-20261006/compose_source01.py';helper.parent.mkdir(parents=True,exist_ok=True);fetch(spec['helpers']['composition_parser']['url'],spec['helpers']['composition_parser']['sha256'],helper)
        # Keep original extracted files untouched; generated model files live separately.
        workspace=OUT/'model';workspace.mkdir();b=workspace/'binding96';b.mkdir();wire=workspace/'wire96';wire.mkdir()
        for name in ['anchors08.json','native-mutations01.json','audit.json','rc03/wires.spice']:
            dst=wire/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(RC/'wire96'/name,dst)
        adaptations={}
        for name,meta in methods['methods'].items():
            original=OUT/'original-binding'/name;assert sha(original)==meta['sha256'];text=original.read_text();changes=[]
            for a,z in [("B.parent/'physical92/lvs", "Path('"+str(RC/'inputs/parent/physical/lvs_flat')),
                ('nssoc_tx_mux2_passive_topmetal_layout_v1',TOP),
                ("Path('/home/hasanmelih/.ciel/ciel/ihp-sg13g2/versions/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2')","R/'pdk'"),
                ('nssoc_tx_mux54_compact_v1',COMPACT),('c.pin_count()==12','c.pin_count()==10'),
                ("{'ap','an','bp','bn','sp','sn','op','on','avdd','avss','sub','iref'}and len(ports)==12","{'dp','dn','ep','en','qp','qn','avdd','avss','sub','iref'}and len(ports)==10")]:
                # Paths require closing the newlyintroduced Path(...) call before
                # the original quote/delimiter. Handle explicit complete paths below.
                if a.startswith("B.parent/"):continue
                if a in text:changes.append(dict(before=a,after=z,count=text.count(a)));text=text.replace(a,z)
            for suffix in ['','/extracted.cir','/audit.json','/result.lvsdb']:
                a="B.parent/'physical92/lvs"+suffix+"'";z='Path('+repr(str(RC/'inputs/parent/physical/lvs_flat')+suffix)+')'
                if a in text:changes.append(dict(before=a,after=z,count=text.count(a)));text=text.replace(a,z)
            assert 'physical92/'not in text and 'nssoc_tx_mux2_passive_topmetal_layout_v1'not in text
            (b/name).write_text(text);adaptations[name]=dict(original_sha256=meta['sha256'],adapted_sha256=sha(b/name),changes=changes)
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==layout['runtime_sha256']
        run([app,'python',b/'export01.py'],'export-native54')
        run([sys.executable,b/'build-devices01.py'],'bind-native54-models')
        native=json.loads((b/'binding01.json').read_text());assert native['status']=='PASS_NATIVE54_MODEL_AND_TERMINAL_BINDING'and len(native['devices'])==54
        for name in ['compose49.py','check-compose98.py']:
            src=RC/'wire96'/name;text=src.read_text();changes=[]
            pairs=[('nssoc_tx_mux54_wire_v1',WIRE),("B/'audit48.json'","B/'audit.json'"),
                ("M=B.parent.parent/'pcie-tail115-connected570-source-20261006/compose_source01.py'",'M=Path('+repr(str(helper))+')'),
                ('dict(devices=54,R=229,C=301)','dict(devices=54,R=4020,C=2641)'),
                ('PASS_ALL54_NATIVE_DEVICES530_WIRES_AND_SIX_COMPOSITION_FAULTS','PASS_ALL54_NATIVE_DEVICES6661_WIRES_AND_SIX_COMPOSITION_FAULTS'),
                ('112actual metal reference points,17wire conductors','110actual metal reference points,15wire conductors')]
            for a,z in pairs:
                if a in text:changes.append(dict(before=a,after=z,count=text.count(a)));text=text.replace(a,z)
            (wire/name).write_text(text);adaptations[name]=dict(original_sha256=sha(src),adapted_sha256=sha(wire/name),changes=changes)
        r['method_adaptations']=adaptations;save()
        run([sys.executable,wire/'compose49.py'],'compose-actual-device-wire-model')
        run([sys.executable,wire/'check-compose98.py'],'verify-native-model-and-six-mutations')
        composed=json.loads((wire/'composition01.json').read_text());controls=json.loads((wire/'composition-controls98.json').read_text())
        assert composed['counts']==controls['counts']==dict(devices=54,R=4020,C=2641)and len(controls['controls'])==6
        assert controls['status']=='PASS_ALL54_NATIVE_DEVICES6661_WIRES_AND_SIX_COMPOSITION_FAULTS'
        r['native_binding']=native;r['composition']=composed;r['controls']=controls
        for original,name in [(b/'mux54-compact01.spice','xor54-compact.spice'),(wire/'mux54-wire01.spice','xor54-wire.spice')]:shutil.copyfile(original,OUT/name)
        # Preserve source-bound model inputs and all native terminal/RC proofs.
        assert all(sha(RC/n)==v for n,v in source['outputs'].items())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(models/n)==v['sha256']for n,v in mm['files'].items())
        r.update(status='PASS_NATIVE54_XOR_FULL_RC_COMPOSITION_AND_SIX_CONTROLS_REQUIRES_LOADED_WAVES',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
