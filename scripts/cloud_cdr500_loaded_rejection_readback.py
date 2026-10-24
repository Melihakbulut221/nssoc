#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read existing rejected PD500 native captures; never execute a simulator."""
import argparse,copy,hashlib,json,os,subprocess,sys,traceback
from pathlib import Path
import numpy as np
import cloud_cdr500_cleaned_loaded as loaded
import cloud_tx_stream as stream
import compare_cloud_routed_endpoints as reports
from cloud_verified_parts import controls as archive_controls
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
SOURCE='e4aca2e147acf55dfe9718da5a4a6e0471fbb2d5'
SOURCE_RUN=40081228425
RECEIPT='docs/evidence/cdr500-cleaned-loaded-nominal-rejection-diagnosis-20261024.json'
SELECTED=['native/wave.raw','native/original-bench.cir','native/bench.cir','native/native.log','planes/native-planes.json','composed/composition/pd500-mim-wire.spice','composed/composition/composition.json']

def check():
    m=json.loads((ROOT/'scripts/cdr500-loaded-rejection-readback-methods.json').read_text())
    for path,digest in m['protected'].items():assert sha(ROOT/path)==digest,path
    assert loaded.UI==125e-12 and loaded.START==2e-9 and loaded.STOP==34.25e-9 and loaded.STEP==.3125e-12
    return m

def validate_report(r,case):
    assert r['source_head']==SOURCE and r['case']==case and r['corner']=='nominal'
    assert r['status']=='REJECTED_WHOLE_MIM_PD500_LOADED' and r['returncode']==0 and not r['diagnostics']
    assert r['sources_unchanged'] and r['native_flags_verified']==124 and r['zero_source_op_maximum']==0
    assert not r['devices_passed'] and not r['data_passed'] and not r['phase_passed'] and not r['vi']['passed']
    assert not any(r[k]for k in ['full_phy_accepted','cdr_accepted','accepted','qualified_pex','closed_loop'])
    assert r['data_offset_s']==(-.15 if case.endswith('_early')else .15)*loaded.UI
    assert len(r['source_bits'])==256 and set(r['source_bits'])=={0,1}
    assert hashlib.sha256(bytes(r['source_bits'])).hexdigest()==r['source_bits_sha256']=='19651c736d6053f0fbb954fbc351fb9abcbf4f7d32d83f6034fd00e7e952f870'
    assert len(r['vectors'])==len(set(r['vectors']))==1151
    cap=r['raw_capture'];assert cap['header_rows']==113475 and cap['columns']==1152 and cap['complete_unmodified_rows']
    assert cap['raw_bytes']==1045823299 and cap['raw_sha256']==r['outputs']['native/wave.raw']
    assert abs(cap['end_s']-loaded.STOP)<1e-18 and cap['start_s']==0 and cap['max_step_s']<=loaded.STEP*1.00001
    assert len(r['devices'])==124 and len(r['mos_devices'])==50 and len(r['native_caps'])==7
    assert len(r['binding_controls']['rejected'])==13
    for p in SELECTED:assert len(r['outputs'][p])==64

def metadata_controls(r,case):
    trials=[]
    for label,path,value in [('wrong_source',('source_head',),'0'*40),('wrong_case',('case',),'nominal_late'if case=='nominal_early'else'nominal_early'),('native_failure',('returncode',),1),('missing_rows',('raw_capture','header_rows'),113474),('missing_columns',('raw_capture','columns'),1151),('changed_raw_hash',('raw_capture','raw_sha256'),'0'*64),('partial_capture',('raw_capture','complete_unmodified_rows'),False),('changed_bits',('source_bits_sha256',),'0'*64),('reclassified_acceptance',('status',),'PASS'),('changed_phase',('data_offset_s',),0)]:
        bad=copy.deepcopy(r);target=bad
        for key in path[:-1]:target=target[key]
        target[path[-1]]=value
        try:validate_report(bad,case)
        except (AssertionError,KeyError):trials.append(label)
        else:raise AssertionError('Accepted '+label)
    assert len(trials)==10
    return trials

