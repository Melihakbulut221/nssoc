#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Observe power delivery in the saved power128 prefix; no acceptance or restart."""
import hashlib,json,os,struct,tempfile,traceback
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
from cloud_tx_output8088_power128_native import raw_state,source_valid
from cloud_tx_stream import read_streamed_wave,digest
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-power128-prefix-rails'
def read_saved_prefix(path,vectors,stop,step,expected):
    """Diagnostic-only immutable prefix; complete-capture acceptance is unavailable."""
    path=Path(path);assert vectors and len(vectors)==len(set(vectors))
    with path.open('rb') as stream:
        parts=[]
        while True:
            row=stream.readline(1048576)
            assert row and row.endswith(b'\n'),'Incomplete native header'
            parts.append(row)
            assert sum(map(len,parts))<=1048576,'Unbounded native header'
            if row==b'Binary:\n':break
        offset=stream.tell()
    header=b''.join(parts).decode('ascii')
    def field(key):
        matches=[line.split(':',1)[1].strip() for line in header.splitlines() if line.startswith(key+':')]
        assert len(matches)==1,('Missing/duplicate raw field',key)
        return matches[0]
    assert field('Flags')=='real' and field('Plotname')=='Transient Analysis'
    width=int(field('No. Variables'));count=int(field('No. Points'))
    assert width==len(vectors)+1
    observed=raw_state(path,width);assert observed==expected
    count=observed["complete_rows"];assert count>1
    assert header.count('Variables:\n')==1
    table=[row.split() for row in header.split('Variables:\n')[1].split('Binary:\n')[0].splitlines()]
    assert len(table)==width and all(len(row)==3 for row in table)
    assert [r[0] for r in table]==list(map(str,range(width)))
    assert table[0]==['0','time','time']
    aliases={'time':'time'}
    for name in vectors:
        for native in ([name,'i('+name+')'] if name.startswith('@') else [name]):
            assert native not in aliases or aliases[native]==name
            aliases[native]=name
    names=[]
    for _,native,kind in table:
        assert native in aliases,('Unexpected native vector',native)
        logical=aliases[native]
        expected='time' if logical=='time' else 'voltage' if logical.startswith('v(') else 'current'
        assert kind==expected,(native,kind,expected)
        names.append(logical)
    assert len(set(names))==width and set(names)=={'time',*vectors}
    assert path.stat().st_size-offset==count*width*8+observed['partial_row_bytes']
    assert offset==observed['header_bytes']
    matrix=np.memmap(path,mode='r',dtype='<f8',offset=offset,shape=(count,width))
    for first in range(0,count,1024):
        assert np.isfinite(matrix[first:first+1024]).all(),'Nonfinite native sample'
    t=matrix[:,0]
    assert t[0]==0 and abs(t[-1]-observed['last_time_s'])<1e-18 and t[-1]<stop
    delta=np.diff(t)
    assert np.all(delta>0) and np.max(delta)<=step*1.00001
    values={n:matrix[:,i] for i,n in enumerate(names) if i}
    return t,values,dict(complete_rows_in_prefix=count,columns=width,header_bytes=offset,
        original_header_declared_points=int(field('No. Points')),partial_tail_bytes_retained=observed['partial_row_bytes'],full_capture=False,
        raw_bytes=path.stat().st_size,raw_sha256=digest(path),
        start_s=float(t[0]),end_s=float(t[-1]),max_step_s=float(delta.max()),
        logical_vector_order=names,complete_unmodified_rows=True,
        method='Read-only complete rows from immutable saved native prefix; partial tail retained in source; not complete-capture acceptance')

