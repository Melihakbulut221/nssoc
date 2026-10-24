#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Replay the exact 131-column native cache; no simulator or full-capture restore."""
import copy, hashlib, io, json, os, shutil, subprocess, sys, tarfile, tempfile, traceback
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import numpy as np
import cloud_pll_first_latch_sinks as original
import pll_first_latch_native_sampling as sampling
old = original.old
events = original.events
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cloud-pll-first-latch-cache-replay'
REPO = 'repos/Melihakbulut221/nssoc/'
METHOD = 'scripts/pll-first-latch-cache-replay-methods.json'
RECEIPT = 'docs/evidence/pll-first-latch-full131-rejection-20261024.json'
SOURCE = '21f0e56b39b21901cd4a38012503071ccb1f9914'
RUN = 40096538128
JOB = 120879990694
STEM = 'pll-first-latch-sinks-40096538128-1'
PREFIX = 'cloud-pll-first-latch-sinks'
SUMMARY_SHA = '6d2b595d734cfa1ee4f4f6a53b8baa124faef1a4f87cff664cb285b60b845969'
PARTS_SHA = 'c00110e3914af0548260baf157d849bc3031ce73ab8669df34925ea42567fb52'
CACHE_SHA = 'aad3cab8f3035a7c89eca665016bc15558152877bc058972f8a03dfa4172bf97'
OLD8_SHA = '9f4b797a03a6178ae6bf021b7e2cd6f4ba165b4b9322caabb67064aed8f2186b'
ARCHIVE_SHA = '066f788046541e10f48e1d8122a442933c56d590d2206ca3883d7b931287b12c'
LOG_SHA = '81cab7d6ce1154be5294ca898a984d0df7873438492cc2d642811c78731d2c8d'
PARTS = [
 (672440590,1073741824,'fcf03cf9a4b7956104e7f41763cba0b94258e922b85b7525b5fecd283b9167dc'),
 (672442100,1073741824,'222c22dab5ec349dbe4f4f64beab4514f16db6ad064b8cf0d277a005a7c0564e'),
 (672443604,820833375,'c6f743f96f760dc68056ac31f67117d8e497a4ee3512248b5b41197c368d577e')]
CACHE_BYTES = 3355077680
ARCHIVE_BYTES = 2968317023
OLD8 = ['time','v(reference)','v(fb)','v(clkp)','v(clkn)','v(vctrl)','v(up)','v(down)']
REPRODUCTION = dict(original_rejection_reproduced=True, original_cache_bits_identical=True,
 full5106_column_capture_verified=True, acquisition_accepted=False)

def digest(b): return hashlib.sha256(b).hexdigest()
def file_sha(path): return events.file_sha(path)
def api(path): return events.api(path)
def small(asset,sha,size=None): return events.small(asset,sha,size)
def write_json(path,value): path.write_text(json.dumps(value,indent=2)+'\n')

def methods():
    original.methods()
    m = json.loads((ROOT/METHOD).read_text())
    for path, sha in m['protected'].items():
        assert file_sha(ROOT/path) == sha, path
    assert m['native_simulation_allowed'] is False
    return m

def summary_valid(s):
    assert s['status'] == 'FAIL_FIRST_LATCH_SINK_DIAGNOSIS'
    assert s['source_head'] == SOURCE and str(s['run_id']) == str(RUN)
    assert not any(s[k] for k in ('native_activation_performed','acquisition_accepted',
        'full_device_safety_accepted','full_phy_accepted','qualified_pex'))
    assert s['original_reproduction'] == REPRODUCTION
    assert s['full5106_column_capture_verified'] is True
    assert s['prior80_column_sha256'] == events.CACHE_SHA
    c = s['selected_cache']
    assert c['rows'] == 3201410 and len(c['columns']) == len(set(c['columns'])) == 131
    assert c['columns'][0] == 'time' and c['bytes'] == CACHE_BYTES and c['sha256'] == CACHE_SHA
    assert c['all_sample_bits_checked'] is True and c['readonly'] is True
    assert c['samples_removed'] == 0 and c['resampled'] is False
    assert c['format'] == 'row-major little-endian binary64 without header'
    assert s['error'] == 'AssertionError()'
    t = s['traceback']
    assert t.count('line 142, in analyze') == 1 and t.count('line 205, in main') == 1
    assert "hi=int(np.searchsorted(t,x,'left'));assert 0<hi<len(t)" in t
    assert t.endswith('AssertionError\n')
    return c

