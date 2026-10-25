#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh native v50 leaf wire RC with strict point/value/ownership auditing."""
import hashlib,io,json,os,subprocess,sys,tarfile,tokenize
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
TREE_FAULT_SELECTOR="# The actual new leaf must be a forest; every audited resistor is a bridge.\nresistor_rows=[(i,line.split()) for i,line in enumerate(rows) if re.fullmatch(r'R\\d+ \\S+ \\S+ \\S+',line)]\nassert len(resistor_rows)==len(parsed['resistors']) and len(resistor_rows)>0\nassert nx.is_forest(graph) and nx.number_connected_components(graph)==9\nassert 'P_ip' in anchor and 'T004_B' in anchor and anchor['P_ip']==anchor['T004_B']\nassert set(nx.node_connected_component(graph,'P_ip'))=={'P_ip','T004_B'}\ndrop_index,drop_fields=next((i,f) for i,f in resistor_rows if {f[1],f[2]}=={'P_ip','T004_B'})\ndropped_rows=rows[:drop_index]+rows[drop_index+1:]\ndropped_text='\\n'.join(dropped_rows)+'\\n'\ndropped_parsed=m.rawparser.parse_spice(dropped_text)\nassert len(dropped_parsed['resistors'])==len(parsed['resistors'])-1\nbroken=nx.Graph();broken.add_nodes_from(anchor);broken.add_edges_from((x,y)for x,y,v in dropped_parsed['resistors'])\nassert broken.degree('P_ip')==broken.degree('T004_B')==0\nassert nx.number_connected_components(broken)==10\nduplicate_text=text.replace('.ends','R_EXTRA_SAME_CONDUCTOR '+drop_fields[1]+' '+drop_fields[2]+' '+drop_fields[3]+'\\n.ends')\nduplicate_parsed=m.rawparser.parse_spice(duplicate_text)\nassert len(duplicate_parsed['resistors'])==len(parsed['resistors'])+1 and duplicate_text!=text\nassert 'P_ip' in anchor and 'P_inn' in anchor and anchor['P_ip']!=anchor['P_inn']\n"
ROOT=Path(__file__).resolve().parents[1]
# Restore the original cloud path so every native anchor input hash can be checked
# without rewriting any of the source graph, device or terminal reports.
OUT=ROOT/'hw/soc/out/cloud-cdr-active-levelshift-v50-wire-inputs'
STAGE=ROOT/'hw/soc/out/cloud-cdr-active-levelshift-v50-rc-transfer'
def check():
    m=json.loads((ROOT/'scripts/cdr-active-levelshift-v50-rc-method.json').read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    return m
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true' and not OUT.exists()
    check()
    STAGE.mkdir(parents=True,exist_ok=False);reports.OUT=STAGE
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,full_phy_accepted=False,closed_loop=False,
        scope='Exact actual v50 leaf metal/via RC:18native devices/50terminals,9wire components,40actual anchor points. Strict raw R/C value/point/topology checks and14corruptions. Wire-only geometry extracts no intrinsic devices. Original18intrinsic devices must be retained exactly once in subsequent composition. Substrate spreading/RF qualification,actual parent loading and bias,closed-loop/PVT/fullPHY remain unaccepted.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(command,label):
        log=OUT/(label+'.log')
        with log.open('w')as stream:rc=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=rc,log_sha256=sha(log)));save()
        if rc:print(log.read_text(errors='replace')[-16000:],flush=True)
        assert rc==0,(label,rc)
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-active-levelshift-v50-wire-inputs-pass-20261024.json').read_text())
        prior,proof=reports.restore_report('cdr-active-levelshift-v50-wire-inputs',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT,list(pin['outputs']))
        assert prior['outputs']==pin['outputs'] and prior['source_head']==pin['source_head'] and prior['sources_unchanged'] and prior['status']==pin['status']
        (OUT/'result.json').rename(OUT/'wire-inputs-source.json')
        r['physical_inputs']=proof;r['geometry']=prior['geometry'];r['anchors']=prior['anchors']
        assert r['geometry']['native_device_count']==18 and r['geometry']['native_terminal_count']==50 and r['geometry']['wire_component_count']==9
        assert r['anchors']['logical_anchor_count']==r['anchors']['physical_anchor_count']==40 and r['anchors']['public_ports']==8
        assert r['anchors']['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=32,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=18)
        save()
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text());rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'runtime.tar.gz'
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
            elif name=='audit-rc48.py':
                replacements={'12':'8','17':'9','18':'10','112':'40','154':'50','54':'18','100':'32'}
                counts=Counter();tokens=[]
                for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                    if tok.type==tokenize.NUMBER and tok.string in replacements:
                        counts[tok.string]+=1;tok=tok._replace(string=replacements[tok.string])
                    tokens.append(tok)
                assert set(counts)==set(replacements),counts
                text=tokenize.untokenize(tokens);changes.append(dict(numeric_census_token_changes=dict(counts),map=replacements))
                replace("==['18']","==['10']");replace("==['17']","==['9']")
            else:
                replace('cases=[\n',TREE_FAULT_SELECTOR+'cases=[\n')
                replace('R_EXTRA P_cp P_cn 1','R_EXTRA P_ip P_inn 1')
                replace(r"re.sub(r'^R\d+ .*\n','',text,count=1,flags=re.M)",'dropped_text')
                replace("('dropped_resistor',{'wires.spice':dropped_text},'Native/export resistor topology/value differs')",
                        "('dropped_resistor',{'wires.spice':dropped_text},'Physical wire R graph open or incomplete')")
                replace(" ('cross_conductor_short',",
                        " ('duplicated_resistor',{'wires.spice':duplicate_text},'Native/export resistor topology/value differs'),\n ('cross_conductor_short',")
                replace('PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS','PASS_REAL_NATIVE_BASELINE_AND14_RAW_CORRUPTION_CONTROLS')
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
        r['controls']=json.loads((wire/'native-mutations01.json').read_text());assert r['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND14_RAW_CORRUPTION_CONTROLS'and len(r['controls']['cases'])==14
        assert all(sha(OUT/n)==v for n,v in prior['outputs'].items())
        assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(wire/n)==v['adapted_sha256']for n,v in edits.items())
        assert sha(raw)==spec['raw_parser']['sha256'] and sha(OUT/'wire-inputs-source.json')==pin['summary_sha256']
        check()
        r['sources_unchanged']=True;r['status']='PASS_V50_LEAF18_FRESH_NATIVE_WIRE_RC_AND14_CONTROLS_REQUIRES_LOADED_CLOSED_LOOP'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        OUT.mkdir(parents=True,exist_ok=True)
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
