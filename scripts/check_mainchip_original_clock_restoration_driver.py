#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source/control fixtures; no ODB restore, native CAD, or rerouting."""
import ast,base64,copy,hashlib,json,os,tempfile,traceback
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import mainchip_original_clock_restoration as c
import mainchip_original_clock_drc as drc
import cloud_mainchip_original_clock_restoration as driver
OUT=c.ROOT/'cloud-mainchip-original-clock-restoration-controls'

class SwigPyObject:
    """Synthetic opaque return reproduces the actual unsupported set surface."""
    pass

class Category:
    def __init__(self,name=drc.CATEGORY,count=0,children=None,maximum=10000,source='DRT',declared=None):
        self.name=name;self.count=count;self.children=[]if children is None else children
        self.maximum=maximum;self.source=source;self.declared=declared
    def getName(self):return self.name
    def getSource(self):return self.source
    def getMarkers(self):return list(range(self.count))
    def getMarkerCategories(self):return self.children
    def getMaxMarkers(self):return self.maximum
    def getMarkerCount(self):
        return self.declared if self.declared is not None else self.count+sum(c.getMarkerCount()for c in self.children)
    def getAllMarkers(self):return SwigPyObject()
    def serialized(self):
        node=dict(description='',source=self.source,max_markers=str(self.maximum))
        if self.children:node['category']={child.getName():child.serialized()for child in self.children}
        if self.count:node['violations']=[dict(visited='false',visible='true',waived='false',shape='',sources='')for _ in range(self.count)]
        return node
    def writeJSON(self,path):Path(path).write_text(json.dumps({self.name:self.serialized()}))
    def writeTR(self,path):
        Path(path).write_bytes(b''.join(b'violation type: test\n\tsrcs:\n\tbbox = (0, 0) - (1, 1) on Layer M1\n'for _ in range(self.getMarkerCount())))


