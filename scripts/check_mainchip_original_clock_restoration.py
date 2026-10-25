#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source fixtures only; synthetic DEF is not a native preservation proof."""
import ast,copy,json,os,re
from pathlib import Path
import mainchip_original_clock_restoration as c

NAME='clknet_3_5_0_pcie_clk_i'
def fixture():
    head=b'VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN chip ;\nUNITS DISTANCE MICRONS 1000 ;\nCOMPONENTS 1 ;\n- a cell + PLACED ( 2 3 ) N ;\nEND COMPONENTS\nNETS 4 ;\n'
    route=b'  - '+NAME.encode()+b' ( a X ) ( PIN clk )\n    + USE CLOCK\n    + NONDEFAULTRULE WIDE\n    + ROUTED Metal1 ( 10 20 ) ( 30 * )\n      NEW Metal2 ( 30 20 ) via\n ;\n'
    fixed=b' - other_fixed ( a Q )\n  + FIXED Metal1 ( 4 5 ) ( 6 * ) ;\n'
    unwired=b' - clock_unwired ( a CLK ) + USE CLOCK ;\n'
    data=b' - data ( a D )\n + ROUTED Metal1 ( 40 50 ) ( 60 * ) ;\n'
    tail=b'END NETS\nEND DESIGN\n'
    before=head+route+b'\n'+fixed+unwired+data+tail
    after=before.replace(b'( 10 20 )',b'( 11 20 )').replace(b'( 40 50 )',b'( 41 50 )')
    names=[NAME,'other_fixed','clock_unwired']
    snap={}
    for label,raw in [('before',before),('after',after)]:
        records=c.parse_def(raw)['records']
        snap[label]={n:dict(statement=records[n].decode().split(),
            instances={'a':dict(master='cell',location=[2,3],orientation='R0',status='PLACED')})for n in names}
    change={NAME:dict(before=snap['before'][NAME],after=snap['after'][NAME])}
    return before,after,snap,change


def metadata_def_seam(native):
    calls={n.args[-1].value:n for n in ast.walk(native)
        if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='metadata_base'
        and isinstance(n.args[-1],ast.Constant)}
    assert set(calls)=={'fixed-metadata-only','unfixed-metadata-only'}
    for label,call in calls.items():
        assert isinstance(call.args[3],ast.Name)and call.args[3].id=='fixed',label
    return calls

