#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent follow-up of the saved complete mainchip route; no route ECO."""
import hashlib,json,os,re,subprocess,sys,tarfile
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-routed-geometry'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38788529905-1-failed-guide-drt/'
STEM='failed-guide-drt-38788529905-1'
SUMMARY_SHA='e7ba93109d4aa057dd421fff97d1deb3275743ed8beecb3980f9e7fe36c632b2'
ARCHIVE_SHA='ce430c94dd6da745f2a15420eb5f8031842e9ddd78b6ad70aa0bb56634c0b964'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_run=38788529905,source_head=os.environ['GITHUB_SHA'],final_timing_complete=False,full_serial_phy_complete=False,
        scope='Read-only saved113791-instance mainchip routing geometry and native antenna diagnosis. Original global132overflow failure remains. No LVS, inter-net/NDR spacing, qualifiedRC or final timing acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(args,label):
        with (OUT/(label+'.log')).open('w') as log:
            p=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,NSSOC_ROUTE_AUDIT_OUT=str(OUT)),timeout=7200)
        text=(OUT/(label+'.log')).read_text(errors='replace');print(label,p.returncode,text[-3000:],flush=True)
        assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,p.returncode)
        return text
    save()
    try:
        source=OUT/'source';source.mkdir();fetch(BASE+STEM+'.summary.json',SUMMARY_SHA,source/'result.json');old=json.loads((source/'result.json').read_text())
        assert old['native_drt_drvs']==0 and old['audit_after']['counts']['wired_net_count']==113556
        packed=OUT/'source.tar.gz';fetch(BASE+STEM+'.tar.gz',ARCHIVE_SHA,packed);assert packed.stat().st_size==104854492
        names=('routed.odb','routed.def','detailed-route.log','drc.rpt','audit-after.json')
        with tarfile.open(packed) as archive:
            for name in names:
                data=archive.extractfile('cloud-failed-guide-drt/'+name).read();assert hashlib.sha256(data).hexdigest()==old['outputs'][name];(source/name).write_bytes(data)
        packed.unlink();result['source_summary_sha256']=SUMMARY_SHA;result['source_archive_sha256']=ARCHIVE_SHA
        result['routed_odb_sha256']=sha(source/'routed.odb');assert result['routed_odb_sha256']=='4ecf6f150c7288c43b99fb944bec72e5ad45f693234181ff47c1df7566957493'
        tcl=OUT/'antenna.tcl';tcl.write_text(f'read_db {{{source/"routed.odb"}}}\nset_thread_count 2\ncheck_placement -verbose\nset n [check_antennas -verbose -report_file {{{OUT/"antenna.rpt"}}}]\nputs "NSSOC_ANTENNA_RETURN $n"\n')
        text=run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(tcl)],'antenna')
        result['antenna_native_return']=re.findall(r'^NSSOC_ANTENNA_RETURN (.*)$',text,re.M);assert len(result['antenna_native_return'])==1;save()
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/export_cloud_routed_shapes.py')],'export')
        result['geometry_export']=json.loads((OUT/'export.json').read_text());save()
        run([sys.executable,str(ROOT/'scripts/check_cloud_routed_shapes.py'),'--directory',str(OUT)],'continuity')
        result['signal_continuity']=json.loads((OUT/'continuity.json').read_text())
        assert sha(source/'routed.odb')==result['routed_odb_sha256'];result['source_unchanged']=True
        result['status']='COMPLETE_NATIVE_ANTENNA_AND_SIGNAL_GEOMETRY_SCREEN_NOT_SIGNOFF'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':main()
