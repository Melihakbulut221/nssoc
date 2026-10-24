#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Diagnose the completed rejected wire capture without a simulator rerun."""
import hashlib,json,os,shutil,tarfile
from pathlib import Path
import numpy as np
import run_cloud_tx_mux4 as tree
from cloud_tx_stream import read_streamed_wave
from cloud_chunked_results import verify_parts
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-tx-return64-diagnosis'

def safe(name):
    p=Path(name)
    assert name and not p.is_absolute()and '..'not in p.parts
    return p

def restore(receipt,result):
    summary=OUT/'original-summary.json';manifest=OUT/'original-parts.json'
    fetch(receipt['summary_url'],receipt['summary_sha256'],summary)
    fetch(receipt['parts_url'],receipt['parts_sha256'],manifest)
    report=json.loads(summary.read_text());parts=json.loads(manifest.read_text())
    assert parts==receipt['archive']
    assert report['source_head']==receipt['source_head']=='29aa2927dc3a16822ea8fad4cd0865de1f509623'
    assert report['status']=='COMPLETE_ACTUAL_FULL32_PHYSICAL_NATIVE_WAVEFORM_NOT_PHY_ACCEPTANCE'
    assert report['mode']=='wire'and report['variant']=='budget_high3_trim'and report['condition']=='nominal'and report['fault']=='none'
    assert report['returncode']==0 and report['source_unchanged']and not report['diagnostics']
    assert not report['electrical_screen_passed']and report['native_off_flags_count']==604
    assert report['model_sha256']==receipt['model_sha256']=='acde00f937c0bc576d608b51c079b984b8379900834c01d4cd74d7bfff34200f'
    download=OUT/'download';download.mkdir()
    base=receipt['parts_url'].rsplit('/',1)[0]+'/'
    for i,row in enumerate(parts['parts']):
        assert row['index']==i and row['name']==parts['stem']+'.tar.gz.part'+str(i).zfill(4)
        fetch(base+row['name'],row['sha256'],download/row['name'])
    result['archive_verification']=verify_parts(parts,download)
    packed=download/'complete.tar.gz'
    with packed.open('xb')as target:
        for row in parts['parts']:
            p=download/row['name']
            with p.open('rb')as stream:shutil.copyfileobj(stream,target)
            p.unlink()
    assert sha(packed)==parts['sha256']
    selected={'native/wave.raw','native/contract.json','native/op.dat','native/run.log','all-interfaces.json'}
    selected.add('source/cloud-tx-tree32-return64-assembly/wire96/tree1674-wire01.spice')
    actual={};seen=set();embedded=None
    with tarfile.open(packed,'r|gz')as archive:
        for member in archive:
            path=safe(member.name);assert path.parts[0]==parts['source_directory']
            assert member.name not in seen;seen.add(member.name)
            assert member.isdir()or member.isfile()
            if member.isdir():continue
            name=str(Path(*path.parts[1:]));stream=archive.extractfile(member)
            if name=='result.json':
                raw=stream.read();assert hashlib.sha256(raw).hexdigest()==receipt['summary_sha256'];embedded=json.loads(raw)
            elif name in selected:
                dest=OUT/'capture'/safe(name);dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb')as target:shutil.copyfileobj(stream,target)
                actual[name]=sha(dest)
            else:actual[name]=hashlib.file_digest(stream,'sha256').hexdigest()
    assert embedded==report and actual==report['outputs']
    assert selected<=set(actual)
    result['all_original_output_hashes_verified']=actual
    packed.unlink()
    return report

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,
        scope='Read-only diagnosis of already rejected tight700/422 native64umAVSS core wire capture. No native circuit rerun, phase fitting, source-bit change or gate relaxation.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        receipt=json.loads((ROOT/'docs/evidence/tx-return64-wire-rejection-20261017.json').read_text())
        result['source']=receipt;report=restore(receipt,result)
        native=OUT/'capture/native';contract=json.loads((native/'contract.json').read_text())
        assert len(contract['bits'])==256 and contract['streams']==32
        assert contract['source_bits_sha256']=='5dd4496031f00ffea20c2af8cd828d95a868960129829389125dc5055bdb6825'
        assert len(contract['hbt'])==604 and len(contract['mos'])==512
        assert contract['source_bits_sha256']==hashlib.sha256(bytes(contract['bits'])).hexdigest()
        # Reproduce every original scalar physical decision before any new diagnosis.
        reviewed=tree.review(native,contract)
        assert reviewed==report['review'],'Original all-device/interface/bit review changed'
        result['original_review_exactly_reproduced']=True
        t,values,transport=read_streamed_wave(native/'wave.raw',contract['vectors'],tree.STOP,contract['condition']['step_ps']*1e-12)
        result['capture_transport']=transport
        zeros=np.zeros_like(t)
        def v(n):return zeros if n=='0'else values['v('+n+')']
        maps=contract['interface_probes'];rows=[]
        interfaces=json.loads((OUT/'capture/all-interfaces.json').read_text())
        assert interfaces['modes']['wire']==maps
        for key in sorted(k[:-1]for k in maps if k.endswith('p')):
            stride=32 if key.startswith('d')else 2 if key in ('a','b')else int(key.split('_')[0][1:])
            offset=int(key[1:])if key.startswith('d')else ('a','b').index(key)if key in ('a','b')else int(key.split('_')[1])
            group='cmos'if stride==32 else'final'if stride==2 else'level_'+str(stride)
            indices=[i for i in range(256)if i%stride==offset];samples=[]
            assert len(maps[key+'p'])==len(maps[key+'n'])==3
            for i in indices:
                for phase in (.3,.5,.7):
                    at=tree.START+(i+phase)*tree.UI
                    for pn in maps[key+'p']:
                        for nn in maps[key+'n']:
                            pv,nv=(float(np.interp(at,t,v(n)))for n in (pn,nn))
                            samples.append(dict(bit_index=i,phase=phase,time_s=at,pnode=pn,nnode=nn,
                                margin_v=(pv-nv)*(2*contract['bits'][i]-1),common_mode_v=(pv+nv)/2))
            worst=min(samples,key=lambda x:x['margin_v'])
            rows.append(dict(input=key,stage=group,samples=len(samples),minimum_margin_v=worst['margin_v'],
                wrong_sign_samples=sum(x['margin_v']<=0 for x in samples),below_150mv_samples=sum(x['margin_v']<.15 for x in samples),
                common_mode_range_v=[min(x['common_mode_v']for x in samples),max(x['common_mode_v']for x in samples)],
                worst_sample=worst,actual_endpoints={suffix:interfaces['references'][key+suffix]['endpoints']for suffix in ('p','n')},
                original_phase_counts={str(p):dict(samples=sum(x['phase']==p for x in samples),wrong_sign_samples=sum(x['phase']==p and x['margin_v']<=0 for x in samples),below_150mv_samples=sum(x['phase']==p and x['margin_v']<.15 for x in samples))for p in (.3,.5,.7)}))
        assert len(rows)==62
        for stage,old in reviewed['interfaces'].items():
            selected=[x for x in rows if x['stage']==stage]
            assert sum(x['samples']for x in selected)==old['samples']
            assert sum(x['wrong_sign_samples']for x in selected)==old['wrong_sign_samples']
            assert sum(x['below_150mv_samples']for x in selected)==old['below_150mv_samples']
            assert min(x['minimum_margin_v']for x in selected)==old['minimum_margin_v']
        result['all62_differential_input_pairs']=rows
        failed={};active=t>=tree.START
        for name in reviewed['failed_hbts']:
            device=contract['hbt'][name];c,b,e,_=(v(n)for n in device['terminals']);ce=c-e;be=b-e
            current=values['@q.'+name+'.qnpn13g2[ic]']/device['nx']
            checks={'min_post_vce':active&(ce<.4),'max_whole_vce':abs(ce)>1.6,'max_whole_vbe':abs(be)>1.,'max_whole_current':abs(current)>.003}
            detail={}
            for kind,mask in checks.items():
                inds=np.flatnonzero(mask)
                if not len(inds):continue
                array=ce if 'vce'in kind else abs(be)if 'vbe'in kind else abs(current)
                peak=int(inds[np.argmin(array[inds])if kind=='min_post_vce'else np.argmax(abs(array[inds]))])
                detail[kind]=dict(violating_native_rows=len(inds),first_time_s=float(t[inds[0]]),last_time_s=float(t[inds[-1]]),
                    post_start_rows=int(np.count_nonzero(mask&active)),peak=dict(time_s=float(t[peak]),vc=float(c[peak]),vb=float(b[peak]),ve=float(e[peak]),vce=float(ce[peak]),vbe=float(be[peak]),ic_per_emitter_a=float(current[peak])))
            assert detail
            failed[name]=dict(device=device,original_measurement=reviewed['failed_hbts'][name],violation_times=detail)
        result['failed_devices_at_actual_native_times']=failed
        # Independently bind each actual clock port through native R connectivity
        # to the two selector HBT bases per leg. This reads the preserved model;
        # it does not alter stimuli, fit latency, move samples or declare acceptance.
        model=OUT/'capture/source/cloud-tx-tree32-return64-assembly/wire96/tree1674-wire01.spice'
        assert sha(model)==receipt['model_sha256']
        parent={}
        def root(n):
            parent.setdefault(n,n)
            while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
            return n
        resistor_count=0
        for line in model.read_text().lower().splitlines():
            f=line.split()
            if f and f[0].startswith('r'):
                assert len(f)==4 and float(f[3])>0
                parent[root(f[1])]=root(f[2]);resistor_count+=1
        assert resistor_count==114909
        def bare(n):return n.removeprefix('xtree.')
        def crossings(delta):
            ids=np.flatnonzero(delta[:-1]*delta[1:]<0)
            return [(float(t[i]+(t[i+1]-t[i])*(-delta[i])/(delta[i+1]-delta[i])),1 if delta[i+1]>delta[i]else -1)for i in ids if t[i]>=tree.START]
        clock_rows=[]
        for clock in contract['tree_plan']['clocks']:
            name=clock['name'];bases={}
            for suffix in ('p','n'):
                public=name+suffix;assert public in parent
                hits=[(k,row['terminals'][1])for k,row in contract['hbt'].items()if k.startswith('xtree.')and root(bare(row['terminals'][1]))==root(public)]
                assert len(hits)==2,(public,hits);bases[suffix]=hits
            public_delta=v(name+'p')-v(name+'n');public_edges=crossings(public_delta)
            legs=[]
            for ph,pn in bases['p']:
                for nh,nn in bases['n']:
                    delta=v(pn)-v(nn);actual=crossings(delta);matches=[];missing=[];used=set()
                    for ordinal,(edge,direction)in enumerate(public_edges):
                        hits=[(j,x)for j,x in enumerate(actual)if x[1]==direction and abs(x[0]-edge)<clock['period']/4]
                        if len(hits)!=1:missing.append(dict(public_ordinal=ordinal,time_s=edge,direction=direction,candidates=len(hits)));continue
                        j,x=hits[0];assert j not in used;used.add(j)
                        matches.append(dict(public_time_s=edge,base_time_s=x[0],direction=direction,delay_s=x[0]-edge))
                    legs.append(dict(positive_hbt=ph,negative_hbt=nh,positive_base=pn,negative_base=nn,public_edges=len(public_edges),base_edges=len(actual),matched=matches,unmatched_public=missing,unmatched_base=[x for i,x in enumerate(actual)if i not in used],minimum_delay_s=min((x['delay_s']for x in matches),default=None),maximum_delay_s=max((x['delay_s']for x in matches),default=None),differential_range_v=[float(delta[active].min()),float(delta[active].max())],common_mode_range_v=[float(((v(pn)+v(nn))/2)[active].min()),float(((v(pn)+v(nn))/2)[active].max())]))
            clock_rows.append(dict(clock=clock,actual_selector_bases=bases,legs=legs))
        assert len(clock_rows)==31 and sum(len(x['legs'])for x in clock_rows)==124
        result['native31_clock_ports_to124_selector_base_pairs']=clock_rows
        result['clock_diagnosis_scope']='Source public to actual native selector bases; unique same-direction crossings within fixed quarter-period window, with every missing/extra crossing retained. Diagnostic delays only, no phase fitting or altered original bit/device decisions.'
        assert len(failed)==6
        result['status']='COMPLETE_SOURCE_BOUND_WIRE_FAILURE_DIAGNOSIS_NOT_REPAIR_OR_ACCEPTANCE'
        # Native source/raw still exist in their immutable release; do not duplicate gigabytes in this small diagnostic receipt.
        del values,t
        (native/'wave.raw').unlink()
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'and p.name not in ('wave.raw','complete.tar.gz')and '.part'not in p.name}
        save();print(result['status'],flush=True)
if __name__=='__main__':main()