def manifest_valid(m):
    assert m['format'] == 'ordered-tar-gzip-parts-v1' and m['stem'] == STEM
    assert m['source_directory'] == PREFIX
    assert m['bytes'] == ARCHIVE_BYTES and m['sha256'] == ARCHIVE_SHA
    assert m['part_limit_bytes'] == 1073741824 and len(m['parts']) == 3
    for i,(p,(_,size,sha)) in enumerate(zip(m['parts'],PARTS,strict=True)):
        assert p == dict(index=i,name=STEM+'.tar.gz.part'+str(i).zfill(4),bytes=size,sha256=sha)
    assert m['verification'] == dict(parts=3,bytes=ARCHIVE_BYTES,sha256=ARCHIVE_SHA,
        all_parts_and_combined_bytes_verified=True)

def source_identity():
    r = api('actions/runs/'+str(RUN))
    assert r['id'] == RUN and r['status'] == 'completed' and r['conclusion'] == 'failure'
    assert r['head_sha'] == SOURCE and r['run_attempt'] == 1 and r['event'] == 'workflow_dispatch'
    assert r['head_branch'] == 'codex/pll-feedback-cycle-diagnosis'
    assert r['path'] == '.github/workflows/pll-first-latch-sinks-cloud.yml'
    j = api('actions/runs/'+str(RUN)+'/jobs?per_page=100')
    assert j['total_count'] == 2
    rows = {x['name']:x for x in j['jobs']}
    assert set(rows) == {'controls','diagnostic'}
    assert rows['controls']['conclusion'] == 'success'
    assert rows['diagnostic']['id'] == JOB and rows['diagnostic']['conclusion'] == 'failure'
    assert rows['diagnostic']['head_sha'] == SOURCE and rows['diagnostic']['run_attempt'] == 1
    log = subprocess.check_output(['gh','api',REPO+'actions/jobs/'+str(JOB)+'/logs'])
    assert digest(log) == LOG_SHA
    assert b'line 142, in analyze' in log and b'AssertionError' in log
    return dict(run=RUN,source=SOURCE,attempt=1,job=JOB,conclusion='failure',job_log_sha256=LOG_SHA)

@contextmanager
def asset_stream(asset):
    p = subprocess.Popen(['gh','api',REPO+'releases/assets/'+str(asset),
        '-H','Accept: application/octet-stream'],stdout=subprocess.PIPE)
    try:
        yield p.stdout
    except BaseException:
        p.stdout.close()
        if p.poll() is None: p.terminate()
        p.wait()
        raise
    else:
        p.stdout.close()
        assert p.wait() == 0, 'Cloud part download failed'

def concat_checked(manifest,open_part,target):
    """Hashes are checked only after complete stream exhaustion, including all parts."""
    h = hashlib.sha256(); total = 0
    with target.open('xb') as out:
        for i,part in enumerate(manifest['parts']):
            assert part['index'] == i
            ph = hashlib.sha256(); n = 0
            with open_part(i) as inp:
                while True:
                    b = inp.read(1048576)
                    if not b: break
                    n += len(b); assert n <= part['bytes'], 'Part overrun'
                    ph.update(b); h.update(b); out.write(b)
            assert n == part['bytes'] and ph.hexdigest() == part['sha256'], 'Incomplete or corrupt part'
            total += n
            print('Verified cache archive part',i,n,flush=True)
    assert total == manifest['bytes'] and h.hexdigest() == manifest['sha256']
    assert target.stat().st_size == total and file_sha(target) == manifest['sha256']
    return dict(bytes=total,sha256=h.hexdigest(),parts=len(manifest['parts']),
                all_parts_and_combined_bytes_verified=True)

def extract_exact(archive,work,cache_bytes):
    expected = {'result.json':20000000,'selected-native.bin':cache_bytes,
        'selected-native.json':20000000,'original-feedback-diagnosis.json':20000000,
        'original-review.json':20000000}
    found = {}; root_seen = False
    with tarfile.open(archive,mode='r|gz') as tar:
        for member in tar:
            if member.name in (PREFIX,PREFIX+'/'):
                assert member.isdir() and not root_seen
                root_seen = True; continue
            assert member.name.startswith(PREFIX+'/'), 'Wrong archive root'
            name = member.name[len(PREFIX)+1:]
            assert name in expected and member.name == PREFIX+'/'+name, 'Unexpected or unsafe member'
            assert name not in found and member.isfile() and not member.issparse(), 'Alias, duplicate or sparse member'
            assert 0 <= member.size <= expected[name]
            if name == 'selected-native.bin': assert member.size == cache_bytes
            target = work/name
            with tar.extractfile(member) as inp, target.open('xb') as out:
                shutil.copyfileobj(inp,out,1048576)
            assert target.stat().st_size == member.size
            found[name] = target
    assert root_seen and set(found) == set(expected)
    return found

