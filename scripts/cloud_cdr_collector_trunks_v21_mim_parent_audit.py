#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict MIM-aware PD484 raw R/C auditing with unchanged wire conservation gates."""
import difflib,hashlib,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
from unittest.mock import patch
import compare_cloud_routed_endpoints as reports
import audit_cdr_collector_trunks_v21_mim_intrinsic
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-cdr-collector-trunks-v21-mim-parent-audit'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],qualified_pex=False,closed_loop=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    def run(cmd,label):
        path=OUT/(label+'.log')
        with path.open('w')as log:code=subprocess.call(list(map(str,cmd)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        r.setdefault('commands',[]).append(dict(label=label,returncode=code,log_sha256=sha(path)));save()
        if code:print(path.read_text(errors='replace')[-14000:],flush=True)
        assert code==0,(label,code)
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/cdr-collector-trunks-v21-mim-parent-capture-pass-20261020.json').read_text())
        prior,proof=reports.restore_report('cdr-collector-trunks-v21-mim-parent-rc',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'capture',list(pin['report']['outputs']))
        assert prior==pin['report']and prior['sources_unchanged'];r['capture_source']=proof
        binding_pin=json.loads((ROOT/'docs/evidence/cdr-collector-trunks-v21-binding-pass-20261020.json').read_text())
        assert prior['model_binding_source']['summary_sha256']==binding_pin['summary_sha256']
        assert prior['model_binding_source']['run']==binding_pin['run']
        r['intrinsic_binding_source']=dict(run=binding_pin['run'],summary_sha256=binding_pin['summary_sha256'])

        B=OUT/'capture/wire';P=B/'rc03';source=OUT/'capture/source/wire/audit-rc48.py';text=source.read_text();edits=[]
        def replace(a,b):
            nonlocal text
            assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b);edits.append(dict(before=a,after=b))
        replace('import networkx as nx','import networkx as nx\nimport sys\nsys.path.insert(0,str(Path.cwd()/"scripts"))\nfrom audit_cdr_collector_trunks_v21_mim_intrinsic import validate_mim')
        replace("require(not after['devices'] and not before['devices'] and not before['resistors'],'Device insertion into wire-only graph')","require(not before['resistors'],'Unexpected baseline resistor insertion')")
        replace("require(native_r==export_r,'Native/export resistor topology/value differs')","require(native_r==export_r,'Native/export resistor topology/value differs')\n mim_proof=validate_mim(rows,rep,before,after,original,owners,anchors)")
        replace('original_devices=484,','native_mim_intrinsic=mim_proof,original_devices=484,')
        target=B/'audit-rc48.py';assert not target.exists();target.write_text(text)
        mutations=B/'mutations48.py';assert not mutations.exists();mutations.write_bytes((OUT/'capture/source/wire/mutations48.py').read_bytes())
        r['adaptations']=dict(original_auditor_sha256=sha(source),new_auditor_sha256=sha(target),edits=edits,unchanged_wire_mutations_sha256=sha(mutations),intrinsic_helper_sha256=sha(Path(audit_cdr_collector_trunks_v21_mim_intrinsic.__file__)))
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-extraction-input-20261013.json').read_text());raw=ROOT/'hw/soc/out/pcie-magic-resis-terminals-v1-20261004/audit_pilot.py';raw.parent.mkdir(parents=True,exist_ok=True);fetch(spec['raw_parser']['url'],spec['raw_parser']['sha256'],raw)
        save();run([sys.executable,target,P,B/'anchors08.json',B/'mim-audit.json'],'strict-native-mim-wire-audit')
        r['audit']=json.loads((B/'mim-audit.json').read_text());save();assert r['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY'
        assert r['audit']['actual_exported_resistors']==17674 and r['audit']['actual_exported_capacitors']==12704 and r['audit']['native_mim_intrinsic']['devices']==11
        run([sys.executable,mutations],'thirteen-unchanged-raw-wire-controls');r['wire_controls']=json.loads((B/'native-mutations01.json').read_text());assert len(r['wire_controls']['cases'])==13
        module_spec=importlib.util.spec_from_file_location('mim_strict',target);module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
        anchors=json.loads((B/'anchors08.json').read_text());texts={n:(P/n).read_text()for n in ('wires.spice','baseline.spice','pump_wires.ext','pump_wires.res.ext')}
        source_rows=texts['wires.spice'].splitlines();idx=next(i for i,x in enumerate(source_rows)if x.startswith('X'));x=source_rows[idx].split();cases=[]
        def spice_case(name,change):
            lines=source_rows.copy();fields=x.copy();change(fields)
            if fields:lines[idx]=' '.join(fields)
            else:del lines[idx]
            cases.append((name,'wires.spice','\n'.join(lines)+'\n'))
        spice_case('missing_export_mim',lambda f:f.clear())
        spice_case('wrong_export_model',lambda f:f.__setitem__(3,'cap_rfcmim'))
        spice_case('wrong_export_width',lambda f:f.__setitem__(next(i for i,t in enumerate(f)if t.startswith('w=')),'w=999u'))
        spice_case('swapped_export_plates',lambda f:f.__setitem__(slice(1,3),list(reversed(f[1:3]))))
        for name,filename,transform in [
            ('missing_source_device','pump_wires.ext',lambda t:re.sub(r'^device .*\n','',t,count=1,flags=re.M)),
            ('wrong_source_dimension','pump_wires.ext',lambda t:re.sub(r'^(device .*? w=)\S+',r'\g<1>999999',t,count=1,flags=re.M)),
            ('missing_replacement_device','pump_wires.res.ext',lambda t:re.sub(r'^device .*\n','',t,count=1,flags=re.M)),
            ('shifted_replacement_location','pump_wires.res.ext',lambda t:re.sub(r'^(device csubckt cap_cmim )\d+',r'\g<1>1',t,count=1,flags=re.M)),
            ('wrong_parameter_declaration','pump_wires.ext',lambda t:t.replace('parameters cap_cmim w=w l=l','parameters cap_cmim w=l l=w',1))]:cases.append((name,filename,transform(texts[filename])))
        read_text=Path.read_text;r['intrinsic_controls']=[]
        for name,filename,changed in cases:
            assert changed!=texts[filename]
            def changed_read(path,*a,**kw):return changed if path==P/filename else read_text(path,*a,**kw)
            with patch.object(Path,'read_text',changed_read):
                try:module.audit(P,anchors)
                except ValueError as e:reason=str(e)
                else:raise AssertionError('Accepted '+name)
            assert 'MIM'in reason,(name,reason)
            r['intrinsic_controls'].append(dict(name=name,rejected=True,reason=reason,sha256=hashlib.sha256(changed.encode()).hexdigest(),diff=''.join(difflib.unified_diff(texts[filename].splitlines(True),changed.splitlines(True)))))
        assert len(r['intrinsic_controls'])==9
        assert all(sha(OUT/'capture'/n)==v for n,v in prior['outputs'].items())and sha(raw)==spec['raw_parser']['sha256']
        assert sha(target)==r['adaptations']['new_auditor_sha256']and sha(mutations)==r['adaptations']['unchanged_wire_mutations_sha256']and sha(Path(audit_cdr_collector_trunks_v21_mim_intrinsic.__file__))==r['adaptations']['intrinsic_helper_sha256']
        r['sources_unchanged']=True;r['status']='PASS_PD484_MIM_AWARE_RAW_RC_AND22_CONTROLS_REQUIRES_COMPOSITION_AND_LOADED_WAVES'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
