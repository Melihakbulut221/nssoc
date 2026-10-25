#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted parser/source/supervision controls; no RTL simulation in this program."""
import copy, json, os, traceback
import xml.etree.ElementTree as ET
from pathlib import Path
import cloud_pcie_gen12_record_cdc as c

def fixture(top,mutation=None):
    root=ET.Element('testsuites');suite=ET.SubElement(root,'testsuite',name='all')
    for name in c.TESTS[top]:
        case=ET.SubElement(suite,'testcase',name=name,classname='test_'+top,
                           file=str(c.BENCH/('test_'+top+'.py')),lineno='1',
                           time='1.0',sim_time_ns='1000.0',ratio_time='1000.0')
        if mutation and name!=mutation['test']:
            case.set('sim_time_ns','0.0');ET.SubElement(case,'skipped')
        elif mutation:ET.SubElement(case,'failure',error_type='AssertionError',error_msg='placeholder')
    return root

def encoded(tree):return ET.tostring(tree)
def case(root,name):return next(x for x in root.iter('testcase')if x.attrib['name']==name)

def controls():
    m=c.pins();c.authorization(m)
    c.OUT.mkdir(parents=True,exist_ok=False)
    s=c.supervisor();s.TRACE=c.OUT/'supervision-controls'
    result={'status':'RUNNING_CONTROLS_NO_RTL','run':os.environ['GITHUB_RUN_ID'],
            'source':os.environ['GITHUB_SHA'],'controls':{},'scope':c.SCOPE,
            'simulations_executed':False,'synthesis_executed':False}
    c.save(c.OUT/'controls.json',result)
    try:
        # The exact qualified 13 fixtures execute real harmless subprocesses.
        s.controls()
        original=json.loads((s.TRACE/'controls.json').read_text())
        assert original['status']=='PASS_RECORD_TELEMETRY_SOURCE_AND_SUPERVISION_CONTROLS_NO_RTL'
        assert len(original['controls'])==13 and all(original['controls'].values())
        result['qualified_supervision_controls']=original
        found={}
        def reject(name,fn):
            try:fn()
            except (AssertionError,ValueError,KeyError,ET.ParseError)as e:
                found[name]={'rejected':True,'exception':type(e).__name__}
            else:raise AssertionError('Control survived: '+name)
        for top in c.TESTS:
            good=fixture(top);rows=c.xml_review(encoded(good),top,0)
            assert len(rows)==len(c.TESTS[top])and all(x['disposition']=='PASS'for x in rows)
            found['positive_complete_'+top]={'passed':True}
        top=c.DIRECT;good=fixture(top)
        def altered(change):
            tree=copy.deepcopy(good);change(tree);return encoded(tree)
        reject('positive_nonzero_process',lambda:c.xml_review(encoded(good),top,1))
        reject('missing_named_test',lambda:c.xml_review(altered(lambda r:r[0].remove(r[0][0])),top,0))
        reject('duplicate_named_test',lambda:c.xml_review(altered(lambda r:r[0][1].set('name',r[0][0].get('name'))),top,0))
        reject('extra_named_test',lambda:c.xml_review(altered(lambda r:r[0].append(copy.deepcopy(r[0][0]))),top,0))
        reject('wrong_module',lambda:c.xml_review(altered(lambda r:r[0][0].set('classname','other')),top,0))
        reject('wrong_source',lambda:c.xml_review(altered(lambda r:r[0][0].set('file','/unreviewed/test.py')),top,0))
        reject('required_skip',lambda:c.xml_review(altered(lambda r:ET.SubElement(r[0][0],'skipped')),top,0))
        reject('positive_assertion_failure',lambda:c.xml_review(altered(lambda r:ET.SubElement(r[0][0],'failure',error_type='AssertionError')),top,0))
        reject('xml_error',lambda:c.xml_review(altered(lambda r:ET.SubElement(r[0][0],'error')),top,0))
        reject('zero_simulated_time',lambda:c.xml_review(altered(lambda r:r[0][0].set('sim_time_ns','0')),top,0))
        reject('unknown_testcase_child',lambda:c.xml_review(altered(lambda r:ET.SubElement(r[0][0],'unknown')),top,0))
        reject('malformed_xml',lambda:c.xml_review(b'<bad',top,0))
        reject('oversized_xml',lambda:c.xml_review(b' '*(2*1024*1024+1),top,0))
        reject('xml_entity',lambda:c.xml_review(b'<!DOCTYPE testsuites>'+encoded(good),top,0))
        mutations=c.mutation_list()
        assert len(mutations)==18 and set(c.MESSAGES)=={x['name']for x in mutations}
        for mutation in mutations:
            mt=Path(mutation['path']).stem;tree=fixture(mt,mutation)
            sites=c.assertion_sites(mutation);origin,site=next(iter(sites.items()))
            failure=case(tree,mutation['test']).find('failure')
            failure.set('error_msg',site['message']or'')
            log='Traceback (most recent call last):\n  File "%s", line %d, in checked\nAssertionError: %s\n'%(
                origin[0],origin[1],site['message']or'')
            rows=c.xml_review(encoded(tree),mt,2,mutation=mutation,log=log)
            assert sum(x['disposition']=='DETECTED_ASSERTION'for x in rows)==1
        found['all18_exact_assertion_classifier_positives']={'passed':True,'count':18}
        mutation=mutations[0];mt=Path(mutation['path']).stem;tree=fixture(mt,mutation)
        origin,site=next(iter(c.assertion_sites(mutation).items()))
        case(tree,mutation['test']).find('failure').set('error_msg',site['message'])
        log='  File "%s", line %d, in checked\n'%(origin[0],origin[1])
        def bad_mut(change,rc=2,trace=log):
            bad=copy.deepcopy(tree);change(bad)
            return lambda:c.xml_review(encoded(bad),mt,rc,mutation=mutation,log=trace)
        for error_type in ('ValueError','TypeError','SimFailure','RuntimeError'):
            reject('nonbehavioral_'+error_type,bad_mut(lambda r,t=error_type:case(r,mutation['test']).find('failure').set('error_type',t)))
        reject('initialization_failure',bad_mut(lambda r:case(r,mutation['test']).find('failure').attrib.clear()))
        reject('mutant_survived',bad_mut(lambda r:None,rc=0))
        reject('mutant_required_skipped',bad_mut(lambda r:ET.SubElement(case(r,mutation['test']),'skipped')))
        reject('mutant_missing_failure',bad_mut(lambda r:case(r,mutation['test']).remove(case(r,mutation['test']).find('failure'))))
        reject('mutant_extra_failure',bad_mut(lambda r:ET.SubElement(case(r,mutation['test']),'failure')))
        reject('filtered_test_executed',bad_mut(lambda r:r[0][1].remove(r[0][1].find('skipped'))))
        reject('missing_traceback',bad_mut(lambda r:None,trace='AssertionError: field or order mismatch'))
        reject('wrong_traceback_file',bad_mut(lambda r:None,trace='  File "/tmp/unreviewed.py", line 1, in fault\n'))
        reject('wrong_traceback_line',bad_mut(lambda r:None,trace='  File "%s", line 1, in fault\n'%origin[0]))
        reject('wrong_assertion_message',bad_mut(lambda r:case(r,mutation['test']).find('failure').set('error_msg','unrelated')))
        artifact=c.OUT/'tiny-compiled-fixture';artifact.write_bytes(b'nonempty harmless classifier fixture')
        c.compile_admission(0,artifact);found['compile_positive']={'passed':True}
        reject('compile_nonzero',lambda:c.compile_admission(1,artifact))
        reject('compile_missing_binary',lambda:c.compile_admission(0,c.OUT/'absent-binary'))
        artifact.write_bytes(b'')
        reject('compile_empty_binary',lambda:c.compile_admission(0,artifact))
        # Authorization is independent of source-control success; no DUT dispatch here.
        c.authorization(m)
        found['native_authorization_state_consistent']={'passed':True,'native_enabled':m['native_execution_authorized']}
        c.pins()
        result.update(status='PASS_CDC_CONTROLLER_SOURCE_AND_CLASSIFICATION_CONTROLS_NO_RTL',
                      controls=found,classification_control_count=len(found),terminal_source_pins_unchanged=True)
        assert len(found)==36
    except BaseException as error:
        result.update(status='FAIL_OR_INTERRUPTED',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:c.save(c.OUT/'controls.json',result)

if __name__=='__main__':controls()
