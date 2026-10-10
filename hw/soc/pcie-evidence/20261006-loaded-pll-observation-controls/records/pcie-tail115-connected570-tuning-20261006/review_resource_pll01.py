"""Independent saved-byte/resource source review; never imports the producer."""
from pathlib import Path
import ast, gzip, hashlib, json, os, resource

R=Path.cwd(); B=Path(__file__).resolve().parent
def pin(p):
    p=Path(p)
    with p.open('rb') as f:
        return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def read(p): return json.loads(Path(p).read_text())
def part(text,name):
    n=next(n for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
    return ast.get_source_segment(text,n)+'\n'
def identity(pid):
    try: a=Path('/proc',str(pid),'stat').read_text().rsplit(') ',1)[1].split()
    except FileNotFoundError:return None
    return dict(pid=pid,start_ticks=a[19],state=a[0],process_group=int(a[2]))
def main():
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    fpath=B/'source-freeze01.json'; f=read(fpath)
    assert pin(fpath)==dict(bytes=406636,sha256='ccc53ba2c1a247d5d0b7d8a1f72d27d6fa74d054a6a2ec9c8e41c3cf9654413c')
    assert len(f['pins'])==1670
    for path,value in f['pins'].items(): assert pin(path)==value,path
    print('All1670 frozen files independently rehashed',flush=True)
    current=(B/'characterize_clamped570_01.py').read_text(); bridge=read(B/'driver-source-bridge01.json')
    parent=Path(bridge['parent']); assert pin(parent)==bridge['parent_pin']
    ptext=parent.read_text()
    for row in bridge['functions']:
        assert part(ptext,row['name'])==row['before']
        assert part(current,row['name'])==row['after']
    assert part(current,'run_native')==part(ptext,'run_native')
    capture=(B/'capture_custom01.py').read_text()
    assert capture in current and current.startswith((B/'driver_custom01.py').read_text())
    contract=read(B/'resource-contract01.json')
    n=120000*1134*8+4*1024**2+64
    assert contract['raw_payload_cap']==120000*1134*8==1088640000
    assert contract['raw_total_limit']==n==1092834368
    # The declared gzip allowance exceeds the zlib default-deflate bound plus framing.
    bound=n+(n>>12)+(n>>14)+(n>>25)+31
    assert contract['conservative_gzip_bound']>=bound
    assert contract['point_cap']==1280*1024**2
    assert contract['remaining_per_point_for_all_spice_op_logs_metadata']==contract['point_cap']-contract['conservative_gzip_bound']-2*1024**2
    assert contract['three_point_caps']==3*contract['point_cap']<contract['aggregate_cap']==4*1024**3
    assert contract['observations_retained_bound']['float64_bytes']==120000*18*8
    expected={'finite':11,'storage':22,'lifecycle':7}; cases={}
    for key,count in expected.items():
        record=f['actual_controls'][key]; assert pin(record['path'])==record['pin']
        result=read(record['path']); assert result['cases']==record['cases']==count
        assert result['status']==record['status'] and len(result['outcomes'])==count
        assert all(x['passed'] for x in result['outcomes'])
        assert len({x['case'] for x in result['outcomes']})==count
        cases[key]=[x['case'] for x in result['outcomes']]
    fixture=B/'finite-controls01/positive.raw'; raw=fixture.read_bytes()
    cut=raw.index(b'Binary:\n')+len(b'Binary:\n'); header=raw[:cut]
    assert len(raw[cut:])==4*1134*8+1 and raw[-1:]==b'4'
    ldir=B/'lifecycle-controls03'; lrec=read(ldir/'result.json'); owners=[]
    for label in ['clean','term','interrupt']:
        d=ldir/'native'/label; own=read(d/'owned-processes.json'); exe=read(d/'execution.json')
        assert gzip.decompress((d/'wave.raw.gz').read_bytes())==raw
        assert len(own['processes'])==1; p=own['processes'][0]
        assert p['status']==('REAPED_NO_LIVE_MEMBERS' if label=='clean' else 'FAILURE_REAPED')
        assert p['returncode']==(0 if label=='clean' else -15)
        now=identity(p['identity']['pid']); assert now is None or now['start_ticks']!=p['identity']['start_ticks']
        assert exe['actual_affinity']==[10] and exe['address_space_limit_bytes']==2*1024**3 and exe['elapsed_watchdog_seconds'] is None
        if label!='clean':
            assert own['cleanup']['recording_errors']==own['cleanup']['observation_errors']==[]
            assert all(x['immediate_after_kill']==[] for x in own['cleanup']['groups'])
        owners.append(dict(label=label,owner=pin(d/'owned-processes.json'),execution=pin(d/'execution.json'),gzip=pin(d/'wave.raw.gz'),identity=p['identity'],returncode=p['returncode']))
    for signum in ['SIGTERM','SIGINT']:
        own=read(ldir/(signum+'-completed-owner.json'))
        assert own['processes'][0]['status']=='REAPED_NO_LIVE_MEMBERS' and own['processes'][0]['returncode']==0
    storage=B/'storage-controls03/native'; prefixes=[]
    for label in ['short_writes','bad_trailer','shared_floor_after_received_block','bad_header','empty_header']:
        d=storage/label; saved=gzip.decompress((d/'wave.raw.gz').read_bytes())
        if label=='short_writes':assert saved==raw
        elif label=='bad_trailer':assert saved==raw[:-1]+b'5'
        elif label=='shared_floor_after_received_block':assert raw.startswith(saved)
        elif label=='bad_header':assert saved==header.replace(b'No. Variables: 1134',b'No. Variables: 1135')
        else:assert saved==b''
        if (d/'capture-failure.json').exists():
            failure=read(d/'capture-failure.json')
            assert len(saved)==failure['received_raw_bytes'] and hashlib.sha256(saved).hexdigest()==failure['received_raw_sha256']
            assert failure['resumable_solver_checkpoint'] is False
        prefixes.append(dict(label=label,bytes=len(saved),sha256=hashlib.sha256(saved).hexdigest(),gzip=pin(d/'wave.raw.gz')))
    # Static, exact witness: inherited parser permits nonzero counts, but this
    # real subsequent failure is beyond the failed-header preservation boundary.
    parser=(R/'scripts/probe_pcie_clock_stream_capture_v1.py').read_text()
    assert 'points >= 0' in part(parser,'parse_header')
    assert capture.index(' del seen') < capture.index(" require(meta['declared_points']==0") < capture.index(" with(out/'wave.raw.gz').open('xb',buffering=0)as dst:",capture.index(' del seen'))
    findings=[dict(id='HEADER_POST_PARSE_RETENTION_GAP',severity='prelaunch',scope='capture_custom01.py and generated capture body',evidence='A valid header with No. Points: 4 passes inherited parse_header, then NativeFIFO format raises after seen is deleted and before gzip/failure receipt creation.',required='Preserve01; put all header/init checks under retained-prefix failure handling; actual rejected nonzero-count fixture must retain exact consumed bytes and original diagnostic.')]
    receipt=dict(status='FINDING_SOURCE_AND_SAVED_570_RESOURCE_REVIEW',freeze=pin(fpath),reviewer='PLL independent, stdlib only',findings=findings,files_rehashed=len(f['pins']),whole_inherited_run_native_exact=True,full_four_function_bridge_verified=True,current_control_cases=cases,actual_owners=owners,actual_failed_and_complete_prefixes=prefixes,resource_arithmetic=contract,selected_runtime=pin(B/'runtime01.json'),scope=['No producer imports, reviewed controls, native EDA/SPICE or network executed.','Seven actual owner controls use finite FIFO stand-ins, not ngspice.','Sampled cap/floor guards and bounded reserved failed-only finalization; no atomic disk reservation or live power-loss durability.','2GiB process AS limits and bounded observation arrays are enforced; no real570 peak-memory result exists before native.','Physics/deck/Meter acceptance remains separate root review; this finding blocks the combined gate.'],method=pin(__file__))
    out=B/'resource-peer-pll01-findings.json'; assert not out.exists();out.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(out),pin=pin(out),findings=len(findings))))
if __name__=='__main__':main()