def original_analysis_block():
    lines=(ROOT/'scripts/cloud_cdr500_cleaned_loaded.py').read_text().splitlines()
    start=next(i for i,line in enumerate(lines)if line.strip().startswith('def measure('))
    end=next(i for i,line in enumerate(lines)if "r['interface_observations']="in line)
    text='\n'.join(line[8:]for line in lines[start:end+1])+'\n'
    assert 'subprocess'not in text and 'exec('not in text and 'open('not in text and 'protected'not in text
    return text

def reproduce(r,bound,t,d):
    def v(n):
        n=bound['aliases'].get(n,n)
        return np.zeros(len(t))if n=='0'else d['v('+n+')']
    ns=dict(np=np,t=t,d=d,v=v,bound=bound,r={},devices=r['devices'],mos=r['mos_devices'],caps=r['native_caps'],bits=r['source_bits'],offset=r['data_offset_s'],constant=False,active=t>=loaded.START,START=loaded.START,UI=loaded.UI,STEP=loaded.STEP)
    block=original_analysis_block();exec(compile(block,'immutable-original-loaded-analysis','exec'),ns)
    actual=ns['r'];assert actual and all(actual[k]==r[k]for k in actual),'Original native rejection metrics do not reproduce exactly'
    return actual,ns,dict(sha256=hashlib.sha256(block.encode()).hexdigest(),compared_fields=sorted(actual),exact_equality=True)

def metric_controls(actual,r):
    trials=[]
    for name,path,value in [('phase_average',('phase_average_v',),0),('phase_gate',('phase_gate','minimum_signed_v'),.001),('device_result',('devices_passed',),True),('sampler_margin',('sampler_checks','a','minimum_signed_margin_v'),999),('sampler_delay',('sampler_checks','a','maximum_clock_to_valid_s'),0),('hbt_vce',('device_checks','xpd.xd0059','maximum_alltime_abs_vce_v'),0),('vi_current',('vi','mean_signed_current_a'),0),('tail_minimum',('minimum_active_stage_tail_current_a',next(iter(actual['minimum_active_stage_tail_current_a']))),0)]:
        bad=copy.deepcopy(r);target=bad
        for key in path[:-1]:target=target[key]
        target[path[-1]]=value
        try:assert all(actual[k]==bad[k]for k in actual)
        except AssertionError:trials.append(name)
        else:raise AssertionError('Accepted '+name)
    assert len(trials)==8
    return trials

def stats(t,x,mask):
    ids=np.flatnonzero(mask);assert len(ids)>1
    a=ids[int(np.argmin(x[ids]))];b=ids[int(np.argmax(x[ids]))]
    return dict(samples=len(ids),minimum=float(x[a]),minimum_time_s=float(t[a]),maximum=float(x[b]),maximum_time_s=float(t[b]),mean_time_weighted=float(np.trapezoid(x[ids],t[ids])/(t[ids[-1]]-t[ids[0]])))