def restore(work,s,m):
    assert shutil.disk_usage(work).free >= 9*1024**3, 'Insufficient cloud restore reserve'
    rel = api('releases/tags/cloud-results-'+str(RUN)+'-1-pll-first-latch-sinks')
    byname = {a['name']:a for a in rel['assets']}
    assert len(byname) == len(rel['assets']) == 5
    ids = []
    for i,(aid,size,sha) in enumerate(PARTS):
        a = byname[m['parts'][i]['name']]
        assert (a['id'],a['size'],a['digest']) == (aid,size,'sha256:'+sha)
        ids.append(aid)
    for suffix,aid,size,sha in [
        ('.summary.json',672440354,7928,SUMMARY_SHA),('.parts.json',672440465,1275,PARTS_SHA)]:
        a = byname[STEM+suffix]
        assert (a['id'],a['size'],a['digest']) == (aid,size,'sha256:'+sha)
    archive = work/'source.tar.gz'
    proof = concat_checked(m,lambda i:asset_stream(ids[i]),archive)
    found = extract_exact(archive,work,CACHE_BYTES)
    assert file_sha(found['result.json']) == SUMMARY_SHA
    assert json.loads(found['result.json'].read_text()) == s
    assert file_sha(found['selected-native.bin']) == CACHE_SHA
    assert json.loads(found['selected-native.json'].read_text()) == s['selected_cache']
    assert file_sha(found['original-feedback-diagnosis.json']) == events.DIAG_SHA
    archive.unlink() # large verified cache is temporary and never republished
    return found,proof

def cache_scan(path,c,prior,old8,expected_prior,expected_old8,chunk=4096):
    names = c['columns']
    assert len(names) == len(set(names)) and names[0] == 'time'
    assert c['bytes'] == c['rows']*len(names)*8 and path.stat().st_size == c['bytes']
    assert file_sha(path) == c['sha256']
    raw = np.memmap(path,dtype='<f8',mode='r',shape=(c['rows'],len(names)))
    indices = [names.index(n) for n in prior]; oi = [names.index(n) for n in old8]
    h = hashlib.sha256(); oh = hashlib.sha256(); last = None; seen = 0
    for lo in range(0,c['rows'],chunk):
        block = raw[lo:lo+chunk,:]
        assert np.isfinite(block).all(), 'Nonfinite native cache sample'
        t = block[:,0]
        assert np.all(np.diff(t)>0), 'Repeated or unordered time within chunk'
        if last is not None: assert t[0]>last, 'Repeated or unordered time across chunks'
        last = float(t[-1]); seen += len(block)
        h.update(np.take(block,indices,axis=1).tobytes(order='C'))
        oh.update(np.take(block,oi,axis=1).tobytes(order='C'))
    assert seen == c['rows'] and raw[0,0] == 0. and raw[-1,0] == 1e-6
    assert h.hexdigest() == expected_prior and oh.hexdigest() == expected_old8
    assert raw.flags.writeable is False
    return raw,dict(rows=seen,columns=len(names),all_selected_columns_finite=True,
        all_times_strictly_increasing=True,prior80_sha256=h.hexdigest(),old8_sha256=oh.hexdigest(),
        all_sample_bits_checked=True,samples_removed=0,resampled=False,readonly=True)

