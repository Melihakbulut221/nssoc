#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh all-metal RC for actual54device XOR parent, not just added wires."""
import io,json,os,subprocess,sys,tarfile,tokenize
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-v3-rc'
TOP='nssoc_cdr_xor_load_parent_v3'
NONBRIDGE_SELECTOR="# Select one real R whose deletion preserves every connected component.\nresistor_rows=[(i,line.split()) for i,line in enumerate(rows) if re.fullmatch(r'R\\d+ \\S+ \\S+ \\S+',line)]\nassert len(resistor_rows)==len(parsed['resistors'])\nfrom collections import Counter\nedge_counts=Counter(frozenset((f[1],f[2])) for i,f in resistor_rows)\nbridges={frozenset(e) for e in nx.bridges(graph)}\ndrop_index,drop_fields=next((i,f) for i,f in resistor_rows if edge_counts[frozenset((f[1],f[2]))]>1 or frozenset((f[1],f[2])) not in bridges)\ndropped_rows=rows[:drop_index]+rows[drop_index+1:]\ndropped_text='\\n'.join(dropped_rows)+'\\n'\ndropped_parsed=m.rawparser.parse_spice(dropped_text)\nassert len(dropped_parsed['resistors'])==len(parsed['resistors'])-1\nkept_graph=nx.Graph();kept_graph.add_edges_from((x,y) for x,y,v in dropped_parsed['resistors'])\nassert set(kept_graph)==set(graph)\nassert {frozenset(c) for c in nx.connected_components(kept_graph)}=={frozenset(c) for c in nx.connected_components(graph)}\n"

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,full_phy_accepted=False,
        scope='Fresh distributed native metalRC for full54device XOR parent including original core and newcrossed metal/vias. All154native terminals:100metal/54intrinsicbody;10publicports,15independentphysical wire components. Strict native raw-R/C point/value/topology audit and13corruptions. No substrate spreading/RF qualification, loaded electrical acceptance, fullCDR ormainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(command,label):
        log=OUT/(label+'.log')
        with log.open('w')as stream:code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code,log_sha256=sha(log)));save()
        if code:print(log.read_text(errors='replace')[-16000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-v3-rc-inputs-20261017.json').read_text())
        prior,proof=reports.restore_report('cdr-v3-rc-inputs',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'inputs',list(pin['report']['outputs']))
        assert prior==pin['report']and prior['native_planes']['status']=='PASS_NATIVE54_XOR_PARENT22_PLANES_AND_FOUR_MAPPING_CONTROLS';r['physical_inputs']=proof
        runtime=json.loads((ROOT/'docs/evidence/pcie-magic-cloud-runtime-20261013.json').read_text());rt=OUT/'magic-cloud';rt.mkdir();packed=OUT/'runtime.tar.gz'
        fetch(runtime['receipt']['url'],runtime['receipt']['sha256'],packed)
        with tarfile.open(packed)as tar:tar.extractall(rt,filter='data')
        packed.unlink();manifest=json.loads((rt/'manifest.json').read_text());assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text())
        raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';raw.parent.mkdir(parents=True,exist_ok=True);fetch(spec['raw_parser']['url'],spec['raw_parser']['sha256'],raw)
        wire=OUT/'wire96';wire.mkdir();edits={}
        for name,meta in prior['original_extraction_methods'].items():
            original=OUT/'inputs/original-methods'/name;assert sha(original)==meta['sha256']and original.read_text()==meta['text']
            text=meta['text'];changes=[]
            for a,b in [("/'layout91/","/'inputs/parent/integrated/"),("/'physical92/lvs/","/'inputs/parent/physical/lvs_flat/"),
                ('nssoc_tx_mux2_passive_topmetal_layout_v1',TOP),
                ("Path('/dev/shm/nssoc-magic-area-product-v4-build/runtime/lib')","B.parent/'magic-cloud/runtime/lib'"),
                ("Path('/dev/shm/nssoc-magic-pad-stack-tech-v1')","B.parent/'magic-cloud/tech'")]:
                if a in text:changes.append(dict(before=a,after=b,count=text.count(a)));text=text.replace(a,b)
            specific=[]
            if name=='probe01.py':specific=[('c.pin_count()==12','c.pin_count()==10')]
            if name=='anchors01.py':specific=[('len(anchors)==112','len(anchors)==110'),('public_ports=12','public_ports=10')]
            if name=='dedup01.py':specific=[('len(anchors)>12','len(anchors)>10')]
            if name=='audit-rc48.py':
                # Explicit census changes only. Confirm15components and110unique probes
                # from the independent native graph BEFORE running this auditor.
                counts=Counter();tokens=[]
                for tok in tokenize.generate_tokens(io.StringIO(text).readline):
                    if tok.type==tokenize.NUMBER and tok.string in ('12','17','18','112'):
                        counts[tok.string]+=1;tok=tok._replace(string={'12':'10','17':'15','18':'16','112':'110'}[tok.string])
                    tokens.append(tok)
                assert set(counts)=={'12','17','18','112'},counts
                text=tokenize.untokenize(tokens);changes.append(dict(numeric_census_token_changes=dict(counts),map={'12':10,'17':15,'18':16,'112':110}))
                specific=[("==['18']","==['16']"),("==['17']","==['15']")]
            if name=='mutations48.py':
                specific=[('R_EXTRA P_cp P_cn 1','R_EXTRA P_qp P_qn 1'),('cases=[\n',NONBRIDGE_SELECTOR+'cases=[\n'),("re.sub(r'^R\\d+ .*\\n','',text,count=1,flags=re.M)",'dropped_text')]
            for a,b in specific:
                assert text.count(a)==1,(name,a,text.count(a));text=text.replace(a,b);changes.append(dict(before=a,after=b,count=1))
            (wire/name).write_text(text);edits[name]=dict(original_sha256=meta['sha256'],adapted_sha256=sha(wire/name),changes=changes)
        r['method_adaptations']=edits;save()
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        for method in ('probe01.py','locate01.py','anchors01.py','dedup01.py'):run([app,'python',wire/method],method)
        geometry=json.loads((wire/'native05/result.json').read_text());anchors=json.loads((wire/'anchors08.json').read_text())
        assert geometry['native_device_count']==54 and geometry['wire_component_count']==15
        assert set(geometry['native_ports'])=={'dp','dn','ep','en','qp','qn','avdd','avss','sub','iref'}
        assert geometry['native_terminal_count']==154 and anchors['public_ports']==10
        assert anchors['logical_anchor_count']==anchors['physical_anchor_count']==110
        assert anchors['dispositions']==dict(ACTUAL_TERMINAL_METAL_POINT_REFERENCE=100,RETAINED_INTRINSIC_BODY_NO_SUBSTRATE_RESISTANCE=54)
        r['geometry']=geometry;r['anchors']=anchors;save()
        run([sys.executable,wire/'run-rc01.py'],'native-extraction')
        r['capture']=json.loads((wire/'rc03/result.json').read_text());save()
        assert r['capture']['returncode']==0 and r['capture']['status']=='NATIVE_COMPLETE_AWAITING_RC_AUDIT'
        run([sys.executable,wire/'audit-rc48.py',wire/'rc03',wire/'anchors08.json',wire/'audit.json'],'native-audit')
        r['audit']=json.loads((wire/'audit.json').read_text());save();assert r['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        run([sys.executable,wire/'mutations48.py'],'native-fault-controls')
        r['controls']=json.loads((wire/'native-mutations01.json').read_text());assert r['controls']['status']=='PASS_REAL_NATIVE_BASELINE_AND13_RAW_CORRUPTION_CONTROLS'and len(r['controls']['cases'])==13
        assert all(sha(OUT/'inputs'/n)==v for n,v in prior['outputs'].items())
        assert all(sha(rt/n)==v['sha256']for n,v in manifest['files'].items())
        assert all(sha(wire/n)==v['adapted_sha256']for n,v in edits.items())
        r['sources_unchanged']=True;r['status']='PASS_XOR_PARENT54_FULL_METAL_NATIVE_RC_AND13_CONTROLS_REQUIRES_COMPOSITION_WAVES_CDR'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
