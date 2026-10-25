#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read the completed 50ns all-HBT capture; never repeat its native simulation."""
import json,os,re
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
import run_cloud_pll865_snapshot as pll
from route_cloud_newer_postcts import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-pll-divider-review'
def inspect_op(raw,base,vectors):
    marker=b'Binary:\n';stop=raw.find(marker,0,1048576);assert stop>=0;stop+=len(marker)
    header=raw[:stop].decode('ascii');fields={l.split(':',1)[0]:l.split(':',1)[1].strip()for l in header.splitlines()if ':'in l}
    assert fields['Flags']=='real' and fields['Plotname'].lower()=='operating point' and int(fields['No. Points'])==1
    table=[l.split()for l in header.split('Variables:\n',1)[1].split('Binary:\n',1)[0].splitlines()]
    assert int(fields['No. Variables'])==len(table) and all(len(r)==3 for r in table)
    assert [r[0]for r in table]==list(map(str,range(len(table))))
    names=[r[1]for r in table];assert len(raw)-stop==8*len(names)
    assert len(base)==34 and len(set(base))==34
    explicit_scale_duplicate=names==[base[0],*base]
    assert explicit_scale_duplicate or (len(set(names))==len(names) and set(names)==set(base)), 'Unexpected OP names or duplicates'
    values=np.frombuffer(raw[stop:],dtype='<f8');assert np.isfinite(values).all()
    if explicit_scale_duplicate:assert raw[stop:stop+8]==raw[stop+8:stop+16], 'Duplicated native scale values disagree'
    records=[dict(name=row[1],unit=row[2],value=float(v))for row,v in zip(table,values,strict=True)]
    extras=set(names)-set(base);allowed_currents={n for n in vectors if n.startswith('@q.')}|{'i('+n+')'for n in vectors if n.startswith('@q.')}
    base_complete=set(base)<=set(names) and all(row['unit']=='voltage'for row in records if row['name']in base)
    scale_ok=not extras or (len(extras)==1 and names[0]in extras and names[0]in allowed_currents and table[0][2]=='current')
    all_zero=all(abs(row['value'])<({'voltage':1e-9,'current':1e-12}.get(row['unit'],0))for row in records)
    return dict(explicit_first_voltage_scale_duplicate=explicit_scale_duplicate,header=header,records=records,base_voltage_probes_complete=base_complete,extra_names=sorted(extras),additional_first_scale_is_saved_hbt_current=scale_ok,all_recorded_values_zero=all_zero,diagnostic_zero_op_verified=base_complete and scale_ok and all_zero,original_strict34_voltage_reader_still_failed=len(table)!=len(base),scope='Independent description of original native operating-point bytes. Does not change the frozen 34-column reader or acquisition acceptance.')
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,acquisition_accepted=False,no_new_native=True,original_failed_report_preserved=True,scope='Replay exact completed50ns442-probe physical845 diagnostic; describe original OP scale/units and all102HBT terminal ranges. Original1us acquisition remains failed. No transistor safety or PVT/fullPHY acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        selected=('diagnostic/actual-acquisition.raw','diagnostic/op.raw','diagnostic/circuit.cir','diagnostic/actual-acquisition.cir','diagnostic/parent865.spice','native.log','source/result.json','source/case/circuit.cir')
        old,proof=reports.restore_report('pll-divider-probes',38957588814,'df9024887fc1e5e7e0180cf006a1dc725e470d640ee36156b557eccf28b40aaa','20625c53dac60329af9fe015b046a89ed3480d3f1f37dcb23f4512d3418f3c15',OUT/'source',selected);r['source']=proof
        assert old['status']=='FAIL_OR_ERROR' and old['error']=='AssertionError()' and old['returncode']==0 and not old['diagnostics']
        assert old['source_head']=='0c035348f24f65fa6037a4752ebbc3252f57895d'
        case=OUT/'source/diagnostic';parent=(case/'parent865.spice').read_text();assert sha(case/'parent865.spice')=='8147a7cbae9d1a43b362733a3b52c218c5d04ef519cedf9abf35cd17ff27911e'
        rows=[l.lower().split()for l in parent.splitlines()if l.lower().startswith('x_')]
        hbts={w[0]:dict(terminals=w[1:5],nx=float(next(p.split('=')[1]for p in w if p.startswith('nx='))))for w in rows if len(w)>5 and w[5]=='npn13g2'};assert hbts==old['hbt_devices'] and len(hbts)==102
        prior=json.loads((OUT/'source/source/result.json').read_text());base=prior['preparation']['vectors'];assert len(base)==34
        body=(case/'circuit.cir').read_text();save_lines=[l for l in body.splitlines()if l.startswith('save ')];assert len(save_lines)==1;vectors=save_lines[0].split()[1:];assert len(vectors)==old['probe_count']==442
        original=(OUT/'source/source/case/circuit.cir').read_text()
        assert body.replace(save_lines[0],'save '+' '.join(base)).replace('.tran 3.125e-13 5e-08 0 3.125e-13','.tran 3.125e-13 1e-06 0 3.125e-13')==original
        op_raw=(case/'op.raw').read_bytes();mark=op_raw.find(b'Binary:\n',0,1048576);assert mark>=0
        r['operating_point_transport']=dict(raw_sha256=sha(case/'op.raw'),bytes=len(op_raw),header=op_raw[:mark+8].decode('ascii'),binary_bytes=len(op_raw)-mark-8)
        save()
        try:r['zero_source_op']=inspect_op(op_raw,base,vectors)
        except AssertionError as error:
            r['zero_source_op']=dict(status='UNVERIFIED_NATIVE_OP_FORMAT',diagnostic_zero_op_verified=False,error=repr(error),scope='Do not accept startup or device safety. Preserve failure and inspect recorded header; transient measurements are independent descriptions only.')
        save()
        positive=inspect_op(op_raw,base,vectors);assert positive['diagnostic_zero_op_verified'] and positive['explicit_first_voltage_scale_duplicate']
        faults=[op_raw[:-1],op_raw+b'x',op_raw.replace(b'v(clkp)',b'v(xbad)',1),op_raw[:mark+8]+np.array([.01],dtype='<f8').tobytes()+op_raw[mark+16:]]
        for bad in faults:
            try:verdict=inspect_op(bad,base,vectors)
            except AssertionError:continue
            assert not verdict['diagnostic_zero_op_verified'],'Malformed or nonzero OP accepted'
        r['op_duplicate_controls']=dict(actual_positive=True,negative=len(faults),duplicate_values_checked_byte_for_byte=True)
        r['reader_controls']=pll.self_test();r['original_op_reader_controls']=pll.pfd_op_controls()
        raw=(case/'actual-acquisition.raw').read_bytes();names,values,meta=pll.decode_prefix(raw)
        assert meta['header_matches_observed'] and meta['payload_has_only_complete_rows'] and np.isfinite(values).all()
        observed={n:values[:,i]for i,n in enumerate(names)};assert len(names)==len(vectors)+1 and len(observed)==len(names)
        data={'time':observed['time']};used={'time'}
        for name in vectors:
            allowed={name}if name.startswith('v(')else{name,'i('+name+')'};found=allowed&set(observed);assert len(found)==1
            actual=found.pop();assert actual not in used;used.add(actual);data[name]=observed[actual]
        assert used==set(observed);t=data['time'];assert t[0]==0 and abs(t[-1]-50e-9)<1e-15 and np.all(np.diff(t)>0) and np.diff(t).max()<=3.125e-13*1.00001
        r['capture']=dict(**meta,raw_sha256=sha(case/'actual-acquisition.raw'),start_s=float(t[0]),end_s=float(t[-1]),rows=len(t))
        measurements={}
        for name,d in hbts.items():
            c,b,e,sub=[data['v(xloop.'+n+')']for n in d['terminals']]
            ic=data['@q.xloop.'+name+'.qnpn13g2[ic]']/d['nx'];signals={'vce_v':c-e,'vbe_v':b-e,'vbc_v':b-c,'ic_per_emitter_a':ic,'collector_v':c,'base_v':b,'emitter_v':e,'substrate_v':sub};windows=[]
            for lo,hi in [(0.,50e-9),(5e-9,10e-9),(10e-9,20e-9),(40e-9,50e-9)]:
                mask=(t>=lo)&(t<=hi);assert mask.sum()>10
                windows.append(dict(interval_s=[lo,hi],signals={k:dict(minimum=float(v[mask].min()),maximum=float(v[mask].max()),mean=float(v[mask].mean()))for k,v in signals.items()}))
            measurements[name]=dict(nx=d['nx'],windows=windows)
        r['hbt_measurements']=measurements;r['terminal_signal_ranges']={n:[float(data[n][t>=40e-9].min()),float(data[n][t>=40e-9].max())]for n in base}
        r['hbt_devices']=hbts
        assert all(sha(OUT/'source'/p)==old['outputs'][p]for p in selected)
        r.update(status='COMPLETE_EXISTING_50NS_ALL102HBT_DIAGNOSTIC_REVIEW_NOT_ACQUISITION_OR_SAFETY_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:r.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
