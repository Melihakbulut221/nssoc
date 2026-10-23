#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read the current repaired candidate placement reports; not routed timing acceptance."""
import hashlib,json,os,re,subprocess,traceback
from pathlib import Path
from collections import Counter
import compare_cloud_routed_endpoints as reports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-mainchip-repair-deep-triage'
RUN=39674630712
HEAD='6fbd221520a35d6b5ef01cc1c67796175093ee3c'
SUMMARY='cff0a3533c622f4ecf9951f205e046ba8ad35ab0ca326b6e2f82371559f2cade'
PARTS='997ee6b2b8b5f9fd971a1901a68cf49465b80bf8f0914ae461f347e915b34123'
CORNERS=('nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C')
NAMES=('max','min')
def digest(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
      scope='Exact native placement-estimated paths of the repaired candidate now being routed. Not extracted routed timing, repair or full timing closure.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        live=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/'+str(RUN)]))
        assert live['head_sha']==HEAD and live['run_attempt']==1 and live['status']=='completed'and live['conclusion']=='success'
        assert live['path']=='.github/workflows/mainchip-postroute-repair-deep-cloud.yml'
        names=[f'optimizer-placement-{c}-{n}.rpt'for c in CORNERS for n in NAMES]+['native-repair.log','candidate.v']
        prior,proof=reports.restore_report('mainchip-postroute-repair-deep',RUN,SUMMARY,PARTS,OUT/'source',names)
        assert prior['source_head']==HEAD and prior['sources_unchanged']
        assert prior['status']=='PASS_NATIVE_RESIZER_CANDIDATE_REQUIRES_ROUTE_FRESH_RC_ALL_CORNER_STA'
        assert prior['candidate_netlist_sha256']=='3a200ea79143bc3b723905495085c317083deac7cc6b10ad3033b186293d7030'
        assert prior['candidate_odb_sha256']=='25b1e56fe0667adc84b7c2bd5397a755d6cfdf7375b3d5c1444e56bd9252e279'
        assert prior['source_sdc_sha256']=='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597'
        assert prior['actual_inversion_control_rejected'] and prior['proof']['status']=='PASS within scope'
        assert prior['fixed_clock']['original_physical_route_preserved']
        result.update(source=proof,candidate_netlist_sha256=prior['candidate_netlist_sha256'],
          source_sdc_sha256=prior['source_sdc_sha256'],optimizer_parasitics=prior['optimizer_parasitics'],
          accepted=False,final_timing_complete=False,full_phy_accepted=False,corners={})
        for c in CORNERS:
            base=OUT/'source'
            row={}
            for kind in ('max','min'):
                raw=(base/('optimizer-placement-'+c+'-'+kind+'.rpt')).read_text()
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
            result['corners'][c]=row
        assert digest(OUT/'source/candidate.v')==prior['candidate_netlist_sha256']
        from map_mainchip_candidate_timing import map_endpoints
        result['candidate_endpoint_mapping']=map_endpoints(OUT/'source/candidate.v',result['corners'])
        assert all(digest(OUT/'source'/n)==prior['outputs'][n]for n in names)
        result.update(status='COMPLETE_EXACT_CANDIDATE_PLACEMENT_PATH_DIAGNOSIS_NOT_ROUTED_TIMING',
          sources_unchanged=True,all_native_reports_retained=True)
    except BaseException as e:
        result.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):digest(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
        save()
if __name__=='__main__':main()