def controls():
    vectors=['v(n)']
    header=b'Title: diagnostic fixture\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: 2\nNo. Points: 0\nVariables:\n\t0\ttime\ttime\n\t1\tv(n)\tvoltage\nBinary:\n'
    body=struct.pack('<dddddd',0.,0.,.5e-12,1.,1e-12,2.)+b'tail123'
    with tempfile.TemporaryDirectory()as td:
        p=Path(td)/'prefix.raw';p.write_bytes(header+body);expected=raw_state(p,2)
        t,v,proof=read_saved_prefix(p,vectors,34e-9,.5e-12,expected)
        assert len(t)==3 and list(v['v(n)'])==[0.,1.,2.]and proof['partial_tail_bytes_retained']==7
        assert not proof['full_capture']and p.read_bytes()==header+body
        try:read_streamed_wave(p,vectors,34e-9,.5e-12)
        except AssertionError:pass
        else:raise AssertionError('Original full-capture reader accepted incomplete prefix')
        rejected=[]
        for fault in ('changed_vector','changed_payload','truncated_prefix','lost_partial_tail','omitted_vector','nonfinite_value','nonmonotonic_time','oversized_step'):
            data=header+body;vv=vectors;reference=expected
            if fault=='changed_vector':data=data.replace(b'v(n)',b'v(x)')
            elif fault=='changed_payload':data=header+struct.pack('<dddddd',0.,.1,.5e-12,1.,1e-12,2.)+b'tail123'
            elif fault=='truncated_prefix':data=data[:-16]
            elif fault=='lost_partial_tail':data=data[:-7]
            elif fault=='omitted_vector':vv=[]
            else:
                payload={'nonfinite_value':(0.,0.,.5e-12,float('nan'),1e-12,2.),
                    'nonmonotonic_time':(0.,0.,.5e-12,1.,.4e-12,2.),
                    'oversized_step':(0.,0.,.5e-12,1.,2e-12,2.)}[fault]
                data=header+struct.pack('<dddddd',*payload)+b'tail123'
            p.write_bytes(data)
            if fault in ('nonfinite_value','nonmonotonic_time','oversized_step'):reference=raw_state(p,2)
            try:read_saved_prefix(p,vv,34e-9,.5e-12,reference)
            except (AssertionError,KeyError):rejected.append(fault)
            else:raise AssertionError('Accepted '+fault)
        return dict(status='PASS_PREFIX_DIAGNOSTIC_CONTROLS_ONLY',rejected=rejected,
            original_full_capture_reader_still_rejects_prefix=True,full_capture=False)
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],no_new_simulation=True,
        full_capture=False,electrical_accepted=False,full_phy_accepted=False,mainchip_integrated=False,
        scope='Actual power128 saved-prefix rail planes after2ns; not complete34ns or any device/signal/PHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        methods=json.loads((ROOT/'scripts/tx-power128-prefix-rails-methods.json').read_text())
        assert all(sha(ROOT/p)==v for p,v in methods.items());r['controls']=controls()
        pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128-first-continuations-20261021.json').read_text())['cases']['none']
        assert pin['run']==39630182787
        spec=pin['descriptor']
        live=json.loads(__import__('subprocess').check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/'+str(spec['run'])]))
        old,proof=reports.restore_report(spec['group'],spec['run'],spec['summary_sha256'],spec['parts_sha256'],
            OUT/'source',['work/wave.raw','work/contract.json'])
        source_valid(spec,live,old,methods['scripts/cloud_tx_output8088_power128_native.py'])
        assert old['raw_prefix']==pin['report_excerpt']['raw_prefix']
        case=OUT/'source/work';raw=case/'wave.raw';contract=json.loads((case/'contract.json').read_text())
        before=sha(raw);assert before==old['outputs']['work/wave.raw']
        ip=json.loads((ROOT/'docs/evidence/tx-output8088-power128-interfaces-pass-20261021.json').read_text())
        names=['interfaces.json','composed/composition.json','composed/intrinsic/native.json']
        ir,ipr=reports.restore_report('tx-output8088-power128-interfaces',ip['run'],ip['summary_sha256'],ip['parts_sha256'],OUT/'physical',names)
        assert ir==ip['report']and ir['sources_unchanged']
        interface=json.loads((OUT/'physical/interfaces.json').read_text())
        comp=json.loads((OUT/'physical/composed/composition.json').read_text())
        native=json.loads((OUT/'physical/composed/intrinsic/native.json').read_text())
        assert len(comp['device_records'])==8088 and interface['modes']['wire']==contract['interface_probes']
        t,values,transport=read_saved_prefix(raw,contract['vectors'],34e-9,contract['condition']['step_ps']*1e-12,old['raw_prefix'])
        assert transport['columns']==14182 and transport['complete_rows_in_prefix']==10423
        active=t>=2e-9;assert int(active.sum())>1000
        zeros=np.zeros_like(t);public={p.lower()for p in comp['interface']}
        def voltage(node):return zeros if node=='0'else values['v('+node+')']
        def terminal(node):return '0'if node.lower()in('avss','sub','wire_cref')else node.lower()if node.lower()in public else'xtree.'+node.lower()
        def span(value):
            v=np.asarray(value)[active];assert len(v)and np.isfinite(v).all()
            return dict(minimum=float(v.min()),median=float(np.median(v)),maximum=float(v.max()))
        ports={p['name']:p['cluster']for p in native['ports']};rails={}
        for rail in ('avdd','avss','dvdd'):
            connected={}
            for device in comp['device_records']:
                for q in device['terminals']:
                    if q['native_cluster']==ports[rail]:
                        connected.setdefault(terminal(q['node']),[]).append(dict(instance=device['instance'],model=device['model'],terminal=q['terminal']))
            assert connected
            external=voltage('0'if rail=='avss'else rail)
            planes={node:dict(voltage=span(voltage(node)),external_minus_local=span(external-voltage(node)),devices=devices)for node,devices in connected.items()}
            rails[rail]=dict(terminal_planes=len(planes),lowest=min(planes,key=lambda n:planes[n]['voltage']['minimum']),
                highest=max(planes,key=lambda n:planes[n]['voltage']['maximum']),planes=planes)
        assert sha(raw)==before and all(sha(ROOT/p)==v for p,v in methods.items())
        r.update(status='OBSERVED_ACTUAL_POWER128_PREFIX_RAILS_NOT_FULL_CAPTURE_OR_ACCEPTANCE',
            wave_source=proof,physical_interface_source=ipr,raw_prefix=old['raw_prefix'],transport=transport,
            active_window_s=[float(t[active][0]),float(t[-1])],active_complete_rows=int(active.sum()),rails=rails,sources_unchanged=True,
            comparison_limit='The old rejected8074 fullwave covers a different time window. These are prefix diagnostic measurements, not a fullwave A/B pass.',
            capture_retention='Complete original raw and partial tail retained in immutable source39630182787. Remove only this observer temporary copy after hash equality; live continuation untouched.')
        # The immutable source and active continuation are not modified.
        raw.unlink()
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