def exact_original_failure(data,mapping,chain,analysis,out):
    """Require only the original empty AssertionError at the exact frozen code object/line."""
    assert original.analyze.__code__.co_filename == original.__file__
    with patch.object(original,'OUT',out):
        try:
            original.analyze(data,mapping,chain,analysis)
        except AssertionError as error:
            assert error.args == (), 'Different original assertion'
            tb = error.__traceback__
            while tb.tb_next: tb = tb.tb_next
            assert tb.tb_frame.f_code is original.analyze.__code__ and tb.tb_lineno == 142
            frame = tb.tb_frame.f_locals
            t = frame['t']; x = float(frame['x']); hi = int(frame['hi'])
            assert hi == 0 and x == float(t[0]) == float(data['time'][0]) == 0.
            assert int(np.searchsorted(t,x,'left')) == 0
            assert file_sha(out/'original-feedback-diagnosis.json') == events.DIAG_SHA
            witness = dict(exception='AssertionError()',source=SOURCE,line=142,function='analyze',
                time_s=x,native_row=hi,event_kind=frame['kind'],threshold=frame['key'],
                interval_s=[float(frame['a']),float(frame['b'])],
                original_diagnostic_sha256=events.DIAG_SHA,
                first_native_time_bits=int(np.asarray(t[:1],dtype='<f8').view('<u8')[0]))
            traceback.clear_frames(error.__traceback__)
            return witness
        else:
            raise AssertionError('Original native-endpoint failure did not reproduce')

