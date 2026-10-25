#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted target-specific admission controls; fixtures are not simulator evidence."""
import copy,json,tempfile,types
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock
import cloud_pcie_gen12_record_cdc as c
import cloud_pcie_gen12_collector_reset_diagnostic as d

def fixture(mutated=False,rd_guard=False):
    mutation=next(x for x in c.mutation_list()if x['name']==d.MUTANT)
    root=ET.Element('testsuites');suite=ET.SubElement(root,'testsuite',name='all')
    path=c.BENCH/('test_'+c.COMPOSED+'.py')
    origin,site=next((key,value)for key,value in c.assertion_sites(mutation).items()
        if value.get('kind')=='explicit_public_collector_reset_guard'and
        ('RD survived'in value['message'])==rd_guard)
    for name in c.TESTS[c.COMPOSED]:
        item=ET.SubElement(suite,'testcase',name=name,classname='test_'+c.COMPOSED,
            file=str(path),sim_time_ns='1000.0')
        if mutated and name!=d.TEST:
            item.set('sim_time_ns','0.0');ET.SubElement(item,'skipped')
        elif mutated:ET.SubElement(item,'failure',error_type='AssertionError',error_msg=site['message'])
    rc=2 if mutated else 0
    trace='  File "%s", line %d, in %s\n'%(*origin,d.TEST)
    tests=c.xml_review(ET.tostring(root),c.COMPOSED,rc,
        mutation=mutation if mutated else None,log=trace)
    row=dict(label='fixture-target',top=c.COMPOSED,depth=4,simulator='icarus',mapped=False,
        compile_returncode=0,compiled_image=dict(bytes=7,sha256=c.sha(b'fixture')),
        run_returncode=rc,mutation=d.MUTANT if mutated else None,tests=tests,
        xml=dict(bytes=len(ET.tostring(root)),sha256=c.sha(ET.tostring(root))))
    samples=[]
    for i,(polarity,domain)in enumerate(d.ORDER[:1]if mutated else d.ORDER):
        samples.append(dict(schema='public-collector-asserted-reset-v1',polarity=polarity,domain=domain,
            reset_port={'wr':'recovered_reset_i','rr':'common_reset_i'}[domain],reset_asserted=1,
            asserted_at_ps=100000+200000*i,observed_at_ps=101100+200000*i,
            expected_boundary=0,expected_rd=0,
            prior=dict(boundary=1,rd=1,oracle_start=0,oracle_rd=1,retired_records=2),
            actual_boundary=int(mutated and not rd_guard),actual_rd=int(mutated and rd_guard)))
    return row,samples

def streams(samples):
    return (''.join(d.MARKER+json.dumps(x,sort_keys=True)+'\n'for x in samples)).encode(),b''

def record(row,stdout,stderr):
    return dict(label=row['label']+'-simulate',returncode=row['run_returncode'],
        supervision_failure=None,process_group_cleanup=dict(remaining_live=[]),
        stdout_bytes=len(stdout),stdout_sha256=c.sha(stdout),
        stderr_bytes=len(stderr),stderr_sha256=c.sha(stderr))

