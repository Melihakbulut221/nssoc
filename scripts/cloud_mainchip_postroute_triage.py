#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read the completed route's exact native reports; no CAD rerun or acceptance."""
import hashlib,json,os,re,subprocess,traceback
from pathlib import Path
from collections import Counter
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-mainchip-postroute-triage'
RUN=39654204345
HEAD='59297d93106c4401d94213ee94d048d7c839d7a3'
SUMMARY='39ddb8633e57072ce21d12fbe2c30c8a78a8d0f9b5c544724edc2ecdfc77635a'
PARTS='e10f42775e7ead514d4ca2701f6fa6e5266090329913a7d61522e12e05f1c237'
CORNERS=('nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C')
NAMES=('max.rpt','min.rpt','checks.rpt','violator_list.rpt','clock.rpt','ws.max.rpt','ws.min.rpt')
def digest(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
      scope='Exact immutable native report diagnosis, not repair or full timing closure.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        live=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/'+str(RUN)]))
        assert live['head_sha']==HEAD and live['run_attempt']==1 and live['status']=='completed'and live['conclusion']=='success'
        assert live['path']=='.github/workflows/mainchip-postroute-review-cloud.yml'
        names=[f'run/4-nssoc-onehotroutedsta/{c}/{n}'for c in CORNERS for n in NAMES]
        prior,proof=reports.restore_report('mainchip-postroute-review',RUN,SUMMARY,PARTS,OUT/'source',names)
        assert prior['source_head']==HEAD and prior['sources_unchanged']
        assert prior['status']=='COMPLETE_NATIVE_POSTROUTE_WITH_UNCLOSED_GATES'
        result.update(source=proof,measurements=prior['measurements'],
          antenna={k:prior['antenna'][k]for k in ('final_violating_nets','final_violating_pins','passed')},
          corners={})
        for c in CORNERS:
            base=OUT/'source/run/4-nssoc-onehotroutedsta'/c
            row={}
            for kind in ('max','min'):
                raw=(base/(kind+'.rpt')).read_text()
                blocks=['Startpoint:'+s for s in raw.split('Startpoint:')[1:]]
                assert blocks,('No native paths in report',c,kind)
                paths=[]
                for b in blocks:
                    fields={}
                    for key in ('Startpoint','Endpoint','Path Group','Path Type'):
                        m=re.search(r'^'+key+r':\s*(.+)$',b,re.M)
                        assert m,(c,kind,key,b[:400])
                        fields[key]=m.group(1).strip()
                    slacks=re.findall(r'^\s*([+-]?\d+(?:\.\d+)?)\s+slack\s+\(([^)]+)\)',b,re.M)
                    assert len(slacks)==1,(c,kind,slacks)
                    fields['reported_slack']=float(slacks[0][0])
                    fields['native_slack_label']=slacks[0][1]
                    paths.append(fields)
                row[kind]=dict(reported_paths=len(paths),paths=paths,
                    path_groups=dict(Counter(x['Path Group']for x in paths)),
                    first_three_native_paths=blocks[:3])
            row['native_checks_excerpt']=(base/'checks.rpt').read_text()[:18000]
            row['native_violator_excerpt']=(base/'violator_list.rpt').read_text()[:6000]
            row['native_clock_report']=(base/'clock.rpt').read_text()
            result['corners'][c]=row
        assert all(digest(OUT/'source'/n)==prior['outputs'][n]for n in names)
        result.update(status='COMPLETE_EXACT_POSTROUTE_NATIVE_PATH_DIAGNOSIS_NOT_REPAIR',
          sources_unchanged=True,all_native_reports_retained=True)
    except BaseException as e:
        result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):digest(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
