#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted parser/source/supervision controls; no RTL simulation in this program."""
import ast, contextlib, copy, io, json, os, sys, traceback, types
from unittest import mock
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

def readonly_publication_controls(release):
    tree=ast.parse(Path(c.__file__).read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='publish')
    program=next(n.value.value for n in fn.body if isinstance(n,ast.Assign)and
                 any(isinstance(v,ast.Name)and v.id=='program'for v in n.targets))
    env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY=release.REPO,GITHUB_RUN_ID='123',
             GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='a'*40)
    tag,source=release.context(c.GROUP,env)
    info=dict(id=5,tag_name=tag,target_commitish=source,draft=False,prerelease=True,assets=[])
    ref=dict(ref='refs/tags/'+tag,object=dict(type='commit',sha=source))
    def exercise(code,body,reference):
        calls=[]
        def read(path,missing=False):
            calls.append(path)
            return copy.deepcopy(body if path.startswith('releases/')else reference)
        def legacy(*args):raise AssertionError('Legacy release creation path must never execute')
        migration=types.SimpleNamespace(release=legacy)
        def publish(group,paths):
            assert group==c.GROUP and paths==['fixture.summary.json','fixture.parts.json']
            migration.release(tag)
            return dict(tag=tag,assets=[dict(name=p)for p in paths])
        guard=types.SimpleNamespace(context=release.context,api=read,validate_release=release.validate_release)
        oldpath=list(sys.path)
        try:
            with mock.patch.dict(os.environ,env),mock.patch.object(sys,'argv',
                 ['fixture',str(c.ROOT/'scripts'),c.GROUP,'fixture.summary.json','fixture.parts.json']),\
                 mock.patch.dict(sys.modules,{'ensure_cloud_tested_source_release':guard,
                  'migrate_outputs_to_cloud':migration,'publish_cloud_results':types.SimpleNamespace(publish_results=publish)}),\
                 contextlib.redirect_stdout(io.StringIO())as output:
                exec(compile(code,'reviewed-publication-program','exec'),{})
            result=json.loads(output.getvalue())
            assert result['tag']==tag and len(calls)==4
        finally:sys.path[:]=oldpath
    exercise(program,info,ref)
    rejected=[]
    cases=[('legacy-create-path',program.replace('migration.release=readonly_release','pass'),info,ref)]
    bad=copy.deepcopy(info);bad['target_commitish']='b'*40
    cases.append(('wrong-release-source',program,bad,ref))
    badref=copy.deepcopy(ref);badref['object']['sha']='b'*40
    cases.append(('wrong-tag-object',program,info,badref))
    for name,code,body,reference in cases:
        try:exercise(code,body,reference)
        except AssertionError:rejected.append(name)
        else:raise AssertionError('Read-only publication control survived: '+name)
    assert len(rejected)==3
    return dict(actual_extracted_program_positive=True,rejected=rejected,network_or_upload_executed=False)

