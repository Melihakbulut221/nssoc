"""Read-only additive review. Imports only this reviewer's stdlib helpers."""
from pathlib import Path
import ast, gzip, hashlib, json, resource
from review_resource_pll01 import pin, read, part, identity
B=Path(__file__).resolve().parent
def dump(n):return ast.dump(n,include_attributes=False)
def main():
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
    fp=B/'source-freeze02.json'; f=read(fp); old=read(B/'source-freeze01.json')
    assert pin(fp)==dict(bytes=423199,sha256='725638ec401f55f728fe1e3d3c806d541d9ac381bf6e3854434e01ec23791dad')
    assert len(f['pins'])==1736 and all(f['pins'][p]==v for p,v in old['pins'].items())
    for p,v in f['pins'].items():assert pin(p)==v,p
    correction=read(B/'header-retention-correction02.json'); assert len(correction['changes'])==8
    for row in correction['changes']:
        for label in ['before','after']:
            rec=row[label]; p=Path(rec['path'])
            assert pin(p)=={k:rec[k]for k in ['bytes','sha256']} and p.read_text()==row[label+'_body']
    ca=(B/'capture_custom01.py').read_text(); cb=(B/'capture_custom02.py').read_text()
    a=ast.parse(ca).body[0];b=ast.parse(cb).body[0]
    # Compare exact flattened success statements and identical exception body;
    # the only semantic difference is that the header/init gates enter the try.
    ta=next(x for x in a.body if isinstance(x,ast.Try));tb=next(x for x in b.body if isinstance(x,ast.Try))
    assert [dump(x)for x in ta.handlers]==[dump(x)for x in tb.handlers]
    assert len(ta.body)==1 and len(tb.body)==6
    def flattened(fn):
        out=[]
        for x in fn.body:
            if x is next(n for n in fn.body if isinstance(n,ast.Try)):out+=x.body
            elif isinstance(x,ast.Delete):continue
            else:out.append(x)
        return [dump(x)for x in out]
    assert flattened(a)==flattened(b)
    assert isinstance(tb.handlers[0].body[-1],ast.Raise) and tb.handlers[0].body[-1].exc is None
    before=(B/'characterize_clamped570_01.py').read_text();after=(B/'characterize_clamped570_02.py').read_text()
    assert before.count(ca)==1 and before.replace("NATIVE_ROOT=B/'native01'","NATIVE_ROOT=B/'native02'").replace(ca,cb)==after
    bridge=read(B/'driver-source-bridge02.json');pt=Path(bridge['parent']).read_text()
    for r in bridge['functions']:
        assert part(pt,r['name'])==r['before'] and part(after,r['name'])==r['after']
    assert part(after,'run_native')==part(before,'run_native')==part(pt,'run_native')
    la=(B/'launch_three01.py').read_text()
    for x in ['characterize_clamped570_','source-freeze','source-only-peer-root','campaign','launch-once','controller','detached-launch']:
        la=la.replace(x+'01',x+'02')
    assert la==(B/'launch_three02.py').read_text()
    rc=read(B/'resource-contract01.json'); rc['native_root']=rc['native_root'].replace('/native01','/native02')
    assert rc==read(B/'resource-contract02.json')
    runtime=read(B/'runtime01.json');runtime['scope']=runtime['scope'].replace('Authoritative40','Authoritative41')
    assert runtime==read(B/'runtime02.json')
    controls={}
    for key,num in [('finite',11),('storage',23),('lifecycle',7)]:
        entry=f['actual_controls'][key]; r=read(entry['path']);assert pin(entry['path'])==entry['pin']
        assert r['cases']==num==len(r['outcomes']) and r['status']==entry['status'] and all(x['passed']for x in r['outcomes'])
        assert len({x['case']for x in r['outcomes']})==num
        assert r.get('source',r.get('producer',r.get('driver')))==pin(B/'characterize_clamped570_02.py')
        controls[key]=dict(result=entry,cases=[x['case']for x in r['outcomes']])
    raw=(B/'finite-controls01/positive.raw').read_bytes();end=raw.index(b'Binary:\n')+len(b'Binary:\n');header=raw[:end]
    storage=B/'storage-controls04/native'; prefixes=[]
    for label in ['short_writes','bad_trailer','shared_floor_after_received_block','bad_header','empty_header','declared_nonzero_points']:
        d=storage/label;actual=gzip.decompress((d/'wave.raw.gz').read_bytes())
        expected=raw if label=='short_writes'else raw[:-1]+b'5'if label=='bad_trailer'else header.replace(b'No. Variables: 1134',b'No. Variables: 1135')if label=='bad_header'else b''if label=='empty_header'else header.replace(b'No. Points: 0',b'No. Points: 4')if label=='declared_nonzero_points'else None
        if expected is None:assert raw.startswith(actual)
        else:assert actual==expected
        if (d/'capture-failure.json').exists():
            failure=read(d/'capture-failure.json');assert failure['received_raw_bytes']==len(actual) and failure['received_raw_sha256']==hashlib.sha256(actual).hexdigest()
            assert not failure['resumable_solver_checkpoint']
            if label=='declared_nonzero_points':assert failure['status']=='FAILED_HEADER_PREFIX_RETAINED' and 'NativeFIFO format'in failure['error']
        prefixes.append(dict(label=label,gzip=pin(d/'wave.raw.gz'),raw_bytes=len(actual),raw_sha256=hashlib.sha256(actual).hexdigest()))
    owners=[];ld=B/'lifecycle-controls04'
    for label in ['clean','term','interrupt']:
        d=ld/'native'/label; own=read(d/'owned-processes.json');exe=read(d/'execution.json');p=own['processes'][0]
        assert len(own['processes'])==1 and gzip.decompress((d/'wave.raw.gz').read_bytes())==raw
        assert p['status']==('REAPED_NO_LIVE_MEMBERS'if label=='clean'else'FAILURE_REAPED') and p['returncode']==(0 if label=='clean'else -15)
        now=identity(p['identity']['pid']);assert now is None or now['start_ticks']!=p['identity']['start_ticks']
        assert exe['actual_affinity']==[10]and exe['address_space_limit_bytes']==2*1024**3 and exe['elapsed_watchdog_seconds']is None
        if label!='clean':assert own['cleanup']['recording_errors']==own['cleanup']['observation_errors']==[]and all(not x['immediate_after_kill']for x in own['cleanup']['groups'])
        owners.append(dict(label=label,owner=pin(d/'owned-processes.json'),execution=pin(d/'execution.json'),birth=p['identity']))
    for signum in ['SIGTERM','SIGINT']:
        p=read(ld/(signum+'-completed-owner.json'))['processes'][0];assert p['status']=='REAPED_NO_LIVE_MEMBERS'and p['returncode']==0
    assert not(B/'native01').exists()and not(B/'native02').exists()
    prior=read(B/'resource-peer-pll01-findings.json')
    receipt=dict(status='PASS_SOURCE_AND_SAVED_570_RESOURCE_LIFECYCLE_CONTROLS',freeze=pin(fp),reviewer='PLL independent stdlib saved reader',findings=[],prior_finding=pin(B/'resource-peer-pll01-findings.json'),closed_finding='HEADER_POST_PARSE_RETENTION_GAP',whole_body_bridges=8,old1670pins_unchanged=True,current_files_rehashed=1736,current_actual_cases=41,controls=controls,failed_and_complete_prefixes=prefixes,actual_owned_fifo_cases=owners,resource_arithmetic=rc,scope=prior['scope'][:-1]+['Initial header-retention finding is closed by actual nonzero-count failure retaining exactly the consumed header bytes reported above, not unread payload.','Final combined launch gate and physics/deck/Meter audit remain root-owned. No native was launched by this reader.'],method=pin(__file__))
    target=B/'resource-peer-pll02.json';assert not target.exists();target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(result=str(target),pin=pin(target),current_cases=41,findings=[])))
if __name__=='__main__':main()
