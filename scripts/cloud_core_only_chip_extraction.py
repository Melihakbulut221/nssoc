#!/usr/bin/env python3
"""Extract actual parent-level routes; nominal RC only, not full-chip signoff."""
import os,json,hashlib,subprocess,sys,urllib.request
from pathlib import Path
from cloud_core_only_postgrt import archive,completed,sha,ROOT
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-chip-extraction'
RULE_SHA='ffda02d57a6ecb39b02268be9511d89ef072911f17bd2dcd095f3f3cbeb5a905'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,qualified_rc_minmax=False,final_timing_complete=False,core_internal_parasitics_included=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    try:
        run=completed(44294471048,'c48b3ebddd01531a8b39acc170a1905f89db0479')
        z,meta=archive(run,'core-only-chip-physical-connectivity-native-44294471048')
        assert meta['id']==14423440493 and meta['digest']=='sha256:79ef51448c6ffbd4c1df8381de336666f4d44dab897ee1cb343d4227f82e752c'
        source=json.loads(z.read('result.json'));assert source['source_head']==run['head_sha']and source['sources_unchanged']
        for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h
        a=source['audit'];assert a==json.loads(z.read('physical-route-audit.json'))
        assert len(a['native_decoder_qualification'])==11 and all(x['passed']for x in a['native_decoder_qualification'].values())
        assert not a['signal_nets_with_disconnected_geometry']and not a['terminals_without_geometry']and a['inter_net_contact_pairs']==0
        assert len(a['unwired_multi_terminal_nets'])==76 and all(x['components']==1 for x in a['unwired_multi_terminal_nets'])
        odb=OUT/'chip-detailedroute.odb';odb.write_bytes(z.read('chip-detailedroute.odb'))
        assert sha(odb)=='afc4a1518e1c9d5e20e667379db5a979385fc4d2b30382872e003c7205857cf1'
        r['source_artifact']=meta;r['visible_geometry_audit']=a
        url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/librelane/IHP_rcx_patterns.rules'
        with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
        assert hashlib.sha256(data).hexdigest()==RULE_SHA
        rule=OUT/'IHP_rcx_patterns.rules';rule.write_bytes(data);r['rule_source']=url
        auditor=ROOT/'hw/soc/flow/audit_estimated_spef.py'
        protected={str(p):sha(p)for p in [Path(__file__),odb,rule,auditor]};r['protected_inputs']=protected
        app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
        def path(n):return '{'+str(OUT/n)+'}'
        tcl='set_thread_count 4\nread_db '+path('chip-detailedroute.odb')+'\ndefine_process_corner -ext_model_index 0 nominal\n'
        tcl+='extract_parasitics -ext_model_file '+path('IHP_rcx_patterns.rules')+' -lef_res\n'
        tcl+='write_spef '+path('chip-shell.nom.spef')+'\nputs NSSOC_PARENT_NATIVE_RCX_COMPLETE\n'
        script=OUT/'extract.tcl';script.write_text(tcl);protected[str(script)]=sha(script)
        r['status']='EXTRACTING_PARENT_ROUTE';save()
        with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(script)],stdout=log,stderr=subprocess.STDOUT,check=True)
        assert 'NSSOC_PARENT_NATIVE_RCX_COMPLETE'in(OUT/'native.log').read_text()
        sys.path.insert(0,str(auditor.parent));from audit_estimated_spef import audit
        check=audit(OUT/'chip-shell.nom.spef',allow_coupling=True)
        (OUT/'spef-integrity.json').write_text(json.dumps(check,indent=2)+'\n');r['spef_integrity']=check
        assert check['status'].startswith('PASS'),'SPEF capacitance conservation failed'
        assert all(sha(p)==h for p,h in protected.items())
        r.update(status='PARENT_ROUTE_NOMINAL_RC_EXTRACTED_REQUIRES_COVERAGE_CORE_REBIND_AND_SIGNOFF',sources_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
    finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