def diagnose(r,bound,contract,t,d,ns):
    v=ns['v'];active=t>=loaded.START;startup=t<loaded.START;window=ns['window'];records={x['native_id']:x for x in contract['device_records']}
    def point(row):return bound['interface'].get(row['node'],'xpd.'+row['node'].lower())
    def sample(i,name):
        dev=r['devices'][name];vc,vb,ve,vs=[float(v(n)[i])for n in dev['nodes']]
        return dict(index=int(i),time_s=float(t[i]),collector_v=vc,base_v=vb,emitter_v=ve,body_v=vs,vce_v=vc-ve,vbe_v=vb-ve,collector_current_a=float(d['@q.'+name+'.qnpn13g2[ic]'][i]),avdd_port_v=float(v('avdd')[i]))
    stress={}
    for did in [59,60,111,112]:
        name='xpd.xd'+str(did).zfill(4);dev=r['devices'][name];vc,vb,ve,_=map(v,dev['nodes']);vce=vc-ve
        peaks={}
        for label,mask in [('all',np.ones(len(t),dtype=bool)),('startup_before2ns',startup),('active_from2ns',active)]:
            ids=np.flatnonzero(mask);index=ids[int(np.argmax(abs(vce[ids])))];bad=ids[abs(vce[ids])>1.6]
            peaks[label]=dict(peak=sample(index,name),over_1p6v_samples=len(bad),first_over_time_s=float(t[bad[0]])if len(bad)else None,last_over_time_s=float(t[bad[-1]])if len(bad)else None,stats_vce=stats(t,vce,mask))
        peak_index=peaks['all']['peak']['index'];spreads={}
        for terminal in records[did]['terminals']:
            if terminal['terminal']=='S':continue
            same=[dict(device=x['instance'],model=x['model'],terminal=a['terminal'],node=point(a),native_net=a['native_net'],voltage_v=float(v(point(a))[peak_index]))for x in records.values()for a in x['terminals']if a['native_cluster']==terminal['native_cluster']and a['native_net']==terminal['native_net']and a['terminal']not in ('S','BULK')]
            assert same
            spreads[terminal['terminal']]=dict(native_cluster=terminal['native_cluster'],native_net=terminal['native_net'],same_native_net_physical_terminal_values=same,spread_v=max(x['voltage_v']for x in same)-min(x['voltage_v']for x in same),interpretation='Actual distributed terminal voltages at the same native-net cluster; not an intrinsic resistance estimate.')
        stress[name]=dict(native_record=records[did],windows=peaks,same_native_net_at_global_peak=spreads)
    sampling={}
    for tag in 'abcd':
        expected=ns['expected'][tag];edges=ns['falling']if tag=='b'else ns['rising'];p=bound['aliases']['xpd.'+tag+'qp'];n=bound['aliases']['xpd.'+tag+'qn'];delta=v(p)-v(n);witness=[]
        for i,(bit,edge)in enumerate(zip(expected,edges,strict=True)):
            for phase in (.3,.6,.9):
                when=edge+phase*loaded.UI;signed=float(np.interp(when,t,delta))*(2*bit-1);j=int(np.searchsorted(t,when));assert 0<j<len(t)
                witness.append(dict(source_bit_index=i+1,expected_bit=bit,clock_edge_s=edge,phase_ui=phase,measurement_time_s=when,signed_margin_v=signed,bracketing_native_rows=[dict(index=k,time_s=float(t[k]),positive_v=float(v(p)[k]),negative_v=float(v(n)[k]))for k in [j-1,j]]))
        delays=r['sampler_checks'][tag]['clock_to_valid_by_bit_s'];worst=sorted(range(len(delays)),key=lambda i:delays[i],reverse=True)[:8]
        sampling[tag]=dict(positive_native_node=p,negative_native_node=n,probe_witnesses={leg:bound['probe_witnesses'][tag+'q'+leg]for leg in ('p','n')},original_gate=r['sampler_checks'][tag],worst_margin_witness=min(witness,key=lambda x:x['signed_margin_v']),worst_delay_witnesses=[dict(source_bit_index=i+1,expected_bit=expected[i],clock_edge_s=edges[i],clock_to_valid_s=delays[i],gate_limit_s=.3*loaded.UI)for i in worst],interpolation='Only the unchanged original gate interpolation at prescribed phases; adjacent original native rows are included. No fitted phase or retimed input.')
    vi={};currents={}
    for role,name in bound['vi_names'].items():
        current=d['@q.'+name+'.qnpn13g2[ic]'];currents[role]=current
        vi[role]=dict(device=name,nodes=r['devices'][name]['nodes'],native_collector_current_a=dict(active=stats(t,current,active),original_phase_window=stats(t,current,window)))
    sink_vin=currents['xxp']+currents['xyn'];sink_vip=currents['xxn']+currents['xyp'];difference=sink_vin-sink_vip
    vi['output_sink_paths']=dict(vin_roles=['xxp','xyn'],vip_roles=['xxn','xyp'],vin_collector_sum_a=stats(t,sink_vin,window),vip_collector_sum_a=stats(t,sink_vip,window),signed_difference_a=stats(t,difference,window),output_difference_v=stats(t,v('vip')-v('vin'),window),original_gate=r['vi'],scope='Native HBT collector currents only. No inferred emitter/base-current equality or complete node KCL/energy claim.')
    assert vi['output_sink_paths']['signed_difference_a']['mean_time_weighted']==r['vi']['mean_signed_current_a']
    return dict(hbt_stress=stress,samplers=sampling,vi_source_and_sink_observations=vi)

