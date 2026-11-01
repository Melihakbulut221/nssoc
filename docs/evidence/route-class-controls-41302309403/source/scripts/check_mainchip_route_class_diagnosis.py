#!/usr/bin/env python3
"""Exercise actual parser/restorer and diagnostic classification; no native inputs."""
import copy,json
from pathlib import Path
import mainchip_route_class_diagnosis as d
def record(name='protected',kind='FIXED',x=10,connection='u1'):
    if kind is None:return ('- '+name+' ( '+connection+' A ) ;\n').encode()
    return ('- '+name+' ( '+connection+' A )\n  + '+kind+' Metal2 ( '+str(x)+' 20 ) ( 30 20 ) ;\n').encode()
def fixture(row):
    return b'VERSION 5.8 ;\nNETS 2 ;\n'+row+record('mutable','ROUTED')+b'END NETS\nEND DESIGN\n'
def main():
    checks=[]
    def test(label,fn):fn();checks.append(label)
    def expect(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):checks.append(label);return
        raise AssertionError('not rejected: '+label)
    before=fixture(record())
    def run(post,classes=None,mutable=None):return d.analyze(before,fixture(post),{'protected':'ROUTED'}if classes is None else classes,['mutable']if mutable is None else mutable)
    r,_,_=run(record());assert r['strict_restorer_failures']==0 and r['changed_records']==0;checks.append('unchanged_FIXED_original_restorer_passes')
    r,p,_=run(record(kind='ROUTED'));assert r['strict_restorer_failures']==1 and r['class_normalized_changed_records']==0 and p['protected']['connection_prefix_equal'];checks.append('ROUTED_class_only_original_restorer_fails')
    r,_,_=run(record(kind='COVER'));assert r['strict_restorer_failures']==1 and r['class_normalized_changed_records']==0;checks.append('COVER_class_change_reported_without_acceptance')
    r,_,_=run(record(x=11));assert r['strict_restorer_failures']==0 and r['class_normalized_changed_records']==1;checks.append('geometry_change_not_hidden_by_FIXED_class')
    r,_,_=run(record(kind='ROUTED',x=11));assert r['strict_restorer_failures']==1 and r['class_normalized_changed_records']==1;checks.append('class_and_geometry_change_separated')
    r,_,_=run(record(connection='u2'));assert r['connection_prefix_changes']==1 and r['class_normalized_changed_records']==1;checks.append('connection_change_reported')
    r,_,_=run(record(kind=None));assert r['strict_restorer_failures']==1 and r['class_normalized_changed_records']==1;checks.append('lost_selected_wire_reported')
    r,_,_=d.analyze(fixture(record(kind=None)),fixture(record()),{'protected':None},['mutable']);assert r['strict_restorer_failures']==1;checks.append('new_wire_on_unwired_selected_reported')
    unwired_with_guard=fixture(record(kind=None)).replace(b'NETS 2',b'NETS 3').replace(b'END NETS',record('guard')+b'END NETS')
    r,_,_=d.analyze(unwired_with_guard,unwired_with_guard,{'protected':None,'guard':'ROUTED'},['mutable']);assert r['strict_restorer_failures']==0;checks.append('retained_unwired_selected_with_original_required_wired_record')
    expect('all_unwired_original_restorer_precondition',lambda:d.analyze(fixture(record(kind=None)),fixture(record(kind=None)),{'protected':None},['mutable']))
    expect('mutable_overlap',lambda:run(record(),mutable=['mutable','protected']))
    expect('duplicate_mutable',lambda:run(record(),mutable=['mutable','mutable']))
    expect('missing_partition_owner',lambda:run(record(),mutable=[]))
    expect('unknown_partition_owner',lambda:run(record(),mutable=['mutable','absent']))
    expect('net_census_changed',lambda:run(record(name='renamed')))
    expect('invalid_original_class',lambda:run(record(),classes={'protected':'BOGUS'}))
    expect('wrong_before_class',lambda:d.analyze(fixture(record(kind='ROUTED')),fixture(record()),{'protected':'ROUTED'},['mutable']))
    expect('mixed_clauses',lambda:run(record().replace(b' ;',b'\n  + ROUTED Metal3 ( 1 2 ) ( 3 4 ) ;')))
    expect('malformed_section',lambda:d.analyze(before.replace(b'NETS 2',b'NETS 3'),before,{'protected':'ROUTED'},['mutable']))
    expect('duplicate_net',lambda:run(record(name='mutable')))
    expect('CRLF_refused',lambda:d.analyze(before.replace(b'\n',b'\r\n'),before,{'protected':'ROUTED'},['mutable']))
    r,_,_=d.analyze(before,fixture(record(kind='ROUTED',x=11)),{'protected':'ROUTED'},['mutable'],['protected'])
    assert r['counterpart_records']==1 and r['normalized_counterpart_changes']==1 and r['normalized_changes_outside_counterparts']==0 and r['strict_failures_outside_counterparts']==0
    checks.append('authorized_counterpart_class_geometry_change_reported_separately')
    expect('unknown_counterpart',lambda:d.analyze(before,before,{'protected':'ROUTED'},['mutable'],['absent']))
    expect('duplicate_counterpart',lambda:d.analyze(before,before,{'protected':'ROUTED'},['mutable'],['protected','protected']))
    expect('wrong_counterpart_original_class',lambda:d.analyze(before,before,{'protected':'FIXED'},['mutable'],['protected']))
    assert all(r[k]is False for k in ['layout_modified','full_phy_accepted','physical_acceptance','timing_accepted'])
    checks.append('all_acceptance_and_mutation_flags_false')
    out=Path('cloud-route-class-controls');out.mkdir(exist_ok=False)
    (out/'controls.json').write_text(json.dumps(dict(status='PASS_READ_ONLY_CLASS_DIAGNOSIS_CONTROLS',checks=checks,count=len(checks)),indent=2)+'\n')
    print(json.dumps(dict(count=len(checks),status='PASS_READ_ONLY_CLASS_DIAGNOSIS_CONTROLS')))
if __name__=='__main__':
    try:main()
    except BaseException as exc:
        import traceback
        out=Path('cloud-route-class-controls');out.mkdir(exist_ok=True)
        (out/'failure.json').write_text(json.dumps(dict(error=repr(exc),traceback=traceback.format_exc()),indent=2)+'\n')
        raise
