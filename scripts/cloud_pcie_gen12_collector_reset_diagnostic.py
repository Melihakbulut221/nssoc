#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bounded public collector reset diagnostic; never complete CDC acceptance."""
import argparse,json,os,re,signal,sys,threading,traceback
from pathlib import Path
import cloud_pcie_gen12_record_cdc as c

GROUP='pcie-gen12-collector-reset-diagnostic'
MUTANT='collector_reset_POR_only'
TEST='partial_raw_batch_and_complete_record_epoch_reset'
MARKER='CDC_COLLECTOR_RESET_WITNESS '
ORDER=[(0,'wr'),(0,'rr'),(1,'wr'),(1,'rr')]
KEYS={'schema','polarity','domain','reset_port','reset_asserted','asserted_at_ps','observed_at_ps',
      'expected_boundary','expected_rd','prior','actual_boundary','actual_rd'}
PRIOR={'boundary','rd','oracle_start','oracle_rd','retired_records'}

def configuration(m,execute=False):
    c.authorization(m)
    d=m['collector_reset_diagnostic']
    assert d['group']==GROUP and d['depth']==4 and d['mutation']==MUTANT
    assert d['rtl_engines']==['icarus','verilator']and d['mapped_engine']=='icarus'
    assert d['positive_named_tests']==15 and d['synthesis_checks']==1 and d['compiled_fault_runs']==2
    assert type(d['authorized'])is bool
    assert not (m['native_execution_authorized'] and d['authorized']),'Mutually exclusive proof authorizations'
    if d['authorized']:
        receipt=d['review_receipt'];raw=(c.ROOT/receipt['path']).read_bytes()
        assert c.sha(raw)==receipt['sha256']
        proof=json.loads(raw)
        assert proof['status']=='CLEARED_FOR_ONE_TARGETED_COLLECTOR_RESET_DIAGNOSTIC'
        assert proof['protected_sources']==m['protected']
        assert re.fullmatch('[0-9a-f]{40}',proof['reviewed_source'])
    else:assert d['review_receipt']is None
    if execute:
        assert d['authorized'],'Targeted diagnostic not authorized'
        assert m['native_execution_authorized']is False,'Complete proof must remain disabled'
    return d

def validate_evidence(row,record,stdout,stderr,mutated=False):
    """Bind complete terminal streams/command identity before interpreting public samples."""
    assert row['top']==c.COMPOSED and row['depth']==4
    assert row['simulator']in ('icarus','verilator')
    assert row['compile_returncode']==0 and row['compiled_image']['bytes']>0
    assert record['returncode']==row['run_returncode']
    assert record['supervision_failure']is None
    assert record['process_group_cleanup']['remaining_live']==[]
    for key,raw in (('stdout',stdout),('stderr',stderr)):
        assert record[key+'_bytes']==len(raw)and record[key+'_sha256']==c.sha(raw)
    rows=[]
    for line in stdout.decode('utf-8').splitlines():
        if line.startswith(MARKER):
            item=json.loads(line[len(MARKER):]);assert set(item)==KEYS
            assert item['schema']=='public-collector-asserted-reset-v1'
            assert type(item['polarity'])is int and item['polarity']in (0,1)
            assert item['domain']in ('wr','rr')
            assert item['reset_port']=={'wr':'recovered_reset_i','rr':'common_reset_i'}[item['domain']]
            for key in ('reset_asserted','expected_boundary','expected_rd','actual_boundary','actual_rd'):
                assert type(item[key])is int and item[key]in (0,1)
            assert item['reset_asserted']==1 and item['expected_boundary']==item['expected_rd']==0
            for key in ('asserted_at_ps','observed_at_ps'):
                assert type(item[key])is int and item[key]>0
            assert item['observed_at_ps']-item['asserted_at_ps']==1100
            prior=item['prior'];assert set(prior)==PRIOR
            assert all(type(v)is int for v in prior.values())
            assert prior['boundary']==1 and prior['oracle_start']==0 and prior['retired_records']==2
            assert prior['rd']==prior['oracle_rd']and prior['rd']in (0,1)
            rows.append(item)
    tests=row['tests'];assert len(tests)==5 and {x['test']for x in tests}==set(c.TESTS[c.COMPOSED])
    if not mutated:
        assert row['mutation']is None and row['run_returncode']==0
        assert all(x['disposition']=='PASS'for x in tests)
        assert [(x['polarity'],x['domain'])for x in rows]==ORDER
        assert all(x['actual_boundary']==x['actual_rd']==0 for x in rows)
        assert all(a['observed_at_ps']<b['asserted_at_ps']for a,b in zip(rows,rows[1:]))
    else:
        assert row['mutation']==MUTANT and row['run_returncode']!=0 and row['mapped']is False
        hit=[x for x in tests if x['disposition']=='DETECTED_ASSERTION']
        assert len(hit)==1 and hit[0]['test']==TEST and hit[0]['error_type']=='AssertionError'
        assert all(x['disposition']=='FILTERED_NOT_EXECUTED'for x in tests if x is not hit[0])
        mutation=next(x for x in c.mutation_list()if x['name']==MUTANT)
        site=c.assertion_sites(mutation)[tuple(hit[0]['origin'])]
        assert site==hit[0]['assertion']and site.get('kind')=='explicit_public_collector_reset_guard'
        assert site['message']in hit[0]['error_msg']
        assert len(rows)==1 and (rows[0]['polarity'],rows[0]['domain'])==ORDER[0]
        actual=rows[0]
        if site['message']=='collector boundary survived coordinated reset':
            assert actual['actual_boundary']==1
        else:
            assert site['message']=='collector RD survived coordinated reset'
            assert actual['actual_boundary']==0 and actual['actual_rd']==1
    return dict(status='OBSERVED_MUTANT_PUBLIC_RESET_VIOLATION'if mutated else'PASS_PUBLIC_RESET_WITNESSES',
                samples=rows,stdout=dict(bytes=len(stdout),sha256=c.sha(stdout)),
                stderr=dict(bytes=len(stderr),sha256=c.sha(stderr)),
                generic_timeout_accepted=False,complete_CDC_accepted=False)