def controls():
    assert c.source_gate()['source_controls_authorized']is True,'source controls not authorized'
    positives=[];failures=[]
    def reject(name,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError,UnicodeError):failures.append(name)
        else:raise AssertionError('control accepted '+name)
    a,b,s,changes=fixture()
    expected,plan=c.plan_records(a,b,s,changes,3,1)
    # Independent literal expectation keeps the recipient data route at 41, while replacing only clock 11->10.
    literal=b.replace(b'( 11 20 )',b'( 10 20 )')
    assert expected==literal and expected!=a and expected!=b
    c.verify_exact(expected,literal);positives.append('recipient_preserved_donor_record_splice')
    fixed,original=c.fixed_overlay(expected,plan['all_clock_names'])
    assert original=={NAME:'ROUTED','clock_unwired':None,'other_fixed':'FIXED'}
    assert c.restore_classes(fixed,original)==expected
    positives.append('exact_class_roundtrip_with_fixed_and_unwired')
    patch,removed=c.patch_def(b,{NAME:c.parse_def(a)['records'][NAME]})
    assert removed==2 and b'COMPONENTS'not in patch and b'( a X )'not in patch and b'( PIN clk )'not in patch
    assert c.parse_def(patch)['records'][NAME].split()[0:2]==[b'-',NAME.encode()]
    assert b'+ ROUTED'in patch and b'NEW Metal2'in patch
    positives.append('qualified_nets_only_connection_omission')
    encoded={NAME:dict(wire_present=True,metadata='FIXED',paths=['FIXED','FIXED']),
        'other_fixed':dict(wire_present=True,metadata='FIXED',paths=['FIXED']),
        'clock_unwired':dict(wire_present=False,metadata='NONE',paths=[])}
    c.validate_encoded(encoded,{n:'FIXED'if k is not None else None for n,k in original.items()})
    positives.append('all_encoded_paths_not_metadata_only')
    old=copy.deepcopy(encoded);old[NAME]['metadata']='ROUTED';old[NAME]['paths']=['ROUTED','ROUTED']
    after=copy.deepcopy(old);after[NAME]['metadata']='FIXED'
    target={name:row['metadata']for name,row in after.items()}
    assert c.validate_metadata_transition(after,old,target)
    assert c.validate_metadata_transition(old,after,{name:row['metadata']for name,row in old.items()})
    positives.append('independent_metadata_set_and_restore_preserve_encoding')
    # A metadata-only native observation can export the same FIXED text; decoder admission still rejects it.
    c.verify_exact(fixed,fixed)
    reject('fixed_DEF_does_not_prove_encoded_FIXED',lambda:c.validate_encoded(after,
        {n:'FIXED'if v is not None else None for n,v in original.items()}))
    for label,edit in [
        ('metadata_not_set',lambda x:x[NAME].__setitem__('metadata','ROUTED')),
        ('metadata_changes_path',lambda x:x[NAME].__setitem__('paths',['FIXED','FIXED'])),
        ('metadata_drops_wire',lambda x:x[NAME].__setitem__('wire_present',False)),
        ('metadata_missing_member',lambda x:x.pop('other_fixed'))]:
        bad=copy.deepcopy(after);edit(bad)
        reject(label,lambda bad=bad:c.validate_metadata_transition(bad,old,target))
    for name,raw in [
        ('clock_coordinate',expected.replace(b'( 10 20 )',b'( 12 20 )')),
        ('signal_coordinate',expected.replace(b'( 41 50 )',b'( 40 50 )')),
        ('component_coordinate',expected.replace(b'( 2 3 )',b'( 2 4 )')),
        ('whitespace',expected.replace(b'\n\n',b'\n',1)),
        ('connection_order',expected.replace(b'( a X ) ( PIN clk )',b'( PIN clk ) ( a X )')),
        ('ndr_name',expected.replace(b'NONDEFAULTRULE WIDE',b'NONDEFAULTRULE WRONG')),
        ('via_name',expected.replace(b') via',b') wrong')),
        ('clock_class',expected.replace(b'+ ROUTED Metal1 ( 10',b'+ FIXED Metal1 ( 10')),
        ('missing_new_path',expected.replace(b'      NEW Metal2 ( 30 20 ) via\n',b'')),
        ('header',expected.replace(b'DESIGN chip',b'DESIGN other'))]:
        assert raw!=expected
        reject(name,lambda raw=raw:c.verify_exact(expected,raw))
    for name,raw in [
        ('count',b.replace(b'NETS 4 ;',b'NETS 5 ;')),
        ('duplicate_section',b+b),
        ('unterminated',b.replace(b' ;\n\n',b'\n\n',1)),
        ('unowned_text',b.replace(b'NETS 4 ;\n',b'NETS 4 ;\nSURPRISE\n')),
        ('duplicate_record',b.replace(b' - data ',b' - other_fixed ')),
        ('bad_terminator',b.replace(b' ;\n\n',b' ; EXTRA\n\n',1)),
        ('crlf',b.replace(b'\n',b'\r\n'))]:
        assert raw!=b
        reject(name,lambda raw=raw:c.parse_def(raw))
    reject('wrong_replacement_owner',lambda:c.replace_records(b,{'missing':b' - missing ;\n'}))
    reject('renamed_replacement',lambda:c.replace_records(b,{NAME:c.parse_def(a)['records'][NAME].replace(NAME.encode(),b'wrong',1)}))
    reject('multiple_wire_clauses',lambda:c.classes(c.parse_def(a)['records'][NAME]+b' + ROUTED Metal1 ( 1 2 )\n'))
    reject('unwired_treated_routed',lambda:c.classes(c.parse_def(a)['records']['clock_unwired']))
    reject('wrong_source_def',lambda:c.make_plan(a,b,s,{'diagnosis':{'changes':changes}}))
    for name,edit in [
        ('wrong_snapshot_statement',lambda t:t['after'][NAME]['statement'].__setitem__(1,'wrong')),
        ('wrong_attached_master',lambda t:t['after'][NAME]['instances']['a'].__setitem__('master','wrong')),
        ('wrong_attached_position',lambda t:t['after'][NAME]['instances']['a'].__setitem__('location',[2,4])),
        ('missing_selected_net',lambda t:t['after'].pop('other_fixed')),
        ('unreported_snapshot_change',lambda t:t['after']['other_fixed']['instances']['a'].__setitem__('status','FIXED'))]:
        bad=copy.deepcopy(s);edit(bad)
        reject(name,lambda bad=bad:c.plan_records(a,b,bad,changes,3,1))
    reject('missing_changed_owner',lambda:c.plan_records(a,b,s,{},3,1))
    reject('wrong_changed_count',lambda:c.plan_records(a,b,s,changes,3,2))
    for name,key,edit in [
        ('metadata_only',NAME,lambda r:r.__setitem__('paths',['ROUTED','ROUTED'])),
        ('later_path_routed',NAME,lambda r:r.__setitem__('paths',['FIXED','ROUTED'])),
        ('missing_native_wire',NAME,lambda r:r.__setitem__('wire_present',False)),
        ('missing_native_paths',NAME,lambda r:r.__setitem__('paths',[])),
        ('wrong_metadata',NAME,lambda r:r.__setitem__('metadata','ROUTED')),
        ('fabricated_unwired','clock_unwired',lambda r:r.__setitem__('wire_present',True))]:
        bad=copy.deepcopy(encoded);edit(bad[key])
        reject(name,lambda bad=bad:c.validate_encoded(bad,{n:'FIXED'if k is not None else None for n,k in original.items()}))
    reject('missing_encoded_member',lambda:c.validate_encoded({NAME:encoded[NAME]},original))
    reject('wrong_unfix_class',lambda:c.restore_classes(expected,original))
    report=c.diagnosis(c.regular(c.ROOT/c.DIAG).read_bytes())
    inventory=json.loads(c.regular(c.ROOT/'docs/evidence/mainchip-original-clock-restoration-selectors-20261025.json').read_bytes())
    actual=report['diagnosis']['changes']
    assert inventory['changed_names']==sorted(actual)
    assert inventory['changed_names_sha256']==c.digest(c.canonical(sorted(actual)))
    for n,row in inventory['changes'].items():
        for side in ('before','after'):
            assert row[side+'_statement_sha256']==c.digest(c.canonical(actual[n][side]['statement']))
    positives.append('actual_218_selector_and_statement_bindings')
    for name,path,value in [
        ('actual_run',['run_id'],0),('actual_source',['source_head'],'0'*40),
        ('actual_return',['native_returncode'],0),('original_gate',['original_clock_gate_passed'],True),
        ('accepted',['accepted'],True),('changed_census',['diagnosis','changed_nets'],217),
        ('clock_census',['diagnosis','before_nets'],1690),
        ('instance_change',['diagnosis','attached_geometry_changed'],1),
        ('prefix_change',['diagnosis','connection_prefixes_changed'],1),
        ('snapshot_hash',['diagnosis','snapshot_sha256','after'],'0'*64)]:
        bad=copy.deepcopy(report);d=bad
        for k in path[:-1]:d=d[k]
        d[path[-1]]=value
        reject(name,lambda bad=bad:c.diagnosis_fields(bad))
    reject('altered_actual_diagnostic_bytes',lambda:c.diagnosis(c.canonical(report)))
    original_gate=ast.parse(c.regular(c.ROOT/c.GATE).read_bytes())
    native=ast.parse(c.regular(c.ROOT/'scripts/mainchip_original_clock_restoration_native.py').read_bytes())
    main=next(n for n in original_gate.body if isinstance(n,ast.FunctionDef)and n.name=='main')
    selected=next(n for n in native.body if isinstance(n,ast.FunctionDef)and n.name=='selected')
    old=[n for n in ast.walk(main)if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id=='clocks'and isinstance(n.value,ast.SetComp)]
    new=[n for n in selected.body if isinstance(n,ast.Assign)]
    assert len(old)==len(new)==2 and [ast.dump(n,include_attributes=False)for n in old]==[ast.dump(n,include_attributes=False)for n in new]
    positives.append('exact_original_full_selector_AST')
    metadata_def_seam(native);positives.append('actual_metadata_export_overlay_seam')
    for label in ('fixed-metadata-only','unfixed-metadata-only'):
        bad=copy.deepcopy(native);calls=metadata_def_seam(bad)
        calls[label].args[3]=ast.Name(id='expected',ctx=ast.Load())
        reject('wrong_DEF_expectation_'+label,lambda bad=bad:metadata_def_seam(bad))
    assert c.file_sha(c.ROOT/c.GATE)==c.GATE_SHA
    assert len(failures)==len(set(failures))==55 and len(positives)==8
    return dict(status='SOURCE_CONTROLS_ONLY_NOT_NATIVE_EXECUTION',positives=positives,
        refusals=failures,positive_count=len(positives),refusal_count=len(failures),
        native_import_executed=False,actual_FIXED_roundtrip_executed=False,
        routing_DRC_measured=False,accepted=False)

if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    print(json.dumps(controls(),indent=2,sort_keys=True))
