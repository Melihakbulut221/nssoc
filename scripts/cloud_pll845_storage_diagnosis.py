#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read complete failed PLL archive in cloud without activating or storing its native process."""
import hashlib,json,math,os,struct,tarfile
from pathlib import Path
import cloud_streamed_native_archive as archive
import read_pll845_full_native_transient as wave
import pll845_archived_header_observation as observed
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pll845-storage-diagnosis'
RUN=39551551389
GROUP='pll845-native-acquisition-initial'
SUMMARY='bd0f59b0f945d749452199de4a1f11277d179893ed143a7046712297c61af133'
PARTS='e90caa0175de307a74a6bc349e8f18ab2c6117fd37afa853c0c9f2e7ac9b5762'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);stage=ROOT/'pll845-diagnostic-parts';stage.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source_run=RUN,native_activation_allowed=False,full_capture_accepted=False,full_phy_accepted=False,whole_archive_verified=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        r['stream_controls']=archive.controls()
        r['actual_header_qualification']=observed.qualify(OUT/'header-qualification');save()
        stem=GROUP+'-'+str(RUN)+'-1';url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-'+str(RUN)+'-1-'+GROUP+'/'
        fetch(url+stem+'.summary.json',SUMMARY,OUT/'source-summary.json')
        fetch(url+stem+'.parts.json',PARTS,OUT/'source-parts.json')
        report=json.loads((OUT/'source-summary.json').read_text());manifest=json.loads((OUT/'source-parts.json').read_text())
        assert report['source_head']=='21ceb87f7b83008497eb4cc7e44fca5973e605b1'
        assert report['status']=='FAIL_OR_ERROR' and report['error']=="AssertionError('Insufficient native or backing reserve before resume')"
        assert not report['checkpoint_saved'] and not report['full_capture']
        r['source_error']=report['error'];r['source_checkpoint']=report['source_checkpoint'];r['member_census']=[]
        known={};seen=set();small=OUT/'metadata';small.mkdir()
        metadata={}
        def download(part,path):fetch(url+part['name'],part['sha256'],path)
        with archive.verified_remote_parts(manifest,stage,download)as packed:
            with tarfile.open(fileobj=packed,mode='r|gz')as tar:
                for m in tar:
                    p=Path(m.name);assert not p.is_absolute()and '..'not in p.parts and p.parts[0]==manifest['source_directory']
                    assert m.name not in seen and(m.isdir()or m.isfile());seen.add(m.name)
                    if not m.isfile():continue
                    rel=str(Path(*p.parts[1:]));f=tar.extractfile(m);digest=hashlib.sha256();count=0;prefix=bytearray();tail=b'';keep=bytearray()
                    israw=rel=='case/actual-acquisition.raw'
                    keep_small=(rel.startswith('storage-initialization')or rel in ('result.json','new-preparation.json','case/circuit.cir','prepared/terminal-instrumentation.json') or rel.startswith('history/')) and m.size<=2*1024**2
                    while data:=f.read(archive.CHUNK):
                        digest.update(data);count+=len(data)
                        if israw:
                            if len(prefix)<wave.MAX_HEADER:prefix.extend(data[:wave.MAX_HEADER-len(prefix)])
                            tail=(tail+data)[-65536:]
                        if keep_small:keep.extend(data)
                    assert count==m.size
                    known[rel]=digest.hexdigest();r['member_census'].append(dict(path=rel,bytes=count,sha256=digest.hexdigest()))
                    if rel in report['outputs']:assert digest.hexdigest()==report['outputs'][rel],rel
                    if keep_small:
                        target=small/p.relative_to(manifest['source_directory']);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(keep)
                        metadata[rel]=dict(path=str(target.relative_to(OUT)),sha256=sha(target),bytes=count)
                    if israw:
                        head=OUT/'native-header-prefix.bin';head.write_bytes(prefix)
                        names,h=observed.header(head.read_bytes());assert len(names)==5106
                        assert count==94756323259 and digest.hexdigest()=='17a116d880d748a3bf773f6d8268b16b7fa06c914a19dabbf8439819acb8e88a'
                        stride=8*len(names);rows,remainder=divmod(count-h['header_bytes'],stride);assert rows>0
                        absolute=h['header_bytes']+(rows-1)*stride
                        index=absolute-(count-len(tail));assert 0<=index<=len(tail)-8
                        last=struct.unpack('<d',tail[index:index+8])[0];assert math.isfinite(last)and last>=0
                        r['raw_position']=dict(bytes=count,sha256=digest.hexdigest(),header=h,complete_rows=rows,partial_row_bytes=remainder,last_native_time_s=last,all_terminal_values_audited=False)
                    r['observed_files']=len(known);save()
        assert all(known.get(p)==h for p,h in report['outputs'].items())
        assert known['result.json']==SUMMARY
        assert 'storage-initialization-state.json'in metadata
        init=json.loads((OUT/metadata['storage-initialization-state.json']['path']).read_text())
        r['storage_initialization']={k:v for k,v in init.items()if k not in ['immutable_workspace_files','commands']}
        r['metadata']=metadata
        r['largest_members']=sorted(r['member_census'],key=lambda x:x['bytes'],reverse=True)[:30]
        r['logical_archive_file_bytes']=sum(x['bytes']for x in r['member_census'])
        r['whole_archive_verified']=True
        r['status']='COMPLETE_FAILED_PLL_ARCHIVE_STORAGE_CENSUS_AND_NATIVE_POSITION_NOT_RESUME_OR_PHY_ACCEPTANCE'
        r['scope']='All ordered parts and original file digests verified. No native process activated; only bounded metadata/header retained on this cloud runner. Original failed and resumable source archives remain intact. Initialization capacity is not final post-restore free-space measurement.'
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:save()
if __name__=='__main__':main()
