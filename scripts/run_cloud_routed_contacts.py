#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only full saved mainchip signal contact baseline, no reroute."""
import json,os,subprocess,sys
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha
from cloud_verified_parts import extract_verified
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-routed-contacts'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_head=os.environ['GITHUB_SHA'],source_run=38810969514,full_serial_phy_complete=False,final_timing_complete=False)
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        stem='routed-geometry-38810969514-1';base='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38810969514-1-routed-geometry/'
        fetch(base+stem+'.summary.json','3236d5446abdff3b8f8bab9731d38d1f850061d59a5058a37d2f940423b21936',OUT/'source-summary.json')
        source=json.loads((OUT/'source-summary.json').read_text());assert source['source_unchanged'] and source['geometry_export']['shapes']==3323078 and source['geometry_export']['exported_nets']==113556
        fetch(base+stem+'.parts.json','21e3634c3ec55d871414d73918307477270e527048a8b8877c4820523f977f43',OUT/'source-parts.json')
        parts=json.loads((OUT/'source-parts.json').read_text());packed=OUT/'parts';packed.mkdir()
        for part in parts['parts']:fetch(base+part['name'],part['sha256'],packed/part['name'])
        selected={n:source['outputs'][n]for n in ('signal-geometry.jsonl.gz','export.json')};result['restoration']=extract_verified(parts,packed,OUT/'geometry',selected)
        for p in packed.iterdir():p.unlink()
        packed.rmdir();save()
        with (OUT/'contacts.log').open('w') as log:
            p=subprocess.Popen([sys.executable,str(ROOT/'scripts/check_cloud_signal_contacts.py'),'--directory',str(OUT/'geometry')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
            for line in p.stdout:log.write(line);log.flush();print(line,end='',flush=True)
            code=p.wait()
        assert code==0,'Contact checker did not finish'
        audit=json.loads((OUT/'geometry/signal-contacts.json').read_text());assert audit['status']=='COMPLETE_ALL_EXPORTED_SIGNAL_RECTANGLE_CONTACT_SCREEN_NOT_SIGNOFF'
        assert audit['shape_count']==3323078 and audit['net_count']==113556
        assert all(sha(OUT/'geometry'/n)==digest for n,digest in selected.items())
        result.update(status='COMPLETE_ORIGINAL_ROUTED_SIGNAL_CONTACT_BASELINE_NOT_SIGNOFF',audit=audit,source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':main()