def collector_reset_witness_controls():
    """Real pinned source sites and strict source/XML refusal fixtures; no RTL."""
    name='collector_reset_POR_only'
    mutation=next(x for x in c.mutation_list()if x['name']==name)
    path=c.BENCH/('test_'+c.COMPOSED+'.py')
    function=next(n for n in ast.parse(path.read_text()).body
                  if isinstance(n,ast.AsyncFunctionDef)and n.name==mutation['test'])
    guards=[n for n in ast.walk(function)if isinstance(n,ast.Assert)and
            isinstance(n.msg,ast.Constant)and n.msg.value in c.COLLECTOR_RESET_GUARDS]
    assert len(guards)==2 and {n.msg.value for n in guards}==set(c.COLLECTOR_RESET_GUARDS)
    sites=c.assertion_sites(mutation)
    explicit={key:site for key,site in sites.items()
              if site.get('kind')=='explicit_public_collector_reset_guard'}
    assert set(explicit)=={(str(path.resolve()),n.lineno)for n in guards}
    positives=[];rejected={}
    def reject(label,call):
        try:call()
        except (AssertionError,ValueError,KeyError,ET.ParseError)as error:
            rejected[label]={'rejected':True,'exception':type(error).__name__}
        else:raise AssertionError('Collector reset control survived: '+label)
    def require_source(text,mutant=name):
        assert c.assertion_site(ast.parse(text).body[0],mutant)is not None
    for node in guards:
        origin=(str(path.resolve()),node.lineno);message=node.msg.value
        site=c.assertion_site(node,name)
        assert site['kind']=='explicit_public_collector_reset_guard'
        actual=fixture(c.COMPOSED,mutation)
        case(actual,mutation['test']).find('failure').set('error_msg',message)
        log='  File "%s", line %d, in %s\n'%(*origin,mutation['test'])
        rows=c.xml_review(encoded(actual),c.COMPOSED,2,mutation=mutation,log=log)
        assert sum(x['disposition']=='DETECTED_ASSERTION'for x in rows)==1
        positives.append(dict(source=list(origin),message=message,expression=ast.unparse(node.test)))
        def bad_xml(change,trace=log,rc=2):
            altered=copy.deepcopy(actual);change(altered)
            return lambda:c.xml_review(encoded(altered),c.COMPOSED,rc,mutation=mutation,log=trace)
        prefix='boundary'if 'boundary'in message else'rd'
        reject(prefix+'_wrong_message',bad_xml(lambda r:
            case(r,mutation['test']).find('failure').set('error_msg','unrelated reset failure')))
        reject(prefix+'_unknown_conversion',bad_xml(lambda r:
            case(r,mutation['test']).find('failure').set('error_type','ValueError')))
        reject(prefix+'_wrong_file',bad_xml(lambda r:None,
            trace='  File "/tmp/unreviewed.py", line %d, in reset\n'%origin[1]))
        reject(prefix+'_wrong_line',bad_xml(lambda r:None,
            trace='  File "%s", line 1, in reset\n'%origin[0]))
        reject(prefix+'_zero_returncode',bad_xml(lambda r:None,rc=0))
        reject(prefix+'_qualified_frame_not_origin',bad_xml(lambda r:None,
            trace=log+'  File "%s", line 104, in until\n'%c.HARNESS.resolve()))
        assert c.assertion_site(ast.parse(
            'assert (('+c.COLLECTOR_RESET_GUARDS[message]+')), '+repr(message)).body[0],name)==site
    for label,text in [
        ('boundary_wrong_port',"assert link.value('record_valid_o') == 0, 'collector boundary survived coordinated reset'"),
        ('boundary_wrong_operator',"assert link.value('boundary_valid_o') != 0, 'collector boundary survived coordinated reset'"),
        ('boundary_wrong_value',"assert link.value('boundary_valid_o') == 1, 'collector boundary survived coordinated reset'"),
        ('boundary_negated',"assert not (link.value('boundary_valid_o') == 0), 'collector boundary survived coordinated reset'"),
        ('boundary_dynamic_message',"assert link.value('boundary_valid_o') == 0, message"),
        ('boundary_wrong_literal',"assert link.value('boundary_valid_o') == 0, 'unrelated boundary failure'"),
        ('rd_wrong_port',"assert link.value('boundary_valid_o') == 0, 'collector RD survived coordinated reset'"),
        ('rd_wrong_operator',"assert link.value('rd_o') != 0, 'collector RD survived coordinated reset'"),
        ('rd_wrong_value',"assert link.value('rd_o') == 1, 'collector RD survived coordinated reset'"),
        ('rd_dynamic_message',"assert link.value('rd_o') == 0, message"),
        ('raise_not_assert',"raise AssertionError('collector boundary survived coordinated reset')"),
        ('non_assert_node',"link.value('boundary_valid_o') == 0"),
        ('generic_timeout',"raise AssertionError('bounded public-port scenario timeout')")]:
        reject('source_'+label,lambda text=text:require_source(text))
    for node in guards:
        for other in c.mutation_list():
            if other['name']!=name:
                assert c.assertion_site(ast.parse(ast.unparse(node)).body[0],other['name'])is None,other['name']
    for node in ast.walk(function):
        if isinstance(node,ast.Assert)and isinstance(node.msg,ast.Constant)and isinstance(node.msg.value,str):
            if node.msg.value not in c.COLLECTOR_RESET_GUARDS:
                assert c.assertion_site(node,name)is None,(node.lineno,node.msg.value)
    timeout=next(n for n in ast.walk(ast.parse(c.HARNESS.read_text()))if isinstance(n,ast.Raise)and
                 isinstance(n.exc,ast.Call)and isinstance(n.exc.func,ast.Name)and
                 n.exc.func.id=='AssertionError'and n.exc.args and
                 isinstance(n.exc.args[0],ast.Constant)and
                 n.exc.args[0].value=='bounded public-port scenario timeout')
    assert c.assertion_site(timeout,name)is None
    assert (str(c.HARNESS.resolve()),timeout.lineno)not in sites
    reject('xml_generic_timeout',lambda:c.xml_review(encoded(actual),c.COMPOSED,2,
        mutation=mutation,log='  File "%s", line %d, in until\n'%(c.HARNESS.resolve(),timeout.lineno)))
    assert len(positives)==2 and len(rejected)==26
    return dict(status='PASS_LITERAL_PUBLIC_COLLECTOR_RESET_GUARD_CONTROLS_NO_RTL',
                positives=positives,rejected=rejected,wrong_mutant_refusals=34,
                priming_assertions_unqualified=True,generic_timeout_unqualified=True,
                actual_guard_sites=[list(key)for key in explicit],simulations_executed=False)

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
        import ensure_cloud_tested_source_release as release
        import wait_cloud_tested_source_release as wait
        release_proof=release.controls();wait_proof=wait.controls()
        assert len(release_proof['rejected'])==17
        assert wait_proof['status']=='PASS_READ_ONLY_RELEASE_WAIT_CONTROLS'
        assert len(wait_proof['positive_cases'])==3 and len(wait_proof['rejected'])==4
        archive=c.command([os.sys.executable,c.ROOT/'scripts/cloud_chunked_results.py','--self-test'],
                          'publication-archive-fixture',seconds=120)
        archive_proof=json.loads(archive.stdout)
        assert archive_proof['positive_roundtrip']and archive_proof['negative_controls']==6
        result['publication_controls']={'release':release_proof,'wait':wait_proof,'archive':archive_proof,
                                        'readonly_program':readonly_publication_controls(release)}
        assert original['status']=='PASS_RECORD_TELEMETRY_SOURCE_AND_SUPERVISION_CONTROLS_NO_RTL'
        assert len(original['controls'])==13 and all(original['controls'].values())
        result['qualified_supervision_controls']=original
        import check_pcie_live_memory_sampler as memory_controls
        result['bounded_memory_sampler_controls']=memory_controls.controls(s)
        c.save(c.OUT/'controls.json',result)
        result['collector_reset_witness_controls']=collector_reset_witness_controls()
        import check_pcie_gen12_collector_reset_diagnostic as targeted
        result['collector_reset_targeted_controls']=targeted.controls()
        c.save(c.OUT/'controls.json',result)
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
        # Exercise the actual pinned harness raise through the same XML classifier.
        raised=next(x for x in mutations if x['name']=='hide_loss')
        rt=Path(raised['path']).stem
        raised_sites={key:value for key,value in c.assertion_sites(raised).items()
                      if value.get('kind')=='explicit_literal_AssertionError_raise'}
        assert len(raised_sites)==1
        ro,rs=next(iter(raised_sites.items()))
        assert ro[0]==str(c.HARNESS.resolve())
        raise_tree=fixture(rt,raised)
        case(raise_tree,raised['test']).find('failure').set('error_msg',rs['message'])
        raise_trace='  File "%s", line %d, in until\n'%(ro[0],ro[1])
        rows=c.xml_review(encoded(raise_tree),rt,2,mutation=raised,log=raise_trace)
        assert sum(x['disposition']=='DETECTED_ASSERTION'for x in rows)==1
        found['qualified_literal_raise_positive']={'passed':True,'source':list(ro)}
        def bad_raise(change,trace=raise_trace):
            bad=copy.deepcopy(raise_tree);change(bad)
            return lambda:c.xml_review(encoded(bad),rt,2,mutation=raised,log=trace)
        reject('raised_nonbehavioral_RuntimeError',bad_raise(lambda r:
            case(r,raised['test']).find('failure').set('error_type','RuntimeError')))
        reject('raised_wrong_message',bad_raise(lambda r:
            case(r,raised['test']).find('failure').set('error_msg','unrelated timeout')))
        reject('raised_unqualified_line',bad_raise(lambda r:None,
               trace='  File "%s", line 1, in until\n'%ro[0]))
        reject('raised_unqualified_file',bad_raise(lambda r:None,
               trace='  File "/tmp/unreviewed.py", line %d, in until\n'%ro[1]))
        def require_raise_site(source):
            node=ast.parse(source).body[0]
            assert c.assertion_site(node,raised['name'])is not None
        for name,source in [
            ('wrong_type',"raise RuntimeError('bounded public-port scenario timeout')"),
            ('wrong_message',"raise AssertionError('unrelated timeout')"),
            ('dynamic_message',"raise AssertionError(message)"),
            ('reraise','raise'),
            ('attribute_call',"raise errors.AssertionError('bounded public-port scenario timeout')"),
            ('keyword',"raise AssertionError(message='bounded public-port scenario timeout')"),
            ('chained_cause',"raise AssertionError('bounded public-port scenario timeout') from error"),
            ('extra_argument',"raise AssertionError('bounded public-port scenario timeout', other)")]:
            reject('source_raise_'+name,lambda source=source:require_raise_site(source))
        # Actual reset source predicates must be admitted independent of ast.unparse
        # parentheses. Keep the pinned harness and both expressions byte-identical.
        reset_nodes=next(n for n in ast.walk(ast.parse(c.HARNESS.read_text()))
                         if isinstance(n,ast.AsyncFunctionDef)and n.name=='reset')
        direct_assertions=[n for n in reset_nodes.body if isinstance(n,ast.Assert)]
        assert [n.lineno for n in direct_assertions]==[206,207,216]
        post_reset_assertion=direct_assertions[2]
        direct_assertions=direct_assertions[:2]
        reset_proofs=[]
        for reset_name in ('ignore_write_reset','ignore_read_reset'):
            reset_mutation=next(x for x in mutations if x['name']==reset_name)
            reset_sites=c.assertion_sites(reset_mutation)
            assert (str(c.HARNESS.resolve()),216)not in reset_sites
            assert c.assertion_site(post_reset_assertion,reset_name)is None
            for node in direct_assertions:
                reset_origin=(str(c.HARNESS.resolve()),node.lineno)
                assert reset_origin in reset_sites
                assert c.assertion_site(node,reset_name)['message']is None
                reset_xml=fixture(c.DIRECT,reset_mutation)
                case(reset_xml,reset_mutation['test']).find('failure').set('error_msg','')
                reset_log='  File "%s", line %d, in reset\n'%reset_origin
                rows=c.xml_review(encoded(reset_xml),c.DIRECT,2,
                                  mutation=reset_mutation,log=reset_log)
                assert sum(x['disposition']=='DETECTED_ASSERTION'for x in rows)==1
                reset_proofs.append(dict(mutation=reset_name,source=list(reset_origin),
                                         expression=ast.unparse(node.test)))
        found['actual_reset_predicates_both_mutants']={'passed':True,'sites':reset_proofs,
            'unlisted_post_reset_assertion_line':216,'unlisted_assertion_remains_unqualified':True}
        for reset_name in ('ignore_write_reset','ignore_read_reset'):
            for text in [
                "assert not self.value('rv') and not self.value('wa')",
                "assert (not self.value('rv')) and (not self.value('wa'))",
                "assert (((not self.value('rv')) and (not self.value('wa'))))",
                "assert (self.output()) == ((0,) * 5)"]:
                assert c.assertion_site(ast.parse(text).body[0],reset_name)is not None
        found['reset_equivalent_parentheses']={'passed':True,'cases':8}
        def require_reset_site(text):
            assert c.assertion_site(ast.parse(text).body[0],'ignore_read_reset')is not None
        for name,text in [
            ('operator',"assert not self.value('rv') or not self.value('wa')"),
            ('read_port',"assert not self.value('rn') and not self.value('wa')"),
            ('write_port',"assert not self.value('rv') and not self.value('wn')"),
            ('read_negation',"assert self.value('rv') and not self.value('wa')"),
            ('write_negation',"assert not self.value('rv') and self.value('wa')"),
            ('output_operator',"assert self.output() != (0,) * 5"),
            ('output_width',"assert self.output() == (0,) * 4"),
            ('non_assert_node',"not self.value('rv') and not self.value('wa')")]:
            reject('reset_predicate_'+name,lambda text=text:require_reset_site(text))
        reset_mutation=next(x for x in mutations if x['name']=='ignore_read_reset')
        reset_xml=fixture(c.DIRECT,reset_mutation)
        case(reset_xml,reset_mutation['test']).find('failure').set('error_msg','')
        reset_origin=(str(c.HARNESS.resolve()),206)
        reset_log='  File "%s", line %d, in reset\n'%reset_origin
        def bad_reset(change,trace=reset_log,rc=2):
            bad=copy.deepcopy(reset_xml);change(bad)
            return lambda:c.xml_review(encoded(bad),c.DIRECT,rc,
                                       mutation=reset_mutation,log=trace)
        reject('reset_xml_unknown_conversion',bad_reset(lambda r:
            case(r,reset_mutation['test']).find('failure').set('error_type','ValueError')))
        reject('reset_xml_wrong_line',bad_reset(lambda r:None,
            trace='  File "%s", line 1, in reset\n'%reset_origin[0]))
        reject('reset_xml_wrong_file',bad_reset(lambda r:None,
            trace='  File "/tmp/unreviewed.py", line 206, in reset\n'))
        reject('reset_xml_success_returncode',bad_reset(lambda r:None,rc=0))
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
        assert len(found)==63
    except BaseException as error:
        result.update(status='FAIL_OR_INTERRUPTED',error=repr(error),traceback=traceback.format_exc())
        raise
    finally:c.save(c.OUT/'controls.json',result)

if __name__=='__main__':controls()
