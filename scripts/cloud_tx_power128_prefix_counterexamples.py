#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Find irreversible original-gate counterexamples in an immutable TX prefix."""
import hashlib,json,os,re,traceback
from pathlib import Path
import numpy as np
import compare_cloud_routed_endpoints as reports
from cloud_tx_power128_prefix_rails import read_saved_prefix,controls as prefix_controls
from cloud_tx_output8088_power128_native import source_valid
from cloud_tx_p4_drive3_builder import START,UI,STOP,prestage_bias_currents,interface_screen
from cloud_tx_data_driver import original_bit_output_screen
from cloud_tx_chunked_op import commands,assemble_op
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-tx-power128-prefix-counterexamples'
def evaluate_samples(t, values, contract, transport):
    zeros = np.zeros_like(t)
    def volt(node):
        return zeros if node == '0' else values['v('+node+')']
    for name, expected in contract['rails'].items():
        assert np.max(np.abs(volt(name)-expected*np.clip(t/1e-9,0,1))) < 1e-9
    active = t >= START
    bias_current={}
    if contract.get('output_bias')=='native_res':
        for label,node,rail,probe in [('final_feed','finalfeed','avdd','vfinal_feed'),('tx_feed','txfeed','tvdd','vtx_feed')]:
            assert np.max(np.abs(volt(node)-volt(rail))) < 1e-12
            current=values[f'i({probe})'][active]
            bias_current[label]=dict(minimum=float(current.min()),median=float(np.median(current)),maximum=float(current.max()))
    if contract.get('clock_bias')=='native_res':
        for ref in contract.get('clock_refs',[dict(node='clkbias',feed='clkfeed',probe='vclkbias_feed')]):
            assert np.max(np.abs(volt(ref['feed'])-volt('avdd'))) < 1e-12
            current=values['i('+ref['probe']+')'][active]
            bias_current[ref['node']]=dict(minimum=float(current.min()),median=float(np.median(current)),maximum=float(current.max()))
    bias_current.update(prestage_bias_currents(t,volt,values,contract))
    devices = {}
    for name, row in contract['hbt'].items():
        c,b,e,_ = (volt(n) for n in row['terminals'])
        ce, be, current = c-e, b-e, values['@q.'+name+'.qnpn13g2[ic]']/row['nx']
        r = dict(min_post_vce_v=float(ce[active].min()),max_post_vce_v=float(ce[active].max()),
                 max_whole_abs_vce_v=float(abs(ce).max()),max_whole_abs_vbe_v=float(abs(be).max()),
                 max_whole_abs_ic_per_emitter_a=float(abs(current).max()))
        r['passed'] = r['min_post_vce_v'] >= .4 and r['max_whole_abs_vce_v'] <= 1.6 and r['max_whole_abs_vbe_v'] <= 1 and r['max_whole_abs_ic_per_emitter_a'] <= .003
        devices[name] = r
    mos = {}
    for name,row in contract['mos'].items():
        d,g,s,b = (volt(n) for n in row['terminals'])
        limit = 2.75 if row['model'].startswith('sg13_hv_') else 1.32
        peaks = {label:float(abs(v).max()) for label,v in [('vds',d-s),('vgs',g-s),('vgd',g-d)]}
        mos[name] = dict(peaks=peaks, limit_v=limit, passed=max(peaks.values())<=limit)
    signal = original_bit_output_screen(t,volt('op'),volt('on'),contract['bits'],START,UI)
    interfaces = {name:interface_screen(t,volt,contract,name) for name in ('cmos', 'final')}
    stride=4
    while stride<contract.get('streams',4):
        interfaces['level_'+str(stride)]=interface_screen(t,volt,contract,stride)
        stride*=2
    clocks={name:[float(((volt(name+'p')+volt(name+'n'))/2)[active].min()),float(((volt(name+'p')+volt(name+'n'))/2)[active].max())] for name in [c['name'] for c in contract.get('tree_plan',dict(clocks=[dict(name=n) for n in ('sa','sb','s')]))['clocks']]}
    return dict(capture_transport=transport,native_bias_current_a=bias_current, prestage_native_bias_current_a={k:v for k,v in bias_current.items() if k in contract.get('references',['ra','rb'])},clock_common_mode_range_v=clocks,zero_source_op=True,rows=len(t),coverage_s=[float(t[0]),float(t[-1])],
        signals=signal,hbt_devices=devices,mos_devices=mos,interfaces=interfaces,
        failed_hbts={n:r for n,r in devices.items() if not r['passed']},
        failed_mos={n:r for n,r in mos.items() if not r['passed']},
        all_engineering_gates_passed=signal['passed'] and all(r['passed'] for r in interfaces.values()) and
                                   all(r['passed'] for r in [*devices.values(),*mos.values()]))