def marker_controls():
    """Hosted synthetic API/schema fixtures; no actual odb module or native files."""
    positive=[];negative=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,TypeError,FileNotFoundError):negative.append(name)
        else:raise AssertionError('marker control accepted '+name)
    encode=lambda value:json.dumps(value).encode()
    cat=Category(count=1,children=[Category('Short',2),Category('Spacing',2)])
    tree={drc.CATEGORY:cat.serialized()}
    native=drc.marker_tree(cat)
    assert native['marker_count']==5
    proof=drc.bind_serialized_markers(native,encode(tree))
    assert proof['marker_count']==5 and proof['category_count']==3
    positive.append('complete_native_and_serialized_direct_recursive_counts')
    zero=Category()
    assert drc.bind_serialized_markers(drc.marker_tree(zero),encode({drc.CATEGORY:zero.serialized()}))['marker_count']==0
    positive.append('explicit_zero_category_with_absent_violations')
    repeated=Category(children=[Category('A',children=[Category('Same',1)]),Category('B',children=[Category('Same',2)])])
    p=drc.bind_serialized_markers(drc.marker_tree(repeated),encode({drc.CATEGORY:repeated.serialized()}))
    assert p['marker_count']==3 and p['category_count']==5
    positive.append('same_child_name_in_distinct_category_paths')
    reverse=copy.deepcopy(tree);reverse[drc.CATEGORY]['category']=dict(reversed(list(reverse[drc.CATEGORY]['category'].items())))
    assert drc.bind_serialized_markers(native,encode(reverse))['marker_count']==5
    positive.append('category_order_does_not_change_owned_census')
    old=c.regular(c.ROOT/'docs/evidence/mainchip-original-clock-first-native-failed-drc-source-20261025.py').read_bytes()
    assert c.digest(old)=='197e777ae7f5c5c0d24aacc0ecc959905ffff7a669bba5718928db7b286957bb'
    old=old.decode();node=next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)and n.name=='marker_tree')
    ns={'CATEGORY':drc.CATEGORY}
    exec(compile(ast.get_source_segment(old,node),'<actual_failed_marker_tree>','exec'),ns)
    try:ns['marker_tree'](cat)
    except TypeError as error:
        assert "'SwigPyObject' object is not iterable"in str(error)
        negative.append('actual_frozen_getAllMarkers_seam_fails_opaque_return')
    else:raise AssertionError('old unsupported API unexpectedly passed')
    with patch.object(Category,'getAllMarkers',side_effect=RuntimeError('unsupported API must never be called')):
        assert drc.marker_tree(cat)==native
        assert drc.bind_serialized_markers(native,encode(tree))['marker_count']==5
    positive.append('corrected_full_census_never_calls_unsupported_API')
    cases=[]
    def altered(name,change):
        value=copy.deepcopy(tree);change(value[drc.CATEGORY]);cases.append((name,value))
    altered('missing_serialized_child',lambda n:n['category'].pop('Short'))
    altered('extra_serialized_child',lambda n:n['category'].update(Extra=Category('Extra').serialized()))
    altered('wrong_serialized_child_name',lambda n:n['category'].update(Renamed=n['category'].pop('Short')))
    altered('missing_serialized_marker',lambda n:n['category']['Short']['violations'].pop())
    altered('extra_serialized_marker',lambda n:n['category']['Short']['violations'].append(copy.deepcopy(n['violations'][0])))
    def move_marker(n):n['category']['Short']['violations'].append(n['category']['Spacing']['violations'].pop())
    altered('same_total_wrong_direct_category_ownership',move_marker)
    altered('changed_native_cap',lambda n:n.update(max_markers='9999'))
    altered('missing_native_cap',lambda n:n.pop('max_markers'))
    altered('numeric_cap_wrong_writer_schema',lambda n:n.update(max_markers=10000))
    altered('zero_cap',lambda n:n.update(max_markers='0'))
    altered('negative_cap',lambda n:n.update(max_markers='-1'))
    altered('noncanonical_cap',lambda n:n.update(max_markers='010000'))
    altered('wrong_source',lambda n:n.update(source='other'))
    altered('unknown_category_field',lambda n:n.update(unrecorded=[]))
    altered('missing_description',lambda n:n.pop('description'))
    altered('malformed_description',lambda n:n.update(description=None))
    altered('violations_object_instead_of_list',lambda n:n.update(violations={}))
    altered('empty_present_violations',lambda n:n.update(violations=[]))
    altered('invalid_marker_entry',lambda n:n.update(violations=[None]))
    altered('empty_marker_entry',lambda n:n.update(violations=[{}]))
    altered('categories_array',lambda n:n.update(category=[]))
    altered('empty_present_category',lambda n:n.update(category={}))
    altered('nested_saturated_cap',lambda n:n['category']['Short'].update(max_markers='2'))
    for name,value in cases:reject(name,lambda value=value:drc.bind_serialized_markers(native,encode(value)))
    reject('wrong_root',lambda:drc.bind_serialized_markers(native,encode({'other':tree[drc.CATEGORY]})))
    reject('extra_root',lambda:drc.bind_serialized_markers(native,encode(dict(tree,extra=tree[drc.CATEGORY]))))
    reject('duplicate_JSON_key',lambda:drc.bind_serialized_markers(native,b'{"'+drc.CATEGORY.encode()+b'":{},"'+drc.CATEGORY.encode()+b'":{}}'))
    reject('malformed_JSON',lambda:drc.bind_serialized_markers(native,b'{'))
    # Actual file seam: complete JSON is required before the report can be accepted.
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);report=root/'report';again=root/'again';serialized=root/'markers.json'
        cat.writeTR(report);cat.writeJSON(serialized)
        measured=drc.measure_report(cat,report,again,serialized)
        assert measured['marker_count']==5 and measured['serialized_markers']['sha256']==c.file_sha(serialized)
        positive.append('actual_measure_report_binds_full_JSON_file_and_TR')
        serialized.unlink()
        reject('missing_serialized_file',lambda:drc.measure_report(cat,report,again,serialized))
        cat.writeJSON(root/'real.json');serialized.symlink_to(root/'real.json')
        reject('symlink_serialized_file',lambda:drc.measure_report(cat,report,again,serialized))
        serialized.unlink();serialized.write_bytes(b'{}')
        reject('empty_JSON_not_native_zero',lambda:drc.measure_report(cat,report,again,serialized))
        cat.writeJSON(serialized);report.write_bytes(b'violation type: fabricated\n')
        reject('TR_count_or_bytes_mismatch',lambda:drc.measure_report(cat,report,again,serialized))
    assert len(positive)==6 and len(negative)==32,(len(positive),len(negative))
    return dict(status='PASS_SYNTHETIC_MARKER_API_AND_COMPLETE_CENSUS_CONTROLS_NOT_NATIVE',
        positives=positive,refusals=negative,actual_ODB_or_CAD_executed=False)

