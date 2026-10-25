#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Original all-column reader on a verified ordinary complete 1us native file."""
import hashlib,json,os,shutil,traceback
from pathlib import Path
import cloud_pll845_sparse_io as storage
import cloud_pll845_sparse_disk as disk
import cloud_native_sparse_prefix_store as sparse
import cloud_streamed_native_archive as archive
import read_pll845_all_native_transient as wave
import run_cloud_pll865_snapshot as pll
from publish_pll845_sparse_checkpoint import ready
from route_cloud_newer_postcts import fetch
GIB=1024**3
def capacity(free,raw_bytes,part_limit):
    assert all(type(x)is int and x>=0 for x in (free,raw_bytes,part_limit))
    required=raw_bytes+part_limit+4*GIB
    assert raw_bytes>0 and part_limit>0 and free>=required,'Insufficient ordinary full-capture reader capacity'
    return dict(free_bytes=free,raw_bytes=raw_bytes,part_staging_bytes=part_limit,
        reserve_bytes=4*GIB,required_bytes=required,source_download_started=False)
def controls():
    assert capacity(140*GIB,130*GIB,GIB)['reserve_bytes']==4*GIB
    for args in [(134*GIB,130*GIB,GIB),(140*GIB,0,GIB),(140*GIB,130*GIB,0)]:
        try:capacity(*args)
        except AssertionError:pass
        else:raise AssertionError('Invalid complete-reader capacity accepted')
    return dict(ordinary_full_raw_plus_part_and4GiB_reserve=True,negative_cases=3)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    root=Path.cwd();_,methods=disk.source_contract(root)
    out=root/'cloud-pll845-sparse-completed-reader';out.mkdir(exist_ok=False)
    inputs=root/'cloud-pll845-sparse-completed-input';inputs.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],full_capture=False,
        acquisition_accepted=False,full_device_safety_accepted=False,full_phy_accepted=False,
        qualified_pex=False,native_activation_performed=False)
    def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        spec=json.loads(os.environ['SOURCE_CHECKPOINT']);url,stem=storage.source_url(spec)
        summary=inputs/'source-summary.json';parts=inputs/'source-parts.json'
        fetch(url+stem+'.summary.json',spec['summary_sha256'],summary)
        fetch(url+stem+'.parts.json',spec['parts_sha256'],parts)
        prior=json.loads(summary.read_text());manifest=json.loads(parts.read_text())
        assert ready(prior,spec['stage'],str(spec['run']),str(spec['attempt']),'success')
        assert prior['method_hashes']==methods and prior['controller_sha256']==methods[disk.CONTROLLER]
        assert prior['native_startup_readback']['actual_native_devices']==102
        assert prior['native_startup_readback']['all_off_readbacks_one']
        source=prior['logical_capture'];sparse.source_contract(source)
        assert source==prior['logical_storage_proof']and source['sha256']==prior['outputs'][storage.RAW]
        assert manifest['stem']==stem and manifest['source_directory']=='cloud-pll845-native-acquisition'
        published=manifest['verification']['logical_members'][storage.RAW]
        assert {k:published[k]for k in storage.FIELDS}==source and published['original_payload_preserved']
        r.update(source_checkpoint=spec,source_report_status=prior['status'],
            native_complete=True,original_inputs_unchanged=prior['protected_inputs_unchanged'],
            method_hashes=methods,logical_capture=source,controls=controls())
        r['capacity_before_download']=capacity(shutil.disk_usage(inputs).free,source['bytes'],manifest['part_limit_bytes']);save()
        def download(row,path):fetch(url+row['name'],row['sha256'],path)
        raw=inputs/'complete-original.raw'
        chunks=storage.source_member_chunks(manifest,inputs/'part-staging',download,storage.RAW,source['bytes'])
        with raw.open('xb')as f:
            for offset,data in sparse.checked_source(chunks,source):
                assert f.tell()==offset;f.write(data)
            f.flush();os.fsync(f.fileno())
        assert raw.stat().st_size==source['bytes']and archive.sha(raw)==source['sha256']
        contract=disk.load_contract(root,prior['preparation']['vectors'])
        r['verified_ordinary_source']=True;save()
        names,values,capture=wave.capture(raw,contract)
        assert capture['raw_sha256']==source['sha256']
        r.update(full_capture=True,capture=capture)
        columns={n:values[:,i]for i,n in enumerate(names)}
        result=pll.acquisition_analyzer()(columns)
        r['independent_acquisition']=result
        r['cycle_diagnosis']=pll.acquisition_cycle_diagnosis(columns,result)
        r['original_acquisition_passed']=bool(result['passed'])
        r['acquisition_accepted']=bool(result['passed'])
        r['status']='PASS_ORIGINAL_FULL845_CAPTURE_AND_ACQUISITION_REQUIRES_DEVICE_PVT_PHY_SIGNOFF'if result['passed']else'REJECTED_ORIGINAL_FULL845_ACQUISITION_GATES'
        r['original_release_retains_all_native_bytes']=True
        save()
        assert result['passed'],'Original full-duration acquisition gates failed'
    except BaseException as error:
        if r['status']=='RUNNING':r['status']='FAIL_COMPLETE_NATIVE_READER'
        r.update(error=repr(error),traceback=traceback.format_exc());save();raise
    finally:
        save()
        print(json.dumps({k:r[k]for k in ('status','full_capture','acquisition_accepted','full_phy_accepted')}),flush=True)
if __name__=='__main__':
    import sys
    if '--controls'in sys.argv:print(json.dumps(controls()))
    else:main()
