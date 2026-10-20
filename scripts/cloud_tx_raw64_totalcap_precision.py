#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Rebuild archived native Magic with only total-load storage precision changed.

Baseline must reproduce the failed native wire model. Candidate must preserve
all R/C records and pass the unchanged raw auditor and thirteen corruptions.
No post-extraction numeric edits and no tolerance/PDK/geometry changes.
"""
import hashlib,io,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
from collections import Counter
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-raw64-totalcap-precision'
MAGIC_OLD='e8f2d96121e704acee41e7a58c23feead887527e3bfc4f51da4d97aa8183970e'
SOURCE_PREFIX='hw/soc/tools/magic-groundcap-combined-8.3.623/'
MANIFEST_SHA='f13e9ee0e4930db1b4b83771a060046fa41356b51023ce916be590a9f7b735e4'
SOURCE_URL='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-tools-20261013-000/'
HEADER_EDITS=[
    ('    float\trg_nodecap; /* Legacy total load, including coupling. */',
     '    double\trg_nodecap; /* Legacy total load, including coupling. */'),
    ('    float\t\tcapacitance;\t/* Capacitance between node and   */',
     '    double\t\tcapacitance;\t/* Capacitance between node and   */')]
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,qualified_substrate=False,qualified_timing=False,serial_phy_complete=False,mainchip_integrated=False,full_parent_composed=False,electrical_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,log,cwd=ROOT):
        with log.open('w')as stream:
            p=subprocess.run(list(map(str,cmd)),cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(command=list(map(str,cmd)),cwd=str(cwd),returncode=p.returncode,log=str(log.relative_to(OUT)),log_sha256=sha(log)));save()
        if p.returncode:print(log.read_text(errors='replace')[-12000:],flush=True)
        assert p.returncode==0,(cmd,p.returncode)
    save()
    try:
        diagnosis=json.loads((ROOT/'docs/evidence/tx-raw64-totalcap-diagnosis-pass-20261020.json').read_text())
        assert diagnosis['run']==39479905356 and diagnosis['summary_sha256']=='9c5e2a0ae2187bf44fa92d911003eec17d02a6416b28b8d38dccd5e95243ab5b'
        assert diagnosis['report']['status']=='PASS_NATIVE_BINARY32_TOTAL_LOAD_DIAGNOSIS_NOT_RC_ACCEPTANCE'
        assert len(diagnosis['report']['all_native_totals'])==698 and len(diagnosis['report']['controls'])==4
        pin=json.loads((ROOT/'docs/evidence/tx-raw64-native-rc-witness-rejection-20261020.json').read_text())
        # Obtain immutable summary first so the whole source inventory is explicit.
        raw=OUT/'failed-summary.json'
        fetch('https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-39477040508-1-tx-raw64-native-rc/tx-raw64-native-rc-39477040508-1.summary.json',pin['summary_sha256'],raw)
        original=json.loads(raw.read_text())
        prior,proof=reports.restore_report('tx-raw64-native-rc',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'evidence',list(original['outputs']))
        assert prior==original and prior['status']=='FAIL_OR_ERROR'
        r['failed_source']=proof
        evidence=OUT/'evidence'
        assert sha(evidence/'magic-cloud/runtime/lib/magic/tcl/tclmagic.so')==MAGIC_OLD
        methods=json.loads((ROOT/'scripts/tx-raw64-rc-methods.json').read_text())
        for name,d in methods.items():assert sha(evidence/name)==d['adapted_sha256']
        # Restore all regular source files from the exact cloud migration.
        mp=OUT/'source.manifest.json';fetch(SOURCE_URL+'batch-000002.manifest.json',MANIFEST_SHA,mp)
        manifest=json.loads(mp.read_text());parts=manifest['parts']
        assert manifest['encoding']=='tar-gzip'and len(parts)==1
        assert parts[0]['sha256']=='d8fede9cfc6163644b8cdae26b1c044d13ec85444b5047d97e3828ddb9602e4f'
        entries={d['path']:d for d in manifest['records']if d['path'].startswith(SOURCE_PREFIX)}
        assert len(entries)==2057
        package=OUT/'archived-source.tar.gz';fetch(parts[0]['url'],parts[0]['sha256'],package);assert package.stat().st_size==parts[0]['bytes']
        source=OUT/'archived-source';source.mkdir();found=set()
        with tarfile.open(package,'r:gz')as archive:
            for member in archive:
                name=member.name.removeprefix('./')
                if name not in entries:continue
                assert member.isfile()and name not in found
                data=archive.extractfile(member).read();spec=entries[name]
                assert len(data)==spec['bytes']and hashlib.sha256(data).hexdigest()==spec['sha256']
                rel=name[len(SOURCE_PREFIX):];assert '..'not in Path(rel).parts and not Path(rel).is_absolute()
                dst=source/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data);dst.chmod(spec['mode']&0o777);found.add(name)
        assert found==set(entries);package.unlink()
        r['source_restore']=dict(manifest_sha256=MANIFEST_SHA,archive=parts[0],files=len(found),every_file_hash_verified=True)
        # Recreate the exact existing v2/v3/v4 source patches, before any new change.
        import patch_magic_coupled_cap_v2 as coupled
        import patch_magic_cap_precision_v3 as precise
        import patch_magic_area_product_v4 as area
        baseline=OUT/'baseline-source';shutil.copytree(source,baseline)
        # The archived combined tree predates the separate HBT/tap/ESD native
        # overlays used by the published runtime. Restore those exact existing
        # producer patches in BOTH builds before comparing the precision change.
        import patch_magic_hbt_contract_v2 as hbt_contract
        import patch_magic_hbt_multiplicity_v3 as hbt_multiplicity
        import patch_magic_finite_tap_v1 as finite_tap
        import patch_magic_esd_v1 as esd
        historical=[]
        def apply(relative,method):
            target=baseline/relative;before=sha(target)
            target.write_bytes(method(target.read_bytes()))
            historical.append(dict(path=relative,before=before,after=sha(target)))
        apply('extract/ExtBasic.c',lambda data:hbt_contract.patch('ExtBasic.c',data))
        apply('extract/ExtBasic.c',hbt_multiplicity.patch)
        for name in ('ExtBasic.c','ExtTech.c'):
            apply('extract/'+name,lambda data,name=name:finite_tap.patch(name,data))
        for name in ('CIFrdtech.c','CIFgen.c'):
            apply('cif/'+name,lambda data,name=name:esd.patch(name,data))
        r['restored_historical_device_code']=dict(edits=historical,methods={Path(m.__file__).name:sha(Path(m.__file__))for m in (hbt_contract,hbt_multiplicity,finite_tap,esd)},technology_files_unchanged=True)
        for name in coupled.SOURCES:
            p=baseline/'resis'/name;p.write_bytes(coupled.patch(name,p.read_bytes()))
        patch3=OUT/'patch3';precise.patch(baseline,patch3)
        for name in precise.EDITS:shutil.copyfile(patch3/name,baseline/name)
        patch4=OUT/'patch4';area.patch(baseline,patch4)
        shutil.copyfile(patch4/'ResMakeRes.c',baseline/'resis/ResMakeRes.c')
        assert sha(baseline/'resis/resis.h')=='f70ea5aac67a40a5cfcb73bb9485ab114a26655fe3f7c8abd10456810b6a7df6'
        source_files={str(p.relative_to(baseline)):sha(p)for p in baseline.rglob('*')if p.is_file()and p.suffix in ('.c','.h')}
        fixed=OUT/'precise-source';shutil.copytree(baseline,fixed)
        h=fixed/'resis/resis.h';text=h.read_text()
        for old,new in HEADER_EDITS:
            assert text.count(old)==1; text=text.replace(old,new)
        h.write_text(text)
        actual={str(p.relative_to(fixed)):sha(p)for p in fixed.rglob('*')if p.is_file()and p.suffix in ('.c','.h')}
        assert set(actual)==set(source_files)
        assert [n for n in source_files if source_files[n]!=actual[n]]==['resis/resis.h']
        r['source_changes']=dict(baseline=source_files,candidate=actual,changed_only='resis/resis.h',edits=HEADER_EDITS,full_rebuild_required_for_struct_abi=True,ground_cap_distribution_and_wire_rules_unchanged=True)
        runtimes={}
        for label,build in [('baseline',baseline),('precise',fixed)]:
            # These are private restored copies; no object can survive a changed ABI.
            for p in build.rglob('*'):
                if p.is_file()and(p.suffix in ('.o','.a','.so')or p.name in ('config.cache','config.status')):p.unlink()
            assert not list(build.rglob('*.o'))
            run(['sh','configure','--prefix='+str(OUT/(label+'-install'))],OUT/(label+'-configure.log'),build)
            run(['make','-j2'],OUT/(label+'-build.log'),build)
            library=build/'magic/tclmagic.so';assert library.is_file()and library.stat().st_size>1000000
            assert all(sha(build/n)==digest for n,digest in (source_files if label=='baseline'else actual).items())
            runtimes[label]=dict(library=str(library),sha256=sha(library))
        r['rebuilt_runtimes']=runtimes;save()
        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser']
        raw_parser=OUT/'pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';raw_parser.parent.mkdir()
        fetch(rawspec['url'],rawspec['sha256'],raw_parser)
        def wire_records(p):
            return Counter(line for line in p.read_text().splitlines()if line and line[0]in ('R','C'))
        original_wire=wire_records(evidence/'rc01/wires.spice')
        assert sum(n for s,n in original_wire.items()if s.startswith('R'))==137221
        assert sum(n for s,n in original_wire.items()if s.startswith('C'))==98241
        for label in ('baseline','precise'):
            b=OUT/label;b.mkdir()
            shutil.copytree(evidence/'native01',b/'native01')
            shutil.copytree(evidence/'magic-cloud',b/'magic-cloud')
            library=b/'magic-cloud/runtime/lib/magic/tcl/tclmagic.so'
            shutil.copyfile(runtimes[label]['library'],library);assert sha(library)==runtimes[label]['sha256']
            a=json.loads((evidence/'anchors03.json').read_text());old='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-raw64-native-rc/'
            changed={}
            for name,digest in a['inputs'].items():
                if name.startswith(old):p=evidence/name[len(old):]
                else:
                    prefix='/home/runner/work/nssoc/nssoc/';assert name.startswith(prefix);p=ROOT/name[len(prefix):]
                assert sha(p)==digest;changed[str(p)]=digest
            a['inputs']=changed;(b/'anchors03.json').write_text(json.dumps(a,indent=2)+'\n')
            for name in ('run-rc01.py','audit-rc02.py','mutations01.py'):
                text=(evidence/name).read_text()
                if name=='run-rc01.py':
                    assert text.count(MAGIC_OLD)==1;text=text.replace(MAGIC_OLD,runtimes[label]['sha256'])
                (b/name).write_text(text)
            assert sha(b/'audit-rc02.py')==sha(evidence/'audit-rc02.py')
            assert sha(b/'mutations01.py')==sha(evidence/'mutations01.py')
            run([sys.executable,b/'run-rc01.py'],OUT/(label+'-native.log'))
            run([sys.executable,b/'audit-rc02.py',b/'rc01',b/'anchors03.json',b/'audit.json'],OUT/(label+'-audit.log'))
            audit=json.loads((b/'audit.json').read_text());r[label+'_audit']=audit;save()
            expected_status='FAIL_EXPORTED_TERMINAL_AND_CAPACITANCE_CONTRACT'if label=='baseline'else'PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
            assert audit['status']==expected_status,(label,audit['status'],audit.get('error'))
            assert wire_records(b/'rc01/wires.spice')==original_wire,'Rebuilt native R/C records differ from archived failed extraction'
            if label=='baseline':
                assert audit['status']=='FAIL_EXPORTED_TERMINAL_AND_CAPACITANCE_CONTRACT'
                assert audit['wrong_native_branch_witnesses']==prior['audit']['wrong_native_branch_witnesses']
                assert not audit['disconnected_probes']and audit['complete_collapsed_capacitance_conserved']
                r['baseline_reproduced_original_rc_and_failure']=True
            else:
                assert audit['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
                assert not audit['wrong_native_branch_witnesses']
                run([sys.executable,b/'mutations01.py'],OUT/'precise-controls.log')
                controls=json.loads((b/'native-mutations01.json').read_text())
                assert controls['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'
                assert len(controls['cases'])==13;r['controls']=controls
        assert all(sha(evidence/n)==v for n,v in prior['outputs'].items())
        assert sha(raw_parser)==rawspec['sha256']and sha(mp)==MANIFEST_SHA
        r.update(status='PASS_REBUILT_NATIVE8074_RC_DOUBLE_TOTALS_AND13_CONTROLS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE',sources_unchanged=True,no_rc_records_changed=True,no_geometry_technology_or_threshold_change=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