def screen_prefix(t,values,contract,transport):
    assert START<float(t[-1])<STOP and not transport['full_capture']
    assert len(contract['bits'])==256
    n=int(np.floor((float(t[-1])-START)/UI))
    assert 0<n<256 and START+(n-1+.7)*UI<=float(t[-1])
    observed=dict(contract,bits=contract['bits'][:n])
    result=evaluate_samples(t,values,observed,transport)
    no_counterexample=result.pop('all_engineering_gates_passed')
    result.update(observed_full_bits=n,original_required_bits=256,
        observed_prefix_has_no_counterexamples=no_counterexample,full_capture=False,
        electrical_accepted=False,full_phy_accepted=False,
        source_bits_sha256=hashlib.sha256(bytes(contract['bits'])).hexdigest(),
        scope='Only first available complete original bits, unchanged phases/oracle/thresholds; all captured device samples. A failed subset refutes a full pass; a passing subset cannot establish one.')
    result['signals']['method']='Original unchanged output screen on the first '+str(n)+' of256 source bits only. No phase, oracle, latency or threshold change; not full capture acceptance.'
    times=START+(np.arange(n)[:,None]+np.asarray((.3,.5,.7)))*UI
    assert times.min()>=t[0]and times.max()<=t[-1]
    p=np.interp(times,t,values['v(op)']);q=np.interp(times,t,values['v(on)'])
    margins=(p-q)*(2*np.asarray(contract['bits'][:n])[:,None]-1)
    result['output_counterexamples']=[dict(bit_index=int(i),phase=float((.3,.5,.7)[j]),time_s=float(times[i,j]),
        expected_bit=int(contract['bits'][i]),positive_v=float(p[i,j]),negative_v=float(q[i,j]),margin_v=float(margins[i,j]),original_limit_v=.1)
        for i,j in zip(*np.where(margins<.1))]
    assert len(result['output_counterexamples'])==result['signals']['below_100mv_samples']
    result['failed_hbt_actual_terminals']={name:contract['hbt'][name]for name in result['failed_hbts']}
    result['failed_mos_actual_terminals']={name:contract['mos'][name]for name in result['failed_mos']}
    return result
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],no_new_simulation=True,
        full_capture=False,electrical_accepted=False,full_phy_accepted=False)
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        methods=json.loads((ROOT/'scripts/tx-power128-prefix-counterexample-methods.json').read_text())
        assert all(sha(ROOT/p)==v for p,v in methods.items())
        # The numerical review body is byte-for-byte the original full review.
        source=(ROOT/'scripts/cloud_tx_p4_drive3_builder.py').read_text()
        a=source.index('def review(');b=source.index('\ndef ',a+1);old=source[a:b].rstrip()+'\n'
        body=old[old.index('    zeros = np.zeros_like(t)'):]
        assert 'def evaluate_samples(t, values, contract, transport):\n'+body in Path(__file__).read_text()
        r['original_review_math_unchanged']=True;r['prefix_transport_controls']=prefix_controls()
        pin=json.loads((ROOT/'docs/evidence/tx-output8088-power128-first-continuations-20261021.json').read_text())['cases']['none'];spec=pin['descriptor']
        live=json.loads(__import__('subprocess').check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/'+str(spec['run'])]))
        import cloud_replay_onehot_logic as logic
        logic.OUT=OUT
        summary,digest,parts=logic.summary(spec['group'],live)
        assert digest==spec['summary_sha256']and parts==spec['parts_sha256']
        source_valid(spec,live,summary,methods['scripts/cloud_tx_output8088_power128_native.py'])
        chunks=sorted(n for n in summary['outputs']if re.fullmatch(r'work/op-part[0-9]{4}\.dat',n))
        assert len(chunks)==28,'All original native OP chunks are mandatory'
        names=['work/wave.raw','work/contract.json','work/bench.cir',*chunks]
        original,proof=reports.restore_report(spec['group'],spec['run'],spec['summary_sha256'],spec['parts_sha256'],
            OUT/'source',names)
        assert original==summary
        source_valid(spec,live,original,methods['scripts/cloud_tx_output8088_power128_native.py'])
        assert original['raw_prefix']==pin['report_excerpt']['raw_prefix']
        case=OUT/'source/work';raw=case/'wave.raw';contract=json.loads((case/'contract.json').read_text())
        hashes={n.removeprefix('work/'):sha(OUT/'source'/n)for n in names}
        assert all(hashes[n]==original['outputs']['work/'+n]for n in hashes)
        writes,specification=commands(contract['vectors'])
        assert ['work/'+p['file']for p in specification['parts']]==chunks
        actual_commands=[line for line in(case/'bench.cir').read_bytes().decode('latin-1').splitlines()if line.startswith('wrdata op-part')]
        assert actual_commands==writes,'OP chunks do not match the actual native saved deck'
        r['op_reassembly']=assemble_op(case,specification)
        assert r['op_reassembly']['vectors']==len(contract['vectors'])and r['op_reassembly']['chunks']==28
        assert not r['op_reassembly']['numeric_values_reformatted']and not r['op_reassembly']['omitted_vectors']
        op=np.loadtxt(case/'op.dat',skiprows=1)
        assert op.size==len(contract['vectors'])+1 and np.isfinite(op).all()and abs(op).max()<=1e-10
        t,values,transport=read_saved_prefix(raw,contract['vectors'],STOP,contract['condition']['step_ps']*1e-12,original['raw_prefix'])
        result=screen_prefix(t,values,contract,transport)
        assert all(sha(case/n)==v for n,v in hashes.items())and all(sha(ROOT/p)==v for p,v in methods.items())
        r.update(status='ORIGINAL_GATES_REFUTED_BY_IMMUTABLE_POWER128_PREFIX'if not result['observed_prefix_has_no_counterexamples']else'NO_COUNTEREXAMPLE_IN_OBSERVED_PREFIX_FULL_CAPTURE_STILL_REQUIRED',
            wave_source=proof,source_file_hashes=hashes,review=result,sources_unchanged=True,
            native_process_untouched=True,
            capture_retention='Complete original capture prefix and partial tail remain in immutable39630182787; remove only observer temporary copy. Full native continuation not cancelled or modified.')
        raw.unlink()
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
