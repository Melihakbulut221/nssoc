#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh native whole-PD500 wire RC with strict point/value/ownership auditing."""
import hashlib,io,json,os,subprocess,sys,tarfile,tokenize
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
from cloud_cdr_v4_rc import NONBRIDGE_SELECTOR
import cdr_drain_m1_fresh_rc_legacy as admission
from cdr_drain_m1_fresh_rc_legacy import PIN,validate_summary as validate_source,methods as validate_methods
ROOT=Path(__file__).resolve().parents[1]
# Restore the original cloud path so every native anchor input hash can be checked
# without rewriting any of the source graph, device or terminal reports.
OUT=admission.ANALYSIS
STAGE=admission.RC_STAGE
def main():
    admission.authorize('rc')
    admission.assert_current_candidate_ready()
    STAGE.mkdir(parents=True,exist_ok=False);reports.OUT=STAGE
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,full_phy_accepted=False,closed_loop=False,
        scope='Whole actual PD500 metal/via RC. Native500device/1446terminal binding,113 independent wire components,978 actual points; strict raw R/C value/point/topology checks and13corruptions. Intrinsic MIM retained separately; wire-only geometry has no intrinsic device extraction. Substrate spreading/RF qualification, loaded electrical behavior and closed-loop acceptance remain separate.')
    def save():(STAGE/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(command,label):
        log=STAGE/(label+'.log')
        with log.open('w')as stream:rc=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=rc,log_sha256=sha(log)));save()
        if rc:print(log.read_text(errors='replace')[-16000:],flush=True)
        assert rc==0,(label,rc)
    pin=None;save()
    try:
        pin=json.loads(PIN.read_text());validate_source(pin);validate_methods()
        prior,proof=admission.restore_for_rc(pin,STAGE)
        r['physical_inputs']=proof;r['geometry']=prior['strict_wire_graph'];r['anchors']=prior['anchors']
        assert r['geometry']['native_device_count']==500 and r['geometry']['native_terminal_count']==1446 and r['geometry']['wire_component_count']==113
        assert r['anchors']['logical_anchor_count']==r['anchors']['physical_anchor_count']==978 and r['anchors']['public_ports']==25
        assert r['anchors']['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=953,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=493)
        save()
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text());rt=OUT/'magic-cloud';rt.mkdir();packed=STAGE/'runtime.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(rt,filter='data')
        packed.unlink();manifest=json.loads((rt/'manifest.json').read_text());assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())
        raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';raw.parent.mkdir(parents=True,exist_ok=True);fetch(spec['raw_parser']['url'],spec['raw_parser']['sha256'],raw)
        methods=json.loads((ROOT/'docs/evidence/cdr-v4-rc-inputs-20261017.json').read_text())['report']['original_extraction_methods']
        wire=OUT/'wire';edits={}
        for name in ('run-rc01.py','audit-rc48.py','mutations48.py'):
            meta=methods[name];text=meta['text'];assert hashlib.sha256(text.encode()).hexdigest()==meta['sha256'];changes=[]
            def replace(a,b):
                nonlocal text
                assert text.count(a)==1,(name,a,text.count(a));text=text.replace(a,b);changes.append(dict(before=a,after=b))
            if name=='run-rc01.py':
                replace("Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')","B.parent/'magic-cloud/runtime/lib'")
                replace("Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')","B.parent/'magic-cloud/tech'")
                replace('(2*1024**3,)*2','(4*1024**3,)*2')
                replace('size>80*1024**2','size>1024*1024**2');replace('OWNED_SCRATCH_80MIB_LIMIT','OWNED_SCRATCH_1024MIB_LIMIT')
            elif name=='audit-rc48.py':
                replace('original_devices=54','original_devices=500')
                replacements={'12':'25','17':'113','18':'114','112':'978','154':'1446','54':'493','100':'953'}
                counts=Counter();tokens=[]
                for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                    if tok.type==tokenize.NUMBER and tok.string in replacements:
                        counts[tok.string]+=1;tok=tok._replace(string=replacements[tok.string])
                    tokens.append(tok)
                assert set(counts)==set(replacements),counts
                text=tokenize.untokenize(tokens);changes.append(dict(numeric_census_token_changes=dict(counts),map=replacements))
                replace("==['18']","==['114']");replace("==['17']","==['113']")
            else:
                replace('cases=[\n',NONBRIDGE_SELECTOR+'cases=[\n')
                replace(r"re.sub(r'^R\d+ .*\n','',text,count=1,flags=re.M)",'dropped_text')
            assert not(wire/name).exists()
            (wire/name).write_text(text);edits[name]=dict(original_sha256=meta['sha256'],adapted_sha256=sha(wire/name),changes=changes)
        r['method_adaptations']=edits;r['magic_runtime']=runtime;save()
        run([sys.executable,'-m','py_compile',*[wire/n for n in edits]],'compile-native-methods')
        run([sys.executable,wire/'run-rc01.py'],'native-extraction')
        r['capture']=json.loads((wire/'rc03/result.json').read_text());save()
        assert r['capture']['returncode']==0 and r['capture']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'
        run([sys.executable,wire/'audit-rc48.py',wire/'rc03',wire/'anchors08.json',wire/'audit.json'],'native-audit')
        r['audit']=json.loads((wire/'audit.json').read_text());save();assert r['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        run([sys.executable,wire/'mutations48.py'],'native-fault-controls')
        r['controls']=json.loads((wire/'native-mutations01.json').read_text());assert r['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'and len(r['controls']['cases'])==13
        assert all(sha(OUT/n)==v for n,v in prior['outputs'].items())
        assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(wire/n)==v['adapted_sha256']for n,v in edits.items())
        assert sha(raw)==spec['raw_parser']['sha256']
        r['saved_capsule_integrity']=admission.verify_saved_inputs(pin)
        validate_methods();r['sources_unchanged']=True;r['status']='PASS_PD500_FRESH_NATIVE_WIRE_RC_AND13_CONTROLS_REQUIRES_LOADED_CLOSED_LOOP'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        try:
            if pin is not None and admission.CAPSULE.exists():
                r['saved_capsule_integrity']=admission.verify_saved_inputs(pin)
        except BaseException as error:
            r.update(status='FAIL_V59_SAVED_INPUT_INTEGRITY',integrity_error=repr(error));raise
        finally:
            admission.finalize_rc_outputs(r,STAGE,pin,save,sys.exc_info()[1])
if __name__=='__main__':main()