def publish(out,group):
    stem=group+'-'+os.environ['GITHUB_RUN_ID']+'-1';summary=ROOT/(stem+'.summary.json');summary.write_bytes((out/'result.json').read_bytes())
    subprocess.run([sys.executable,'scripts/cloud_chunked_results.py','--directory',str(out),'--stem',stem],cwd=ROOT,check=True)
    manifest=ROOT/(stem+'.parts.json');parts=json.loads(manifest.read_text())
    subprocess.run([sys.executable,'scripts/publish_cloud_results.py','--group',group,str(summary),str(manifest),*[p['name']for p in parts['parts']]],cwd=ROOT,check=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--case',choices=['nominal_early','nominal_late'],required=True);args=p.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ['GITHUB_RUN_ATTEMPT']=='1';method=check()
    group='cdr500-loaded-readback-'+args.case;out=ROOT/('cloud-'+group);out.mkdir(exist_ok=False)
    inputs=ROOT/('cloud-inputs-'+group);inputs.mkdir(exist_ok=False);reports.OUT=inputs
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],source_run=SOURCE_RUN,source_case=args.case,native_simulation_started=False,original_rejection_preserved=True,full_phy_accepted=False,cdr_accepted=False,qualified_pex=False,scope='Read-only full existing capture with exact original failed gates. Diagnostic success is not circuit acceptance.')
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        pin=json.loads((ROOT/RECEIPT).read_text());case=pin['cases'][args.case]
        jobs=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/'+str(SOURCE_RUN)+'/jobs?per_page=100']))['jobs'];job=next(j for j in jobs if j['id']==method['jobs'][args.case])
        assert job['name']=='loaded ('+args.case+')'and job['status']=='completed'and job['conclusion']=='failure'
        run=json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/runs/'+str(SOURCE_RUN)]));assert run['head_sha']==SOURCE and run['head_branch']=='codex/cdr500-floating-wire-diagnosis'
        result['source_job']={k:job[k]for k in ['id','name','status','conclusion','started_at','completed_at']}
        result['archive_controls']=archive_controls();assert len(result['archive_controls']['negative_controls'])==8
        original,proof=reports.restore_report('cdr500-cleaned-loaded-'+args.case,SOURCE_RUN,case['summary']['sha256'],case['parts']['sha256'],inputs/'capture',SELECTED)
        validate_report(original,args.case);result['metadata_controls']=metadata_controls(original,args.case);result['source_restore']=proof
        source=inputs/'capture';before={p:sha(source/p)for p in SELECTED};assert before=={p:original['outputs'][p]for p in SELECTED}
        contract=json.loads((source/'composed/composition/composition.json').read_text());planes=json.loads((source/'planes/native-planes.json').read_text());model=(source/'composed/composition/pd500-mim-wire.spice').read_text()
        bound=loaded.bind_native(model,contract,planes);assert bound==original['binding'];result['binding_controls']=loaded.binding_controls(model,contract,planes);assert len(result['binding_controls']['rejected'])==13
        for witness in pin['failed_device_native_binding']['devices']:
            record=next(d for d in contract['device_records']if d['native_id']==witness['native_id']);assert record==witness['native_record']
        result['native_selected_terminals']=[x['native_record']for x in pin['failed_device_native_binding']['devices']]
        t,d,capture=stream.read_streamed_wave(source/'native/wave.raw',original['vectors'],loaded.STOP,loaded.STEP);assert capture==original['raw_capture']
        result['full_capture']={k:v for k,v in capture.items()if k!='logical_vector_order'}
        actual,ns,analysis=reproduce(original,bound,t,d);result['original_gate_reproduction']=analysis;result['metric_controls']=metric_controls(actual,original)
        result['original_failed_metrics']=actual;result['diagnosis']=diagnose(original,bound,contract,t,d,ns)
        assert all(sha(source/p)==digest for p,digest in before.items());check()
        result.update(status='PASS_EXISTING_FULL_CAPTURE_REJECTION_REPRODUCED_WITH_NATIVE_STRESS_DIAGNOSIS_NOT_CIRCUIT_ACCEPTANCE',sources_unchanged=True,all_original_selected_bytes_unchanged=True,source_file_hashes=before)
    except BaseException as error:result.update(status='FAIL_READBACK',error=repr(error),traceback=traceback.format_exc());raise
    finally:
        save();publish(out,group);print(result['status'],flush=True)
if __name__=='__main__':main()