def source_sequence(source):
    a=ast.parse(source)
    main=next(n for n in a.body if isinstance(n,ast.FunctionDef)and n.name=='native_run')
    calls=[n for n in ast.walk(main)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in ('run','phase')]
    # Line order, including calls inside the phase helper, is explicit.
    actual=[]
    for n in sorted(calls,key=lambda n:n.lineno):
        if n.func.id=='phase':
            assert isinstance(n.args[0],ast.Constant)
            actual.append(('drc-'if len(n.args)==2 and n.args[1].value is True else'')+n.args[0].value)
        elif len(n.args)>1 and isinstance(n.args[1],ast.Constant):actual.append(n.args[1].value)
    expected=['bootstrap-exact-runtime','restore-authenticated-original-ODB','actual-runtime-version','prepare','paired-original-clock-import',
        'audit-restored','drc-prepare','read-only-initial-DRT','drc-audit',
        'prepare-fixed','paired-fixed-control-import','audit-fixed','paired-original-class-return','audit-unfixed']
    assert actual==expected,('source phase order',actual)
    return actual

def controls():
    m=driver.methods();assert m['source_controls_authorized']is True
    assert type(m['native_execution_authorized'])is bool and type(m['cloud_restore_authorized'])is bool
    import cloud_mainchip_clock_diagnostic as original_cloud
    original_cloud.methods()
    sup=driver.supervisor()
    assert getattr(sup.memory_snapshot,'bounded_fresh_rss_adapter',False)
    import check_mainchip_original_clock_restoration as original
    original_result=original.controls()
    positive=['actual_old_restore_module_and_source_gate_import','actual_qualified_supervisor_and_sampler_import'];negative=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,TypeError,AttributeError,FileNotFoundError):negative.append(name)
        else:raise AssertionError('control accepted '+name)
    class Layer:
        def getName(self):return 'M1'
    class Box:
        def getTechLayer(self):return Layer()
        def xMin(self):return 1
        def yMin(self):return 2
        def xMax(self):return 3
        def yMax(self):return 4
    class MPinGeometryOnly:
        def getGeometry(self,include_decomposed_polygons=True):
            assert include_decomposed_polygons is True
            return [Box()]
    pin=MPinGeometryOnly()
    assert not hasattr(pin,'getBoxes')
    assert drc.master_pin_boxes(pin)==[('M1',1,2,3,4)]
    term=SimpleNamespace(getName=lambda:'A',getIoType=lambda:'INPUT',
        getSigType=lambda:'SIGNAL',getMPins=lambda:[pin])
    master=SimpleNamespace(getName=lambda:'fixture_master',getMTerms=lambda:[term])
    inst=SimpleNamespace(getName=lambda:'fixture_instance',getMaster=lambda:master,
        getLocation=lambda:(0,0),getOrient=lambda:'R0',getPlacementStatus=lambda:'PLACED',getOrigin=lambda:(0,0))
    block=SimpleNamespace(getNets=lambda:[],getInsts=lambda:[inst])
    native=SimpleNamespace(vias=lambda db,block,names:{})
    baseline=drc.geometry_projection(None,block,native)
    assert baseline['counts']=={'net':0,'instance':1,'master-pin':1,'used-via':0}
    positive.append('actual_projection_getGeometry_only_MPin_with_polygon_decomposition')
    # Execute the genuinely wrong previous projection seam against the same typed fixture.
    source=c.regular(c.ROOT/'scripts/mainchip_original_clock_drc.py').read_text()
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name=='geometry_projection')
    actual_projection=ast.get_source_segment(source,node)
    assert actual_projection.count('master_pin_boxes(p)')==1
    wrong=actual_projection.replace('master_pin_boxes(p)','native.boxes(p)',1)
    ns={'c':c}
    exec(compile(wrong,'<old_mpin_getBoxes_seam>','exec'),ns)
    native.boxes=lambda p:sorted((b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax())for b in p.getBoxes())
    try:ns['geometry_projection'](None,block,native)
    except AttributeError as error:
        assert "getBoxes" in str(error)
        negative.append('actual_old_MPin_getBoxes_projection_refused')
    else:raise AssertionError('wrong MPin API accepted')
    def changed_pin_projection():
        with patch.object(Box,'xMax',return_value=5):
            assert drc.geometry_projection(None,block,native)==baseline
    reject('actual_MPin_coordinate_projection_change',changed_pin_projection)
    actual=c.diagnosis(c.regular(c.ROOT/c.DIAG).read_bytes())['restore']
    assert driver.admit_restore_proof(actual)==actual
    positive.append('actual_original_629603913_byte_archive_projection')
    for key,value in [('bytes',131000000),('sha256','0'*64),('parts',2)]:
        bad=copy.deepcopy(actual);bad['restore']['archive'][key]=value
        reject('actual_archive_'+key,lambda bad=bad:driver.admit_restore_proof(bad))
    for key,value in [('bytes',0),('sha256','0'*64)]:
        bad=copy.deepcopy(actual);bad['restore']['selected_files'][driver.SELECTED[0]][key]=value
        reject('actual_donor_'+key,lambda bad=bad:driver.admit_restore_proof(bad))
    bad=copy.deepcopy(actual);del bad['restore']['selected_files'][driver.SELECTED[1]]
    reject('actual_recipient_missing',lambda:driver.admit_restore_proof(bad))
    assert driver.disk_admission(16*1024**3,'initial')['required_bytes']==16*1024**3
    assert driver.disk_admission(7*1024**3,'publish',6*1024**3)['required_bytes']==7*1024**3
    positive.append('explicit_storage_reserves_and_publication_full_copy')
    for stage,size in [('initial',16),('restore',12),('phase',4)]:
        reject('disk_'+stage,lambda stage=stage,size=size:driver.disk_admission(size*1024**3-1,stage))
    reject('disk_negative',lambda:driver.disk_admission(-1,'phase'))
    reject('disk_unknown_stage',lambda:driver.disk_admission(100*1024**3,'unknown'))
    zero=drc.marker_tree(Category())
    assert zero['marker_count']==0 and zero['zero_reported_DRT_markers']is True
    positive.append('explicit_existing_native_shaped_zero_category')
    nonzero=drc.marker_tree(Category(children=[Category('Short',2),Category('Spacing',3)]))
    assert nonzero['marker_count']==5 and nonzero['zero_reported_DRT_markers']is False
    positive.append('recursive_five_marker_count')
    for name,value in [
      ('missing_category',None),('wrong_category',Category('DRC')),
      ('wrong_source',Category(source='OTHER')),('zero_cap',Category(maximum=0)),
      ('unknown_cap',Category(maximum='10000')),('saturated',Category(count=2,maximum=2)),
      ('over_cap',Category(count=3,maximum=2)),('wrong_declared_count',Category(count=1,declared=0)),
      ('boolean_declared_count',Category(count=1,declared=True)),
      ('duplicate_subcategory',Category(children=[Category('Short'),Category('Short')])),
      ('nested_saturation',Category(children=[Category('Short',3,maximum=3)]))]:
        reject(name,lambda value=value:drc.marker_tree(value))
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);report=root/'report';reexport=root/'again';serialized=root/'markers.json'
        cat=Category(count=2);cat.writeTR(report);cat.writeJSON(serialized)
        proof=drc.measure_report(cat,report,reexport,serialized)
        assert proof['marker_count']==2 and proof['report_bytes']==report.stat().st_size
        positive.append('actual_file_TR_reexport_count')
        report.write_bytes(b'');reject('false_empty_report',lambda:drc.measure_report(cat,report,reexport,serialized))
        report.unlink();reject('missing_report',lambda:drc.measure_report(cat,report,reexport,serialized))
        cat=Category();cat.writeJSON(serialized);report.write_bytes(b'');assert drc.measure_report(cat,report,reexport,serialized)['marker_count']==0
        positive.append('explicit_zero_and_empty_report_together')
        report.unlink();report.symlink_to(reexport)
        reject('report_symlink',lambda:drc.measure_report(cat,report,reexport,serialized))
        report.unlink()
        report.write_bytes(b'not a zero marker report')
        with patch.object(cat,'writeTR',side_effect=lambda p:Path(p).write_bytes(report.read_bytes())):
            reject('nonempty_report_with_zero_native_count',lambda:drc.measure_report(cat,report,reexport,serialized))
        label='fixture'
        for name,data in [('stdout',b'actual stdout\n'),('stderr',b'')]: (root/(label+'.'+name)).write_bytes(data)
        record=dict(label=label,returncode=0,supervision_failure=None,process_group_cleanup=dict(remaining_live=[]))
        for name in ('stdout','stderr'):
            p=root/(label+'.'+name);record[name+'_bytes']=p.stat().st_size;record[name+'_sha256']=c.file_sha(p)
        assert driver.terminal_stream(record,root,label)==record;positive.append('actual_terminal_stream_bytes')
        for key,value in [('label','wrong'),('returncode',1),('supervision_failure','elapsed_limit'),
          ('process_group_cleanup',dict(remaining_live=[123])),('stdout_bytes',0),('stderr_sha256','0'*64)]:
            bad=copy.deepcopy(record);bad[key]=value
            reject('stream_'+key,lambda bad=bad:driver.terminal_stream(bad,root,label))
        (root/(label+'.stdout')).write_bytes(b'changed')
        reject('changed_terminal_file',lambda:driver.terminal_stream(record,root,label))
        driver.save(root/'atomic.json',dict(x=1))
        assert json.loads((root/'atomic.json').read_bytes())==dict(x=1)and not(root/'atomic.json.tmp').exists()
        positive.append('actual_atomic_result')
    source=c.regular(c.ROOT/'scripts/cloud_mainchip_original_clock_restoration.py').read_text()
    order=source_sequence(source);positive.append('actual_restoration_DRC_before_FIXED_sequence')
    for a,b in [('drc-prepare','prepare-fixed'),('read-only-initial-DRT','detailed-route'),('audit-restored','prepare-fixed')]:
        # Mutate genuine source strings, then inspect the resulting actual AST.
        if a=='drc-prepare':
            wrong=source.replace("phase('prepare',True)","phase('prepare-fixed')",1)
        else:wrong=source.replace("'"+a+"'","'"+b+"'",1)
        assert wrong!=source;reject('sequence_'+a,lambda wrong=wrong:source_sequence(wrong))
    program=drc.tcl(Path('/input.odb'),Path('/out'),lambda p:'{'+str(p)+'}')
    assert program==('read_db {/input.odb}\nset_thread_count 2\nwrite_def {/out/drc-before.def}\n'
      'drt::check_drc -output_file {/out/initial-drc.rpt} -marker_name '+drc.CATEGORY+
      '\nwrite_def {/out/drc-after.def}\nwrite_db {/out/drc-observed.odb}\n')
    assert 'detailed_route'not in program and 'global_route'not in program
    positive.append('actual_whole_design_DRT_program')
    import publish_mainchip_saved_postroute as pub
    previous=pub.GROUP;seen=[]
    def fake(root,out):
        assert pub.GROUP==driver.GROUP and root==driver.OUT and out==driver.ROOT/('publication-'+driver.GROUP)
        seen.append('actual_driver_publish_call');return dict(mock_transport=True)
    with patch.object(driver,'methods',return_value=m),patch.object(driver,'storage',return_value={}),patch.object(pub,'publish_evidence',side_effect=fake):
        assert driver.publish()==dict(mock_transport=True)
    assert pub.GROUP==previous and len(seen)==1
    positive.append('actual_driver_qualified_publisher_group_and_paths')
    injected=ValueError('injected transport refusal')
    with patch.object(driver,'methods',return_value=m),patch.object(driver,'storage',return_value={}),patch.object(pub,'publish_evidence',side_effect=injected)as failed_publish:
        try:driver.publish()
        except ValueError as error:
            assert error is injected and str(error)=='injected transport refusal'
            failed_publish.assert_called_once_with(driver.OUT,driver.ROOT/('publication-'+driver.GROUP))
            negative.append('publisher_error_preserved')
        else:raise AssertionError('injected publisher error accepted')
    assert pub.GROUP==previous
    import check_mainchip_saved_postroute_publication as pubcheck
    publication=pubcheck.controls()
    import cloud_verified_parts as archive
    archive_result=archive.controls()
    import wait_cloud_tested_source_release as waiter
    wait_result=waiter.controls()
    marker_result=marker_controls()
    assert len(positive)==14 and len(negative)==39,(len(positive),len(negative))
    return dict(status='PASS_CLOCK_RESTORATION_DRIVER_SOURCE_CONTROLS_NOT_NATIVE',positives=positive,refusals=negative,
        marker_API_repair=marker_result,original=original_result,qualified_publication=publication,qualified_archive=archive_result,
        qualified_wait=wait_result,phase_sequence=order,protected=len(m['protected']),
        synthetic_marker_API_scope=True,actual_ODB_or_CAD_executed=False,accepted=False)

def emit(path):
    raw=c.regular(path).read_bytes();assert len(raw)<=32*1024*1024
    size=3000;chunks=[raw[i:i+size]for i in range(0,len(raw),size)]
    print('CLOCK_RESTORE_RESULT_BEGIN '+json.dumps(dict(bytes=len(raw),sha256=c.digest(raw),chunks=len(chunks))),flush=True)
    for i,b in enumerate(chunks):print('CLOCK_RESTORE_RESULT_CHUNK '+json.dumps(dict(index=i,base64=base64.b64encode(b).decode())),flush=True)
    print('CLOCK_RESTORE_RESULT_END '+c.digest(raw),flush=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING_SOURCE_CONTROLS',source_head=os.environ['GITHUB_SHA'],native_execution=False)
    try:result.update(controls())
    except BaseException as e:
        result.update(status='FAIL_SOURCE_CONTROLS',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        path=OUT/'result.json';driver.save(path,result);emit(path)
if __name__=='__main__':main()
