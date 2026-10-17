#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Inspect complete native path reports in cloud without repeating physical repair."""
import hashlib,json,os,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-corrpre-timing-path-review'

def digest(p):
    with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,
        scope='Complete saved native postCTS reports; read-only diagnosis, not another repair or timing acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        receipt=json.loads((ROOT/'docs/evidence/corrpre-postcts-timing-trial-20261017.json').read_text())
        prior=receipt['report'];assert prior['source_head']=='1d0caf4db137c3e290ef4c52a3230afed9cb4ab3' and prior['sources_unchanged']
        stem='corrpre-postcts-timing-39011120664-1'
        url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-39011120664-1-corrpre-postcts-timing/'+stem+'.tar.gz.part0000'
        packed=OUT/'source.tar.gz';subprocess.run(['curl','--fail','--location','--retry','4',url,'-o',str(packed)],check=True)
        assert packed.stat().st_size==receipt['archive_bytes']and digest(packed)==receipt['archive_sha256']
        records={};full={}
        with tarfile.open(packed)as t:
            prefix='cloud-corrpre-postcts-timing/'
            assert hashlib.sha256(t.extractfile(prefix+'result.json').read()).hexdigest()==receipt['summary_sha256']
            for name,pin in prior['outputs'].items():
                with t.extractfile(prefix+name)as f:assert hashlib.file_digest(f,'sha256').hexdigest()==pin,name
            result['all_saved_outputs_verified']=len(prior['outputs'])
            for corner,meta in prior['after'].items():
                directory=meta['directory']
                for kind in ('max','min'):
                    name=directory+'/'+kind+'.rpt';text=t.extractfile(prefix+name).read().decode()
                    (OUT/(corner+'-'+kind+'.rpt')).write_text(text)
                    starts=list(re.finditer(r'(?m)^Startpoint:',text));paths=[]
                    assert starts,('No complete native paths',name)
                    for index,start in enumerate(starts):
                        stop=starts[index+1].start()if index+1<len(starts)else len(text);body=text[start.start():stop]
                        endpoints=re.findall(r'(?m)^Endpoint:\s*(.+)$',body);sources=re.findall(r'(?m)^Startpoint:\s*(.+)$',body)
                        slacks=re.findall(r'(?m)^\s*([-+0-9.eE]+)\s+slack\s+\((VIOLATED|MET)\)',body)
                        assert len(endpoints)==len(sources)==len(slacks)==1,('Incomplete native path',name,index)
                        paths.append(dict(startpoint=sources[0],endpoint=endpoints[0],slack_ns=float(slacks[0][0]),native_status=slacks[0][1],native_report=body))
                    records[corner+'-'+kind]=dict(count=len(paths),paths=paths)
                    result.setdefault('worst_paths',{})[corner+'-'+kind]=paths[:2]
            for name in ['native.log','run/1-openroad-resizertimingpostcts/openroad-resizertimingpostcts.log']:
                text=t.extractfile(prefix+name).read().decode(errors='replace')
                (OUT/Path(name).name).write_text(text)
                result.setdefault('repair_messages',{})[name]=[line for line in text.splitlines()if any(word in line.lower()for word in ('iteration','inserted','resized','repair','warning','wns','tns'))][-100:]
        (OUT/'all-native-paths.json').write_text(json.dumps(records,indent=2)+'\n')
        packed.unlink()
        result.update(status='COMPLETE_SOURCE_BOUND_NATIVE_POSTCTS_PATH_REVIEW_NOT_TIMING_CLOSURE',source_run=39011120664,
            before=prior['before'],after=prior['after'],repaired_odb_sha256=prior['repaired_odb_sha256'],report_only=True,
            source_summary_sha256=receipt['summary_sha256'],source_archive_sha256=receipt['archive_sha256'])
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):digest(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};save()
if __name__=='__main__':main()
