#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Use the qualified double-total native producer on the actual8088 parent."""
import json,os,shutil,subprocess,sys,shlex
from pathlib import Path
from collections import Counter
from decimal import Decimal
import compare_cloud_routed_endpoints as reports
import tx_native_cap_order as cap_order
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-output8088-power128return64-precision'
OLD='e8f2d96121e704acee41e7a58c23feead887527e3bfc4f51da4d97aa8183970e'
PRECISE='1a44bd5c70af3800213419c2e3b2213285523a74fcc4b92bc9cf7314d93a592c'
def wire_records(path):
    records=Counter()
    for line in path.read_text().splitlines():
        if not line or line[0]not in ('R','C'):continue
        row=shlex.split(line);assert len(row)==4
        key=tuple(row)if row[0][0]=='R'else('C',*sorted(row[1:3]),Decimal(row[3]))
        records[key]+=1
    return records
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    method=json.loads((ROOT/'scripts/tx-output8088-power128return64-precision-method.json').read_text())
    baseline=ROOT/method['baseline_path'];assert sha(baseline)==method['baseline_sha256']
    source=baseline.read_text()
    for edit in method['edits']:
        assert source.count(edit['before'])==edit['count']
        source=source.replace(edit['before'],edit['after'])
    assert source==Path(__file__).read_text()and sha(Path(__file__))==method['candidate_sha256']
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,qualified_substrate=False,qualified_timing=False,serial_phy_complete=False,mainchip_integrated=False,full_parent_composed=False,electrical_passed=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(args,log):
        with log.open('w')as stream:p=subprocess.run(list(map(str,args)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(command=list(map(str,args)),returncode=p.returncode,log=str(log.relative_to(OUT)),sha256=sha(log)));save()
        if p.returncode:print(log.read_text(errors='replace')[-10000:],flush=True)
        assert p.returncode==0,(args,p.returncode)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128return64-native-rc-pass-20261023.json').read_text())
        assert pin['run']==39901168356 and pin['summary_sha256']=='2b19f65083554c59fc5a171eb89e25ce51bcc5f8f3f31de42024a554e049d729'
        evidence=OUT/'evidence'
        prior,proof=reports.restore_report('tx-output8088-power128return64-native-rc',pin['run'],pin['summary_sha256'],pin['parts_sha256'],evidence,list(pin['outputs']))
        assert prior['status']==pin['status'] and prior['outputs']==pin['outputs']
        assert prior['source_head']==pin['source_head']and prior['sources_unchanged']
        assert prior['audit']==pin['audit']and prior['controls']==pin['controls']
        assert prior['audit']['actual_exported_resistors']>0 and prior['audit']['actual_exported_capacitors']>0
        assert len(prior['controls']['cases'])==13
        r['physical_rc_source']=proof
        # The earlier unrelated startup failure remains in its immutable original report.
        qualified,proof=reports.restore_report('tx-raw64-totalcap-precision',39486998309,'bdcbddedf70af7e4bc9a1d6b3ec4ac334a619e2fe208244b83a6e8b74cc09a38','3b0dc36952ae38ac4ce1c1ea8e27cac8e4917ca7543a81a916a207b49adaa9e2',OUT/'producer',['precise-source/magic/tclmagic.so'])
        assert qualified['status']=='PASS_REBUILT_NATIVE8074_RC_DOUBLE_TOTALS_AND13_CONTROLS_NOT_COMPOSED_ELECTRICAL_OR_PHY_ACCEPTANCE'
        for key in ('sources_unchanged','baseline_reproduced_original_rc_and_failure','no_rc_records_changed','no_geometry_technology_or_threshold_change','both_native_input_orders_verified'):assert qualified[key]
        assert len(qualified['controls']['cases'])==len(qualified['historical_controls']['cases'])==13
        lib=OUT/'producer/precise-source/magic/tclmagic.so'
        assert sha(lib)==qualified['rebuilt_runtimes']['precise']['sha256']==PRECISE
        deps=subprocess.run(['ldd',str(lib)],capture_output=True,text=True)
        (OUT/'producer-ldd.log').write_text(deps.stdout+deps.stderr)
        r['producer_dependencies']=dict(returncode=deps.returncode,log=deps.stdout+deps.stderr)
        print('PRODUCER_DEPENDENCIES',deps.stdout+deps.stderr,flush=True);save()
        assert deps.returncode==0 and 'not found'not in deps.stdout+deps.stderr,'Qualified producer dependency missing'
        assert qualified['source_changes']['changed_only']=='resis/resis.h'
        r['qualified_producer']=proof;r['producer_library_sha256']=PRECISE
        methods=json.loads((ROOT/'scripts/tx-output8088-power128return64-rc-methods.json').read_text())
        for name,spec in methods.items():assert sha(evidence/name)==spec['adapted_sha256']
        assert sha(evidence/'magic-cloud/runtime/lib/magic/tcl/tclmagic.so')==PRECISE
        rawspec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())['raw_parser']
        parser=OUT/'pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';parser.parent.mkdir()
        fetch(rawspec['url'],rawspec['sha256'],parser)
        r['order_controls']=cap_order.controls()
        run([sys.executable,ROOT/'scripts/tx_reverse_native_cap_order.py','--controls'],OUT/'reverse-controls.log')
        original=wire_records(evidence/'rc01/wires.spice')
        assert sum(n for k,n in original.items()if k[0].startswith('R'))==prior['audit']['actual_exported_resistors']
        assert sum(n for k,n in original.items()if k[0]=='C')==prior['audit']['actual_exported_capacitors']
        r['variants']={}
        for label in ('precise','precise_reversed'):
            b=OUT/label;b.mkdir()
            shutil.copytree(evidence/'native01',b/'native01')
            shutil.copytree(evidence/'magic-cloud',b/'magic-cloud')
            target=b/'magic-cloud/runtime/lib/magic/tcl/tclmagic.so';shutil.copyfile(lib,target);assert sha(target)==PRECISE
            anchors=json.loads((evidence/'anchors03.json').read_text())
            old='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-output8088-power128return64-native-rc/'
            mapped={}
            for name,digest in anchors['inputs'].items():
                if name.startswith(old):p=evidence/name[len(old):]
                else:
                    prefix='/home/runner/work/nssoc/nssoc/';assert name.startswith(prefix);p=ROOT/name[len(prefix):]
                assert sha(p)==digest;mapped[str(p)]=digest
            anchors['inputs']=mapped;(b/'anchors03.json').write_text(json.dumps(anchors,indent=2)+'\n')
            for name in ('run-rc01.py','audit-rc02.py','mutations01.py'):
                text=(evidence/name).read_text()
                if name=='run-rc01.py':
                    assert text.count(PRECISE)==1 and OLD not in text
                    if label=='precise_reversed':
                        marker="'extract all',";assert text.count(marker)==1
                        command='exec /usr/bin/python3 {'+str(ROOT/'scripts/tx_reverse_native_cap_order.py')+'} {'+str(b/'rc01/full_tx_output8088_power128return64_wires.ext')+'}'
                        text=text.replace(marker,marker+repr(command)+',')
                (b/name).write_text(text)
            for name in ('audit-rc02.py','mutations01.py'):assert sha(b/name)==sha(evidence/name)
            run([sys.executable,b/'run-rc01.py'],OUT/(label+'-native.log'))
            native=json.loads((b/'rc01/result.json').read_text())
            r.setdefault('native_attempts',{})[label]=native;save()
            if native['returncode']!=0:print((b/'rc01/native.log').read_text(errors='replace')[-12000:],flush=True)
            assert native['returncode']==0 and native['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'
            run([sys.executable,b/'audit-rc02.py',b/'rc01',b/'anchors03.json',b/'audit.json'],OUT/(label+'-audit.log'))
            audit=json.loads((b/'audit.json').read_text())
            r['variants'][label]=dict(native=native,audit=audit);save()
            assert audit['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
            assert wire_records(b/'rc01/wires.spice')==original,'Native R/C records changed'
            _,equivalence=cap_order.reorder((b/'rc01/full_tx_output8088_power128return64_wires.ext').read_text(),(evidence/'rc01/full_tx_output8088_power128return64_wires.ext').read_text())
            r['variants'][label]['source_equivalence']=equivalence
            run([sys.executable,b/'mutations01.py'],OUT/(label+'-controls.log'))
            controls=json.loads((b/'native-mutations01.json').read_text())
            assert controls['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'and len(controls['cases'])==13
            r['variants'][label]['controls']=controls
            for p in (evidence/'magic-cloud').rglob('*'):
                if p.is_file()and p.relative_to(evidence/'magic-cloud')!=Path('runtime/lib/magic/tcl/tclmagic.so'):
                    assert sha(p)==sha(b/'magic-cloud'/p.relative_to(evidence/'magic-cloud'))
            save()
        reversal=json.loads((OUT/'precise_reversed/rc01/full_tx_output8088_power128return64_wires.order-proof.json').read_text())
        assert reversal['reversed_enumeration']and reversal['symmetric_endpoint_value_multiset_exact']and reversal['non_coupling_records_unchanged']
        r['reversal']=reversal
        assert all(sha(evidence/n)==digest for n,digest in prior['outputs'].items())
        assert sha(parser)==rawspec['sha256']and sha(lib)==PRECISE
        r.update(status='PASS_ACTUAL8088_POWER128RETURN64_NATIVE_RC_DOUBLE_TOTALS_TWO_ORDERS_AND13_CONTROLS_EACH_NOT_FULL_PHY',sources_unchanged=True,no_rc_records_changed=True,no_geometry_technology_or_threshold_change=True,both_native_input_orders_verified=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
