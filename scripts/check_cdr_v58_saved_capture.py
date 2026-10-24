#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only source, actual small receipt and tiny transport corruption controls."""
import copy,hashlib,io,json,os,tarfile,tempfile
from pathlib import Path
import numpy as np
import cloud_cdr_v58_saved_capture as c
import cdr_v58_saved_rows as r
from cloud_chunked_results import pack

def controls():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    c.methods();req=json.loads((c.ROOT/c.REQ).read_text());faults=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,ValueError,KeyError,IndexError,FileNotFoundError,TypeError):faults.append(name)
        else:raise AssertionError('Accepted corruption '+name)
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);pin=req['failed_cases'][0]
        c.asset(pin['summary'],root/'summary.json');actual=json.loads((root/'summary.json').read_text());c.summary(actual,pin)
        run=c.api('actions/runs/'+str(c.RUN));job=c.api('actions/jobs/'+str(c.JOBS[pin['case']]));c.identity(run,job,pin['case'])
        for field,value in [('head_sha','0'*40),('id',1),('run_attempt',2),('status','in_progress'),('conclusion','success')]:
            bad=copy.deepcopy(run);bad[field]=value;reject('identity-'+field,lambda:c.identity(bad,job,pin['case']))
        bad=copy.deepcopy(job);bad['id']=c.JOBS['nominal_late'];reject('job-case',lambda:c.identity(run,bad,pin['case']))
        for field,value in [('source_head','0'*40),('case','hot_early'),('status','PASS'),('returncode',1),('diagnostics',['native failure']),('sources_unchanged',False),('error','other'),('devices_passed',True),('data_offset_s',0.)]:
            bad=copy.deepcopy(actual);bad[field]=value;reject('summary-'+field,lambda:c.summary(bad,pin))
        bad=copy.deepcopy(actual);bad['vectors'][0],bad['vectors'][1]=bad['vectors'][1],bad['vectors'][0]
        # Ordering is tied to the model-derived list and full raw capture, not set membership.
        reject('saved-vector-order',lambda:assert_equal(bad['vectors'],actual['vectors']))
        for field in ('sha256','bytes','source_directory'):
            bad=copy.deepcopy(pin['parts']['manifest']);bad[field]='wrong'
            reject('manifest-'+field,lambda:c.manifest_valid(bad,pin))
        for mode in ('duplicate','reorder','offset','hash'):
            bad=copy.deepcopy(pin['parts']['manifest'])
            if mode=='duplicate':bad['parts']*=2
            elif mode=='reorder':bad['parts'][0]['index']=1
            elif mode=='offset':bad['parts'][0]['bytes']-=1
            else:bad['parts'][0]['sha256']='0'*64
            reject('manifest-part-'+mode,lambda:c.manifest_valid(bad,pin))
        physical=json.loads((c.ROOT/'docs/evidence/cdr500-input-access-v58-physical-pass-20261024.json').read_text())['report']['native_planes']
        contract=json.loads((c.ROOT/'docs/evidence/cdr500-v58-mim-precision-pass-20261024.json').read_text())['report']['composition']['contract']
        clock=r.topology(contract,physical,actual['binding'],req)
        for mode in ('duplicate-id','clock-polarity','hold-track','terminal-cluster','current-vector'):
            bad=copy.deepcopy(req)
            if mode=='duplicate-id':bad['clock_mapping_requirement']['parallel_pairs'][0]['native_ids'][1]=61
            elif mode=='clock-polarity':bad['clock_mapping_requirement']['parallel_pairs'][0]['clock']='cp'
            elif mode=='hold-track':bad['clock_mapping_requirement']['parallel_pairs'][0]['collector_drives_HBT_emitter_ids']=[51,52]
            elif mode=='terminal-cluster':bad['exact_failed_device_records'][0]['terminals'][0]['native_cluster']+=1
            else:bad['clock_mapping_requirement']['parallel_pairs'][0]['vectors'][0]['Ic']='@wrong[ic]'
            reject('topology-'+mode,lambda:r.topology(contract,physical,actual['binding'],bad))
        source=(c.ROOT/'scripts/cloud_cdr500_v58_loaded.py').read_text();r.measurement_source(source)
        for before,after in [('>=.4','>=.3'),('>=.03','>=.02'),('(.3,.6,.9)','(.4,.6,.9)'),('50e-6','40e-6')]:
            assert before in source
            reject('frozen-gate-'+before,lambda before=before,after=after:r.measurement_source(source.replace(before,after,1)))
        for key in ('phase_average_v','devices_passed','sampler_checks'):
            bad=copy.deepcopy(actual);bad[key]=None
            reject('original-measurement-'+key,lambda key=key,bad=bad:r.compare_reproduction({key:actual[key]},bad))
        # Synthetic raw files exercise original frozen parser; they never qualify DUT.
        t=np.array([0.,.25,.5,.75,1.]);d={'v(c)':np.array([1.,3.,2.,4.,3.]),'v(e)':np.array([0.,2.,0.,3.,1.])}
        names=list(d)
        def native(path,time=t,data=d,order=names):
            header='Title: control\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: 3\nNo. Points: 5\nVariables:\n0 time time\n'+''.join(str(i+1)+' '+n+' voltage\n' for i,n in enumerate(order))+'Binary:\n'
            raw=header.encode()+np.column_stack([time,*[data[n] for n in order]]).astype('<f8').tobytes()
            path.write_bytes(raw);return raw
        raw=native(root/'good.raw');tt,dd,cap=c.stream.read_streamed_wave(root/'good.raw',names,1.,.25)
        assert np.array_equal(tt,t) and all(np.array_equal(dd[n],d[n]) for n in names)
        for mode in ('truncated','extra','nonfinite','row-order','missing-vector','duplicate-vector','vector-order'):
            path=root/(mode+'.raw')
            if mode=='truncated':path.write_bytes(raw[:-1])
            elif mode=='extra':path.write_bytes(raw+b'x')
            elif mode=='nonfinite':
                bad=copy.deepcopy(d);bad['v(c)'][2]=np.nan;native(path,data=bad)
            elif mode=='row-order':native(path,time=t[[0,2,1,3,4]])
            elif mode=='missing-vector':path.write_bytes(raw.replace(b'v(c)',b'v(x)',1))
            elif mode=='duplicate-vector':path.write_bytes(raw.replace(b'v(c)',b'v(e)',1))
            else:native(path,order=names[::-1])
            def read(path=path):
                _,_,value=c.stream.read_streamed_wave(path,names,1.,.25)
                assert value['logical_vector_order']==cap['logical_vector_order']
            reject('raw-'+mode,read)
        assert r.bracket(t,d,.5,names)['rows'][0]['row']==2
        assert [x['row'] for x in r.bracket(t,d,.6,names)['rows']]==[2,3]
        for x in (-1.,2.,float('nan')):reject('bracket-outside-'+str(x),lambda x=x:r.bracket(t,d,x,names))
        delta=d['v(c)']-d['v(e)'];idx=int(np.argmax(abs(delta)))
        exact=r.point(t,d,idx,names);assert exact['values']['v(c)']-exact['values']['v(e)']==float(delta[idx])
        reject('independent-time-extrema',lambda:assert_equal(float(d['v(c)'].max()-d['v(e)'].min()),float(abs(delta).max())))
        ev=r.crossings(t,np.array([-1.,0.,0.,1.,-1.]),0,1)
        assert [(x['left_row'],x['right_row']) for x in ev]==[(0,3),(3,4)]
        assert r.relation(ev[0],ev[1])=='overlapping_native_brackets_order_ambiguous'
        meta=r.cache(root/'selected.bin',t,d,names)
        for mode in ('bits','truncate','order'):
            bad=copy.deepcopy(meta);path=root/('cache-'+mode+'.bin');data=(root/'selected.bin').read_bytes()
            if mode=='bits':data=data[:-1]+bytes([data[-1]^1]);bad['sha256']=hashlib.sha256(data).hexdigest()
            elif mode=='truncate':data=data[:-1]
            else:bad['columns']=['time',*names[::-1]]
            path.write_bytes(data);reject('cache-'+mode,lambda:r.verify_cache(path,t,d,bad))
        # Real tiny gzip tar fixtures: complete hash/CRC + exact inventory gate.
        fixture=root/'fixture';fixture.mkdir()
        for name in c.SELECT:
            p=fixture/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(name.encode())
        fixture_report={'outputs':{n:c.sha(fixture/n) for n in c.SELECT}}
        summary_bytes=(json.dumps(fixture_report)+'\n').encode();(fixture/'result.json').write_bytes(summary_bytes)
        packed=pack(fixture,'fixture',root,127)
        good=c.restore(packed,root,root/'good-restored',fixture_report,hashlib.sha256(summary_bytes).hexdigest())
        assert len(good['selected'])==9
        for mode in ('part-order','part-truncate','part-bit'):
            bad=copy.deepcopy(packed);folder=root
            if mode=='part-order':bad['parts']=bad['parts'][::-1]
            else:
                folder=root/mode;folder.mkdir()
                for p in packed['parts']:(folder/p['name']).write_bytes((root/p['name']).read_bytes())
                p=folder/packed['parts'][-1]['name'];b=p.read_bytes();p.write_bytes(b[:-1] if mode=='part-truncate' else b[:-1]+bytes([b[-1]^1]))
            reject('transport-'+mode,lambda:c.restore(bad,folder,root/('bad-'+mode),fixture_report,hashlib.sha256(summary_bytes).hexdigest()))
        for mode in ('traversal','absolute','alias','symlink','duplicate','missing'):
            entries=[(str(p.relative_to(root)),p.read_bytes(),tarfile.REGTYPE) for p in fixture.rglob('*') if p.is_file()]
            if mode=='missing':entries=entries[1:]
            elif mode=='duplicate':entries.append(entries[0])
            elif mode=='symlink':entries.append(('fixture/link',b'',tarfile.SYMTYPE))
            else:entries.append(({'traversal':'fixture/../escape','absolute':'/escape','alias':'fixture//alias'}[mode],b'x',tarfile.REGTYPE))
            path=root/(mode+'.tar.gz.part0000')
            with tarfile.open(path,'w:gz') as archive:
                for name,b,kind in entries:
                    item=tarfile.TarInfo(name);item.type=kind;item.size=len(b);item.linkname='/escape' if kind==tarfile.SYMTYPE else ''
                    archive.addfile(item,io.BytesIO(b))
            size=path.stat().st_size;digest=c.sha(path)
            m=dict(format='ordered-tar-gzip-parts-v1',source_directory='fixture',stem=mode,bytes=size,sha256=digest,
                parts=[dict(index=0,name=path.name,bytes=size,sha256=digest)])
            reject('archive-'+mode,lambda:c.restore(m,root,root/('bad-'+mode),fixture_report,hashlib.sha256(summary_bytes).hexdigest()))
    assert len(faults)==len(set(faults))==58,len(faults)
    return dict(status='PASS_SAVED_CDR_SOURCE_AND58_CORRUPTION_CONTROLS_ONLY',rejected=faults,
        actual_source_summary_authenticated=True,actual32_clock_topology_bound=True,
        frozen_original_measurement_bytes=6722,full_native_capture_read=False,new_simulation=False,
        cdr_accepted=False,full_phy_accepted=False)

def assert_equal(a,b):assert a==b
if __name__=='__main__':print(json.dumps(controls(),indent=2))
