#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Locate the exact terminal-free metal rejected by the unchanged native graph gate."""
import hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-cdr-v27-unowned-metal-diagnosis'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',accepted=False,qualified_pex=False,full_phy_accepted=False,source_head=os.environ['GITHUB_SHA'])
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    try:
        raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/661345934','-H','Accept: application/octet-stream'])
        assert hashlib.sha256(raw).hexdigest()=='8c9eedbb132b702892e240c3580ec83e9e7be4939c5f932a52e913d1035c3459'
        prior=json.loads(raw)
        old,proof=reports.restore_report('cdr-bias-access-v27-wire-inputs',39544018550,
            '8c9eedbb132b702892e240c3580ec83e9e7be4939c5f932a52e913d1035c3459',
            'd1599d94fbc753a4dc8b711ecc8325bb712fa44186700ec32d6162ecb76638a9',OUT/'source',list(prior['outputs']))
        assert old==prior
        assert old['status']=='FAIL_OR_ERROR'and old['error']=="AssertionError(('probe01.py', 1))"
        assert old['source_head']=='afceec5c1069a0e1b7ced2f1d8525d482c74f076'
        result['failed_source']=proof
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        source=OUT/'source';original=source/'wire/probe01.py'
        assert sha(original)==old['outputs']['wire/probe01.py']
        protected={p:sha(p)for p in source.rglob('*')if p.is_file()}
        native_env={k:v for k,v in os.environ.items()if k not in ('GH_TOKEN','GITHUB_TOKEN')}
        with(OUT/'original-gate.log').open('w')as log:
            code=subprocess.call([str(app),'python',str(original)],cwd=ROOT,env=native_env,stdout=log,stderr=subprocess.STDOUT)
        native_log=(OUT/'original-gate.log').read_text()
        assert code==1 and 'if not ts:assert not area and not ps and n.cluster_id not in owners'in native_log
        result['strict_original_gate_reproduced']=True;save()
        text=original.read_text()
        before="OUT=B/'native05';OUT.mkdir()";assert text.count(before)==1
        text=text.replace(before,"OUT=B/'native05-diagnosis';OUT.mkdir()")
        before="coverage=[];terminals=defaultdict(list);ports=defaultdict(list)"
        assert text.count(before)==1;text=text.replace(before,before+";orphan_rows=[]")
        before=" if not ts:assert not area and not ps and n.cluster_id not in owners"
        after=""" if not ts and (area or ps or n.cluster_id in owners):
  drawing={}
  for metal in active:
   piece=l.shapes_of_net(n,l.layer_by_index(mapping[metal]),True)
   if not piece.is_empty():
    drawing[str(metal)]=dict(area_dbu2=piece.area(),bbox_dbu=[piece.bbox().left,piece.bbox().bottom,piece.bbox().right,piece.bbox().top],polygons=[poly.to_s()for poly in piece.each()])
  orphan_rows.append(dict(native_cluster=n.cluster_id,name=n.name,metal_area_dbu2=area,wire_components=owners.get(n.cluster_id,[]),public_ports=ps,layers=drawing))"""
        assert text.count(before)==1;text=text.replace(before,after)
        marker="wire.write(str(OUT/'wires.gds'));e.write(str(OUT/'wires.l2n'))"
        assert text.count(marker)==1
        stop="""assert orphan_rows,'Original terminal-free geometry did not reproduce'
diagnosis=dict(status='LOCATED_NATIVE_TERMINAL_FREE_METAL_NOT_ACCEPTANCE',dbu_um=g.dbu,orphan_rows=orphan_rows,native_classes=dict(classes),wire_components=len(rows),native_nets=len(coverage),all_original_graph_checks_before_ownership_reproduced=True,geometry_edited=False,qualified_pex=False,accepted=False)
(P/'unowned-metal.json').write_text(json.dumps(diagnosis,indent=2)+'\\n')
print(json.dumps(diagnosis),flush=True)
raise SystemExit(0)
"""
        text=text.replace(marker,stop+marker)
        diagnostic=source/'wire/diagnostic-probe.py';diagnostic.write_text(text)
        result['diagnostic_source_delta']=dict(original_sha256=sha(original),diagnostic_sha256=sha(diagnostic),native_geometry_unchanged=True,original_gate_unchanged=True)
        with(OUT/'diagnostic.log').open('w')as log:
            code=subprocess.call([str(app),'python',str(diagnostic)],cwd=ROOT,env=native_env,stdout=log,stderr=subprocess.STDOUT)
        assert code==0,('Native geometric diagnosis failed',code)
        result['diagnosis']=json.loads((source/'unowned-metal.json').read_text())
        assert all(sha(p)==h for p,h in protected.items())
        result.update(status='COMPLETE_UNOWNED_METAL_DIAGNOSIS_REQUIRES_PHYSICAL_FIX',sources_unchanged=True)
    except BaseException as e:
        result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