def collect(row,mutated=False):
    label=row['label']+'-simulate';s=c.supervisor()
    stdout=(s.TRACE/(label+'.stdout')).read_bytes()
    stderr=(s.TRACE/(label+'.stderr')).read_bytes()
    record_path=s.TRACE/(label+'.command.json')
    record=json.loads(record_path.read_text())
    assert record['label']==label
    proof=validate_evidence(row,record,stdout,stderr,mutated)
    proof['command_record']=c.file_info(record_path)
    proof['xml']=row['xml']
    c.save(c.OUT/'simulations'/row['label']/'public-reset-witness.json',proof)
    return proof

def configure_paths():
    c.GROUP=GROUP
    c.OUT=c.ROOT/'hw/soc/out/cloud-pcie-gen12-collector-reset-diagnostic'
    c.PUBLICATION=c.ROOT/'hw/soc/out/cloud-pcie-gen12-collector-reset-diagnostic-publication'

def native():
    m=c.pins();configuration(m,execute=True)
    s=c.supervisor();c.OUT.mkdir(parents=True,exist_ok=False)
    s.TRACE=c.OUT/'supervision';s.TRACE.mkdir()
    scratch=Path(os.environ['RUNNER_TEMP'])/('collector-reset-'+os.environ['GITHUB_RUN_ID'])
    scratch.mkdir(exist_ok=False)
    result=dict(status='RUNNING_TARGETED_COLLECTOR_RESET_DIAGNOSTIC',run=os.environ['GITHUB_RUN_ID'],
        attempt=os.environ['GITHUB_RUN_ATTEMPT'],source=os.environ['GITHUB_SHA'],source_pins=m,
        scope=c.SCOPE,engineering_accepted=False,complete_CDC_accepted=False,
        targeted_witness_accepted=False,rtl=[],mapped=[],synthesis=[],mutations=[])
    c.RESULT=result
    old={sig:signal.signal(sig,s.interrupted)for sig in (signal.SIGTERM,signal.SIGINT)}
    thread=threading.Thread(target=s.heartbeat,daemon=True);thread.start()
    try:
        assert os.environ['GITHUB_RUN_ATTEMPT']=='1','No implicit targeted retry'
        c.progress('targeted_exact_source_admission')
        c.command([sys.executable,c.ROOT/'scripts/wait_cloud_tested_source_release.py','--group',GROUP],
                  'exact-source-release-preflight',seconds=360)
        c.progress('exact_source_prerelease_verified_before_bootstrap')
        vendor=c.bootstrap(m,scratch);paths=c.source_paths(vendor)
        for sim in ('icarus','verilator'):
            row=c.simulate(c.COMPOSED,4,sim,paths,'target-positive-'+sim)
            row['public_reset_witness']=collect(row)
            result['rtl'].append(row);c.progress('targeted_RTL_positive_complete')
        netlist,syn=c.synthesize(c.COMPOSED,4,paths);result['synthesis'].append(syn)
        row=c.simulate(c.COMPOSED,4,'icarus',[netlist],'target-mapped-positive',mapped=True)
        row['public_reset_witness']=collect(row)
        result['mapped'].append(row);c.progress('targeted_mapped_positive_complete')
        assert sum(len(x['tests'])for x in result['rtl']+result['mapped'])==15
        mutation=next(x for x in c.mutation_list()if x['name']==MUTANT)
        altered_paths=c.source_paths(vendor,mutation)
        altered=c.OUT/'mutations'/MUTANT/Path(mutation['path']).name
        altered_hash=c.file_info(altered)
        result['compiled_mutation_source']=altered_hash
        for sim in ('icarus','verilator'):
            row=c.simulate(c.COMPOSED,4,sim,altered_paths,'target-mutant-'+sim,mutation)
            row['public_reset_witness']=collect(row,mutated=True)
            result['mutations'].append(row);c.progress('targeted_mutant_public_reset_violation')
        assert len(result['mutations'])==2 and c.file_info(altered)==altered_hash
        c.pins()
        result.update(status='PASS_TARGETED_PUBLIC_COLLECTOR_RESET_WITNESS',
                      targeted_witness_accepted=True)
    except BaseException as error:
        result.update(status='FAIL_OR_INTERRUPTED',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:
        cleanup=s.stop_process(s.ACTIVE);s.STOP.set();thread.join(timeout=2)
        for sig,fn in old.items():signal.signal(sig,fn)
        result['last_cleanup']=cleanup
        try:c.pins();result['terminal_source_pins_unchanged']=True
        except BaseException as error:
            result.update(status='FAIL_OR_INTERRUPTED',targeted_witness_accepted=False,source_recheck_error=repr(error))
        c.save(c.OUT/'result.json',result)
        s.event('collector_reset_terminal',status=result['status'],engineering_accepted=False)
        assert result.get('terminal_source_pins_unchanged')is True,'terminal source identity failed'

if __name__=='__main__':
    parser=argparse.ArgumentParser();modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--native',action='store_true')
    modes.add_argument('--publish',action='store_true')
    modes.add_argument('--log-result',action='store_true')
    args=parser.parse_args();configure_paths()
    if args.publish:c.publish()
    elif args.log_result:c.log_result()
    else:native()