def controls():
    d.configuration(c.pins())
    positives={};rejected={}
    def review(row,samples,mutated=False):
        out,err=streams(samples)
        return d.validate_evidence(row,record(row,out,err),out,err,mutated)
    for name,mutated,rd in [('complete_positive',False,False),
                            ('boundary_violation',True,False),('rd_violation',True,True)]:
        row,samples=fixture(mutated,rd);answer=review(row,samples,mutated)
        assert answer['generic_timeout_accepted']is False and answer['complete_CDC_accepted']is False
        positives[name]=True
    def reject(name,call):
        try:call()
        except (AssertionError,ValueError,KeyError,TypeError)as error:
            rejected[name]=dict(rejected=True,exception=type(error).__name__)
        else:raise AssertionError('Targeted diagnostic control survived: '+name)
    def altered(name,change,mutated=False):
        row,samples=fixture(mutated);change(row,samples)
        reject(name,lambda:review(row,samples,mutated))
    sample_changes=[
        ('wrong_schema',lambda x:x.update(schema='other')),
        ('wrong_polarity',lambda x:x.update(polarity=2)),
        ('wrong_domain',lambda x:x.update(domain='por')),
        ('wrong_port',lambda x:x.update(reset_port='por_ni')),
        ('reset_not_asserted',lambda x:x.update(reset_asserted=0)),
        ('wrong_interval',lambda x:x.update(observed_at_ps=x['observed_at_ps']+1)),
        ('expected_boundary_not_reset',lambda x:x.update(expected_boundary=1)),
        ('expected_RD_not_reset',lambda x:x.update(expected_rd=1)),
        ('priming_boundary_absent',lambda x:x['prior'].update(boundary=0)),
        ('priming_oracle_unacquired',lambda x:x['prior'].update(oracle_start=None)),
        ('priming_RD_mismatch',lambda x:x['prior'].update(oracle_rd=0)),
        ('priming_record_missing',lambda x:x['prior'].update(retired_records=1)),
    ]
    for name,change in sample_changes:
        altered(name,lambda r,s,change=change:change(s[0]))
    altered('missing_samples',lambda r,s:s.clear())
    altered('duplicate_sample',lambda r,s:s.__setitem__(1,copy.deepcopy(s[0])))
    altered('wrong_sample_order',lambda r,s:s.reverse())
    altered('unknown_sample_field',lambda r,s:s[0].update(extra='unbound'))
    altered('baseline_boundary_nonzero',lambda r,s:s[0].update(actual_boundary=1))
    altered('baseline_RD_nonzero',lambda r,s:s[0].update(actual_rd=1))
    altered('extra_sample',lambda r,s:s.append(copy.deepcopy(s[-1])))
    def hit(row):return next(x for x in row['tests']if x['disposition']=='DETECTED_ASSERTION')
    altered('no_fault_state_violation',lambda r,s:s[0].update(actual_boundary=0),True)
    altered('wrong_fault_message',lambda r,s:hit(r)['assertion'].update(message='unrelated'),True)
    altered('legacy_fault_kind',lambda r,s:hit(r)['assertion'].update(kind='field_failure'),True)
    altered('generic_timeout_origin',lambda r,s:hit(r).update(origin=[str(c.HARNESS.resolve()),104]),True)
    altered('unknown_conversion_error',lambda r,s:hit(r).update(error_type='ValueError'),True)
    row,samples=fixture();out=b'CDC_COLLECTOR_RESET_WITNESS {bad JSON}\n';err=b''
    reject('malformed_sample',lambda:d.validate_evidence(row,record(row,out,err),out,err))
    for name,change in [
        ('compile_nonzero',lambda r,q:r.update(compile_returncode=1)),
        ('mutant_returned_success',lambda r,q:(r.update(run_returncode=0),q.update(returncode=0))),
        ('supervision_failure',lambda r,q:q.update(supervision_failure='memory_sample_unavailable')),
        ('live_descendant',lambda r,q:q['process_group_cleanup'].update(remaining_live=[123])),
        ('stdout_digest',lambda r,q:q.update(stdout_sha256='0'*64)),
        ('stderr_size',lambda r,q:q.update(stderr_bytes=1)),
    ]:
        row,samples=fixture(True);out,err=streams(samples);q=record(row,out,err);change(row,q)
        reject(name,lambda row=row,q=q,out=out,err=err:d.validate_evidence(row,q,out,err,True))
    # Exercise the actual file/label/terminal-stream seam without any simulator.
    with tempfile.TemporaryDirectory(prefix='collector-reset-controls-')as temporary:
        root=Path(temporary);trace=root/'supervision';trace.mkdir()
        row,samples=fixture();out,err=streams(samples);q=record(row,out,err)
        label=row['label']+'-simulate'
        (trace/(label+'.stdout')).write_bytes(out);(trace/(label+'.stderr')).write_bytes(err)
        command_path=trace/(label+'.command.json');command_path.write_text(json.dumps(q))
        with mock.patch.object(c,'OUT',root),mock.patch.object(c,'supervisor',return_value=types.SimpleNamespace(TRACE=trace)):
            proof=d.collect(row)
            saved=json.loads((root/'simulations'/row['label']/'public-reset-witness.json').read_text())
            assert saved==proof and proof['command_record']==c.file_info(command_path)
            positives['actual_terminal_file_seam']=True
            q['label']='wrong-command';command_path.write_text(json.dumps(q))
            reject('wrong_command_label',lambda:d.collect(row))
    assert len(positives)==4 and len(rejected)==32
    return dict(status='PASS_TARGETED_PUBLIC_RESET_ADMISSION_CONTROLS_NO_RTL',
        positives=positives,rejected=rejected,simulations_executed=False,
        synthetic_fixtures_not_native_evidence=True)

if __name__=='__main__':print(json.dumps(controls(),indent=2,sort_keys=True))
