#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replay actual native float accumulation; never waive the raw RC acceptance gate."""
import io,json,os,re,shlex,struct,tarfile,urllib.request,hashlib
from pathlib import Path
from collections import defaultdict
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-raw64-totalcap-diagnosis'
def f32(v):return struct.unpack('f',struct.pack('f',v))[0]
def replay(rows):
    native=defaultdict(float);exact=defaultdict(float)
    for row in rows:
        if row[0]=='node':
            n=row[1];v=float(row[3]);native[n]=f32(native[n]+v);exact[n]+=v
        elif row[0]=='cap':
            x,y=row[1:3];v=float(row[3])
            native[x]=f32(native[x]+v);native[y]=f32(native[y]+v)
            exact[x]+=v;exact[y]+=v
    return dict(native),dict(exact)
def assess(rows,markers):
    native,exact=replay(rows)
    assert set(native)==set(markers),'Native marker/node ownership mismatch'
    wrong=[dict(node=n,replayed=v,native=markers[n][0])for n,v in native.items()if v!=markers[n][0]]
    assert not wrong,('Actual native float accumulation was not reproduced',wrong[:8])
    return [dict(node=n,serialized_native_total=markers[n][0],replayed_binary32_total=native[n],double_sum_of_same_source_records=exact[n],error_af=native[n]-exact[n],error_ppm=(native[n]-exact[n])/exact[n]*1e6 if exact[n]else 0)for n in sorted(native)]
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],raw_rc_accepted=False,qualified_pex=False,full_parent_composed=False,serial_phy_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/'docs/evidence/tx-raw64-native-rc-witness-rejection-20261020.json').read_text())
        selected=['rc01/full_raw64_core_wires.ext','rc01/native.log','audit.json']
        prior,proof=reports.restore_report('tx-raw64-native-rc',pin['run'],pin['summary_sha256'],pin['parts_sha256'],OUT/'source',selected)
        assert prior['status']=='FAIL_OR_ERROR'and prior['source_head']=='b66dcdb3d72b5fcbc1055b2f05247ca2a6e791c3';result['failed_source']=proof
        a=json.loads((OUT/'source/audit.json').read_text())
        assert a==prior['audit']and a['status']=='FAIL_EXPORTED_TERMINAL_AND_CAPACITANCE_CONTRACT'
        assert len(a['wrong_native_branch_witnesses'])==2 and not a['disconnected_probes']
        assert a['native_export_r_edge_value_multiset_exact']and a['complete_collapsed_capacitance_conserved']and a['every_native_point_ground_capacitance_preserved']and a['every_native_mutual_attachment_and_value_preserved']
        text=(OUT/'source/rc01/full_raw64_core_wires.ext').read_text()
        rows=[shlex.split(s)for s in text.splitlines()if s.strip()]
        log=(OUT/'source/rc01/native.log').read_text()
        found=re.findall(r'^NSSOC_V2_INTRINSIC_DISTRIBUTION (\S+) total=(\S+) intrinsic=(\S+)$',log,re.M)
        assert len(found)==698 and len({n for n,t,i in found})==698
        markers={n:(float(t),float(i))for n,t,i in found}
        result['all_native_totals']=assess(rows,markers)
        wanted={x['node']:x for x in a['wrong_native_branch_witnesses']}
        result['rejected_rails']=[x for x in result['all_native_totals']if x['node']in wanted]
        for x in result['rejected_rails']:
            old=wanted[x['node']]
            assert abs(x['double_sum_of_same_source_records']-old['legacy_expected'])<1e-6
            assert x['replayed_binary32_total']==old['legacy_actual']
        result['controls']=[]
        for case in ('changed_coupling_value','missing_coupling_record','changed_ground_value','changed_serialized_marker'):
            changed=[x.copy()for x in rows];cm=markers.copy()
            i=next(i for i,x in enumerate(changed)if x[0]=='cap'and 'P_avss'in x[1:3]and float(x[3])>1000)
            if case=='changed_coupling_value':changed[i][3]=str(float(changed[i][3])*1.01)
            elif case=='missing_coupling_record':del changed[i]
            elif case=='changed_ground_value':
                j=next(j for j,x in enumerate(changed)if x[:2]==['node','P_avss']);changed[j][3]=str(float(changed[j][3])*1.01)
            else:cm['P_avss']=(cm['P_avss'][0]+1024,cm['P_avss'][1])
            try:assess(changed,cm)
            except AssertionError as e:result['controls'].append(dict(name=case,rejected=True,reason=str(e)[:2000]))
            else:raise AssertionError('Accepted source/marker corruption '+case)
        assert len(result['controls'])==4
        assert all(sha(OUT/'source'/n)==prior['outputs'][n]for n in selected)
        result.update(status='PASS_NATIVE_BINARY32_TOTAL_LOAD_DIAGNOSIS_NOT_RC_ACCEPTANCE',sources_unchanged=True,
            disposition='Native binary32 accumulation reproduced for all698 totals. Two power-rail errors are not physical missing-R/C evidence, but the original native witness gate still fails. Fix producer accumulation in an isolated rebuilt runtime and rerun unchanged complete native audit and13 controls before accepting RC. No threshold change or post-extraction marker rewrite.')
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