def controls(s,m):
    """Real metadata mutations plus complete successful/failing transport fixtures; no simulator."""
    methods(); summary_valid(s); manifest_valid(m)
    bad = []
    def reject(name,fn):
        try: fn()
        except (AssertionError,KeyError,ValueError,tarfile.TarError,EOFError): bad.append(name)
        else: raise AssertionError('Accepted fault '+name)
    for label,mutate in [
        ('accepted-source',lambda x:x.__setitem__('acquisition_accepted',True)),
        ('wrong-source',lambda x:x.__setitem__('source_head','0'*40)),
        ('wrong-run',lambda x:x.__setitem__('run_id','1')),
        ('missing-full5106-proof',lambda x:x.__setitem__('full5106_column_capture_verified',False)),
        ('changed-prior80',lambda x:x.__setitem__('prior80_column_sha256','0'*64)),
        ('different-original-failure',lambda x:x.__setitem__('error','AssertionError("other")')),
        ('different-failure-line',lambda x:x.__setitem__('traceback',x['traceback'].replace('line 142','line 141'))),
        ('cache-row-loss',lambda x:x['selected_cache'].__setitem__('rows',3201409)),
        ('cache-column-duplicate',lambda x:x['selected_cache']['columns'].__setitem__(1,'time')),
        ('cache-bit-hash',lambda x:x['selected_cache'].__setitem__('sha256','0'*64)),
        ('cache-resampled',lambda x:x['selected_cache'].__setitem__('resampled',True))]:
        q=copy.deepcopy(s);mutate(q);reject(label,lambda:summary_valid(q))
    for label,mutate in [
        ('part-loss',lambda x:x['parts'].pop()),
        ('part-order',lambda x:x['parts'].reverse()),
        ('part-hash',lambda x:x['parts'][1].__setitem__('sha256','0'*64)),
        ('part-size',lambda x:x['parts'][1].__setitem__('bytes',1)),
        ('archive-hash',lambda x:x.__setitem__('sha256','0'*64)),
        ('archive-root',lambda x:x.__setitem__('source_directory','other')),
        ('incomplete-publication',lambda x:x['verification'].__setitem__('all_parts_and_combined_bytes_verified',False))]:
        q=copy.deepcopy(m);mutate(q);reject(label,lambda:manifest_valid(q))
    with tempfile.TemporaryDirectory(prefix='replay-transport-controls-') as td:
        d=Path(td); chunks=[b'first\x00payload',b'middle\x00payload',b'last\xffpayload']
        fm=dict(parts=[dict(index=i,bytes=len(b),sha256=digest(b)) for i,b in enumerate(chunks)],
            bytes=sum(map(len,chunks)),sha256=digest(b''.join(chunks)))
        def opener(values):
            @contextmanager
            def open_part(i): yield io.BytesIO(values[i])
            return open_part
        positive=concat_checked(fm,opener(chunks),d/'positive.parts')
        for label,values in [
            ('truncated-part-stream',[chunks[0],chunks[1][:-1],chunks[2]]),
            ('extra-part-byte',[chunks[0],chunks[1]+b'x',chunks[2]]),
            ('corrupt-part-stream',[chunks[0],b'X'+chunks[1][1:],chunks[2]]),
            ('reordered-part-stream',[chunks[1],chunks[0],chunks[2]]),
            ('last-part-truncated',[chunks[0],chunks[1],chunks[2][:-1]])]:
            reject(label,lambda:concat_checked(fm,opener(values),d/label))
        q=copy.deepcopy(fm);q['sha256']='0'*64
        reject('combined-hash-after-all-parts',lambda:concat_checked(q,opener(chunks),d/'combined-bad'))
        @contextmanager
        def failed_exit(i):
            yield io.BytesIO(chunks[i])
            raise AssertionError('Downloader nonzero after valid bytes')
        reject('stream-exit-after-valid-bytes',lambda:concat_checked(fm,failed_exit,d/'exit-bad'))
        fixture={'result.json':b'{}','selected-native.bin':b'\x00'*16,
                 'selected-native.json':b'{}','original-feedback-diagnosis.json':b'{}','original-review.json':b'{}'}
        def make_tar(path,mutation=None):
            entries=[(PREFIX+'/',b'',tarfile.DIRTYPE)]+[(PREFIX+'/'+n,b,tarfile.REGTYPE)for n,b in fixture.items()]
            if mutation: entries=mutation(entries)
            with tarfile.open(path,'w:gz') as t:
                for n,b,kind in entries:
                    info=tarfile.TarInfo(n);info.type=kind;info.size=len(b) if kind==tarfile.REGTYPE else 0
                    if kind in (tarfile.SYMTYPE,tarfile.LNKTYPE): info.linkname='/tmp/forbidden'
                    t.addfile(info,io.BytesIO(b) if kind==tarfile.REGTYPE else None)
        tarpath=d/'good.tar.gz';make_tar(tarpath);target=d/'good-extract';target.mkdir()
        assert len(extract_exact(tarpath,target,16))==5
        changes=[
            ('tar-extra',lambda es:es+[(PREFIX+'/extra.json',b'{}',tarfile.REGTYPE)]),
            ('tar-traversal',lambda es:es+[(PREFIX+'/../escape',b'x',tarfile.REGTYPE)]),
            ('tar-absolute',lambda es:es+[('/tmp/escape',b'x',tarfile.REGTYPE)]),
            ('tar-duplicate',lambda es:es+[es[1]]),
            ('tar-nested-alias',lambda es:[es[0]]+[(n.replace('/result.json','/sub/result.json'),b,k)for n,b,k in es[1:]]),
            ('tar-symlink',lambda es:es[:1]+[(es[1][0],b'',tarfile.SYMTYPE)]+es[2:]),
            ('tar-hardlink',lambda es:es[:1]+[(es[1][0],b'',tarfile.LNKTYPE)]+es[2:]),
            ('tar-missing',lambda es:es[:-1]),
            ('tar-missing-root',lambda es:es[1:]),
            ('tar-wrong-cache-size',lambda es:[(n,b+b'x' if n.endswith('.bin')else b,k)for n,b,k in es])]
        for label,mutate in changes:
            a=d/(label+'.tgz');make_tar(a,mutate);target=d/label;target.mkdir()
            reject(label,lambda:extract_exact(a,target,16))
        values=np.arange(21,dtype='<f8').reshape(7,3);values[:,0]=np.linspace(0,1e-6,7)
        names=['time','v(a)','v(b)'];prior=['time','v(b)'];old8=['time','v(a)']
        def cache_check(v,name,hash_override=None,prior_order=None):
            path=d/(name+'.bin');path.write_bytes(v.tobytes())
            c=dict(rows=7,columns=names,bytes=v.nbytes,sha256=hash_override or digest(v.tobytes()))
            return cache_scan(path,c,prior_order or prior,old8,digest(values[:,[0,2]].tobytes()),
                              digest(values[:,[0,1]].tobytes()),chunk=3)
        _,scan=cache_check(values,'cache-positive')
        reject('cache-persisted-bit',lambda:cache_check(values,'hash-bad','0'*64))
        reject('cache-prior-order',lambda:cache_check(values,'order-bad',prior_order=prior[::-1]))
        for label,row,col,value in [('cache-nan',4,2,np.nan),('cache-same-time-seam',3,0,values[2,0]),
            ('cache-unordered-time',2,0,-1.),('cache-original8-bit',1,1,999.),('cache-prior80-bit',2,2,999.),
            ('cache-first-time',0,0,1e-12),('cache-last-time',6,0,1.1e-6)]:
            q=values.copy();q[row,col]=value;reject(label,lambda:cache_check(q,label))
    assert len(bad)==44, len(bad)
    return dict(status='PASS_REPLAY_TRANSPORT_METADATA_CACHE_AND44_FAULTS',
        rejected=bad,successful_three_part_transport=positive,successful_exact_tar=True,
        successful_chunked_cache=scan,endpoint_sampling=sampling.controls(),
        original_source_and_observer_controls=original.controls(),native_simulation_started=False)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true','Cloud-only'
    assert sys.argv[1:] in (['--controls'],['--replay'])
    OUT.mkdir(exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],run_id=os.environ['GITHUB_RUN_ID'],
        native_activation_performed=False,full_capture_reread=False,acquisition_accepted=False,
        full_device_safety_accepted=False,full_phy_accepted=False,qualified_pex=False,large_cache_republished=False)
    try:
        r['method']=methods()
        s=json.loads(small(672440354,SUMMARY_SHA,7928))
        m=json.loads(small(672440465,PARTS_SHA,1275))
        r['controls']=controls(s,m)
        if sys.argv[1:]==['--controls']:
            r['status']='PASS_FIRST_LATCH_CACHE_REPLAY_CONTROLS_NO_NATIVE_ANALYSIS';return
        r['original_failed_job']=source_identity()
        with tempfile.TemporaryDirectory(prefix='first-latch-cache-only-') as td:
            work=Path(td)
            found,r['transport']=restore(work,s,m)
            current=json.loads(found['original-review.json'].read_text())
            base=json.loads(small(671784463,events.OLD_SHA))
            assert base['source_checkpoint']==old.SOURCE
            r['original_reproduction']=old.reproduce(current,base)
            assert r['original_reproduction']==REPRODUCTION
            assert base['analyzer_cache']['selected_row_major_binary64_sha256']==OLD8_SHA
            assert base['analyzer_cache']['cached_columns']==OLD8
            prev=json.loads(small(672131330,events.SUMMARY_SHA,288016));events.summary_valid(prev)
            mapping=json.loads((ROOT/original.MAP).read_text())
            chain=json.loads((ROOT/old.MAP).read_text())
            ref=old.adapter.reference.load_reference(work/'reference')
            assert digest((json.dumps(ref['contract'],indent=2)+'\n').encode())==mapping['proofs']['contract_sha256']
            selected,prior=original.choose(mapping,ref['contract']['raw_table'],chain)
            assert selected==s['selected_cache']['columns'] and prior==prev['selected_cache']['columns']
            raw,r['cache']=cache_scan(found['selected-native.bin'],s['selected_cache'],prior,
                                     OLD8,events.CACHE_SHA,OLD8_SHA)
            data={n:raw[:,i] for i,n in enumerate(selected)}
            failed=work/'original-failure';failed.mkdir()
            r['original_analyze_failure']=exact_original_failure(data,mapping,chain,
                current['independent_acquisition'],failed)
            diagnosis=sampling.replay_analyze(data,mapping,chain,current['independent_acquisition'],OUT)
            witnesses=diagnosis['native_sampling_repair']['original_assertion_endpoint_witnesses']
            old_witness=r['original_analyze_failure']
            assert any(w['time_s']==old_witness['time_s'] and w['threshold']==old_witness['threshold']
                       and w['kind']==old_witness['event_kind'] and w['interval_s']==old_witness['interval_s']
                       for w in witnesses), 'Repair did not explain exact original failure event'
            assert file_sha(OUT/'original-feedback-diagnosis.json')==events.DIAG_SHA
            write_json(OUT/'first-latch-diagnosis.json',diagnosis)
            r['diagnosis_sha256']=file_sha(OUT/'first-latch-diagnosis.json')
            r['native_sampling_repair']=diagnosis['native_sampling_repair']
            r['master_transition_histograms']={k:{p:v[p]for p in
              ('complete_input_intervals','transition_count_histogram')}for k,v in diagnosis['master_events'].items()}
            r['signals']={k:v['full']for k,v in diagnosis['signals'].items()}
            write_json(OUT/'original-failure-receipt.json',json.loads((ROOT/RECEIPT).read_text()))
            del data,raw
        methods()
        r['status']='PASS_EXACT_FIRST_LATCH_CACHE_REPLAY_ORIGINAL_PLL_ACQUISITION_REMAINS_REJECTED'
    except BaseException as error:
        r.update(status='FAIL_FIRST_LATCH_CACHE_REPLAY',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        # Only small diagnosis/receipts are retained; selected-native.bin never enters OUT.
        assert not any(p.name.endswith('.bin') for p in OUT.rglob('*'))
        r['outputs']={str(p.relative_to(OUT)):file_sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
        write_json(OUT/'result.json',r)
        print(r['status'],flush=True)
if __name__=='__main__': main()
