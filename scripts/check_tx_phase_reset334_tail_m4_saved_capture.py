#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted real-code fixtures; synthetic inputs never qualify a native capture."""
import ast,contextlib,copy,io,json,os,re,tempfile,types
from pathlib import Path
from unittest import mock
import numpy as np
import cloud_tx_phase_reset334_tail_m4_saved_capture as c
import tx_phase_reset334_tail_m4_saved_diagnosis as d
import check_tx_phase_reset334_saved_diagnosis as inherited_math
import check_tx_phase_reset334_tail_m4_saved_imports as imports

def reject(name,fn):
    try:fn()
    except(AssertionError,KeyError,ValueError,TypeError,FileNotFoundError):return name
    raise AssertionError('Accepted fixture corruption '+name)

def synthetic_topology():
    roles={}
    ids=[dict(XREF=68,XAP=69,XAN=70,XBP=71,XBN=72,XSA=73,XSB=74,XT=75),
         dict(XREF=76,XAP=77,XAN=78,XBP=79,XBN=80,XSA=81,XSB=82,XT=83),
         dict(XREF=91,XAP=92,XAN=93,XBP=94,XBN=95,XSA=96,XSB=97,XT=98),
         dict(XREF=99,XAP=100,XAN=101,XBP=102,XBN=106,XSA=103,XSB=104,XT=105)]
    for prefix,table in zip(d.TARGETS.values(),ids,strict=True):
        local=lambda n:prefix+'__'+n
        nets=dict(XT=[local('TAIL'),local('REF'),'AVSS','SUB'],
          XREF=[local('REF'),local('REF'),'AVSS','SUB'],
          XSA=[local('EA'),'PHASE__RUNP',local('TAIL'),'SUB'],
          XSB=[local('EB'),'PHASE__RUNN',local('TAIL'),'SUB'],
          XAP=[local('OUTN'),local('DP'),local('EA'),'SUB'],
          XAN=[local('OUTP'),local('DN'),local('EA'),'SUB'],
          XBP=[local('OUTN'),local('SEEDP'),local('EB'),'SUB'],
          XBN=[local('OUTP'),local('SEEDN'),local('EB'),'SUB'])
        for leaf,did in table.items():
            source=prefix+'__'+leaf;nx=1 if leaf=='XREF'else 4 if leaf in ('XT','XSA','XSB')else 2
            roles[source]=dict(source_instance=source,native_id=did,model='npn13G2',parameters=dict(Nx=nx,m=1),
              terminals={t:dict(model_node='BULK'if t=='S'else 'f'+str(did)+t,source_net=n,
                native_cluster='synthetic-'+n,reference_label=None if t=='S'else 'T'+str(did)+'_'+t)
                for t,n in zip(('C','B','E','S'),nets[leaf],strict=True)})
    for i,name in enumerate(sorted(d.passive_source_names()),200):
        roles[name]=dict(source_instance=name,native_id=i,model='rppd',parameters=dict(w=1,l=2),
          terminals={t:dict(model_node='BULK'if t=='rppd_sub'else 'r'+str(i)+t,source_net='SUB'if t=='rppd_sub'else name+'__'+t,
            native_cluster='synthetic',reference_label=None if t=='rppd_sub'else 'T'+str(i)+'_'+t)
            for t in ('rppd_1','rppd_2','rppd_sub')})
    payloads={p:dict(compact_roles=copy.deepcopy(roles))for p in ('p','n')}
    cc=dict(instances=[],hbt={},vectors=[])
    for inst,sign in [('xdut','p'),('xloadm','n'),('xloadq','p')]:
        ports=['clkp','clkn','mp','mn','qp','qn','armp','armn','avdd','0','0','0']
        cc['instances'].append(dict(instance=inst,variant=sign,actual_ports=ports))
        for src,r in roles.items():
            if r['model']!='npn13G2':continue
            terms=[inst+'.'+r['terminals'][t]['model_node'].lower()for t in ('C','B','E','S')]
            cc['hbt'][inst+'.xd'+str(r['native_id'])]=dict(fixture_instance=inst,source_instance=src,
              native_id=r['native_id'],terminals=terms,nx=r['parameters']['Nx'])
        for r in roles.values():
            cc['vectors']+=['v('+inst+'.'+t['model_node'].lower()+')'for t in r['terminals'].values()]
    cc['vectors']=sorted(set(cc['vectors']))
    return cc,payloads

def headroom_fixture(fn=d.headroom):
    names={n:dict(name=n)for n in ('XT','XREF','XSA','XSB','XAP','XAN','XBP','XBN')}
    def state(cv,bv,ev,ic=1e-3,nx=4):return[cv,bv,ev,0.,cv-ev,bv-ev,ic,ic/nx]
    frame=dict(hbt={n:state(1.5,1.2,.5)for n in names})
    frame['hbt'].update(XT=state(1.2,.9,.3),XREF=state(.89,.88,.28,nx=1),
      XSA=state(1.6,2.,1.22),XSB=state(1.5,1.95,1.21))
    result=fn(frame,{'tail':dict(devices=names)},{'tail':0.})['tail']
    assert abs(result['tail_vce_v']-.9)<1e-14 and abs(result['tail_emitter_to_public_AVSS_v']-.3)<1e-14
    for leg,wire,base,vbe in [('XSA',.02,1.7,-.78),('XSB',.01,1.65,-.74)]:
        r=result['steering_VCE_decomposition'][leg]
        assert abs(r['wire_emitter_to_tail_collector_v']-wire)<1e-14
        assert abs(r['base_to_tail_emitter_v']-base)<1e-14 and abs(r['minus_steering_vbe_v']-vbe)<1e-14
        assert abs(r['reconstructed_tail_vce_v']-.9)<1e-14
    ref=result['local_reference_VBE_decomposition']
    assert abs(ref['base_contact_drop_v']-.02)<1e-14 and abs(ref['reference_to_tail_emitter_v']+.02)<1e-14
    assert abs(ref['reference_vbe_v']-.6)<1e-14 and abs(ref['reconstructed_tail_vbe_v']-.6)<1e-14
    assert not result['full_KCL_claimed']and result['collector_Ic_is_not_emitter_current']
    return result

def interval_fixture(fn=d.intervals):
    t=np.array([0.,1.,2.,3.,4.]);y=np.array([.39,.38,.41,.39,.42])
    rows=fn(t,y,start=1.)
    assert len(rows)==2 and rows[0]['first']['row']==rows[0]['last']['row']==1
    assert rows[0]['left_censored']and not rows[0]['right_censored']and rows[0]['before']['value_v']==.39
    assert rows[1]['first']['row']==3 and not rows[1]['left_censored']and not rows[1]['right_censored']
    assert rows[1]['before']['row']==2 and rows[1]['after']['row']==4
    whole=fn(t,np.array([.39]*5),start=0.)[0]
    assert whole['left_censored']and whole['right_censored']and whole['before']is whole['after']is None
    assert fn(t,y,start=5.)==[]
    cut=fn(t,np.array([.39]*5),start=1.5)[0]
    assert cut['first']['row']==2 and cut['left_censored']and cut['before']['time_s']==1.
    return dict(exact_samples=True,active_cutoff_and_capture_end_censoring=True)

def mutated_function(name,before,after):
    raw=(c.ROOT/'scripts/tx_phase_reset334_tail_m4_saved_diagnosis.py').read_text()
    node=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name==name)
    text=ast.get_source_segment(raw,node);assert text.count(before)==1
    ns=dict(vars(d));exec(compile(text.replace(before,after),'<actual-function-mutation>','exec'),ns)
    return ns[name]

def reconstruct_fixture():
    """Complete actual reconstruction glue; native/archive collaborators are explicit synthetic stubs."""
    with tempfile.TemporaryDirectory()as td:
        root=Path(td)/'native';root.mkdir();(root/'fresh-preparation').mkdir()
        (root/'fresh-preparation/original-PLL-observer.summary.json').write_bytes(b'fixed scalar fixture')
        base=''.join('old'+str(i)+'\n'for i in range(6));rewritten=''.join('new'+str(i)+'\n'for i in range(6))
        contract={'synthetic_fixture_only':True}
        adapter=types.SimpleNamespace(initialized_deck=lambda b,cc:b+'OFF\n',flag_block=lambda cc,on:'OFF\n')
        init=types.SimpleNamespace(adapters=lambda:adapter)
        def prepare(*args):
            paths=args[6]
            prefix=Path('/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-tx-phase-reset334-tail-m4-loaded/native/fresh-preparation/qualified-binding/qualified-rc')
            assert paths=={p:prefix/p/'composition/reset334-wire.spice'for p in ('p','n')}
            return base,contract
        bench=types.SimpleNamespace(prepare=prepare,qualified_inputs=lambda *a:({},dict(p={},n={})))
        runtime=types.SimpleNamespace(bench=bench)
        inputs=(b'bound',b'prep',dict(p=b'p',n=b'n'),dict(p='P',n='N'),{},init,runtime,{'p-initial-high':(base,contract)})
        def read_inputs(path,op):
            assert path==root
            return inputs
        controls=dict(actual_source_refusals=list(range(18)),original_path_controls=dict(negative_controls=list(range(32))))
        result=dict(preparation_source=dict(path_binding=dict(six_path_cards=[dict(line=i,old='old'+str(i)+'\n',new='new'+str(i)+'\n')for i in range(6)],
          byte_exact_reversal=True,runtime_base_sha256=c.digest(rewritten))),
          outputs={'work/bench.cir':c.digest(rewritten+'OFF\n'),'work/contract.json':c.digest(c.encode(contract))})
        def actual_stub(*args):return dict(rejected=list(range(24)))
        with mock.patch.object(c.current,'read_inputs',side_effect=read_inputs),mock.patch.object(c.current,'actual_input_controls',return_value=controls),\
             mock.patch.object(c.current.loaded,'isolated',return_value=c.current.frozen),mock.patch.object(c.prior,'actual_controls',actual_stub):
            value=c.reconstruct(root,{},result)
            assert value[:2]==(contract,rewritten+'OFF\n')and value[2].review_capture.__code__ is c.current.frozen.review_capture.__code__
            wrong=copy.deepcopy(result);wrong['outputs']['work/bench.cir']='0'*64
            refused=reject('reconstructed_runtime_deck_hash',lambda:c.reconstruct(root,{},wrong))
        return dict(actual_reconstruct_return_reached=True,negative=refused,native_or_archive_executed=False)

def main_entry_fixture():
    class StopBeforeRestore(Exception):pass
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);out=root/'result';temp=root/'temp';temp.mkdir()
        method=dict(readback_authorized=True)
        def stop(*a):raise StopBeforeRestore('explicit no archive/network boundary')
        with mock.patch.object(c,'methods',return_value=method),mock.patch.object(c,'completed_controls',return_value={'fixture':True}),\
             mock.patch.object(c,'OUT',out),mock.patch.object(c.transport,'precreated',return_value={'fixture':True}),\
             mock.patch.object(c.shutil,'disk_usage',return_value=types.SimpleNamespace(free=32*1024**3)),\
             mock.patch.object(c,'restore_capture',side_effect=stop),mock.patch.dict(os.environ,{'RUNNER_TEMP':str(temp)}),\
             mock.patch('sys.argv',['controller','--readback']):
            try:
                with contextlib.redirect_stdout(io.StringIO()):c.main()
            except StopBeforeRestore:pass
            else:raise AssertionError('Actual main did not reach explicit restore boundary')
        result=json.loads((out/'result.json').read_bytes())
        assert result['status']=='FAIL_CURRENT_TAIL_M4_SAVED_CAPTURE_DIAGNOSIS'and 'StopBeforeRestore'in result['error']
        assert result['outputs']=={}and result['new_simulation']is False and result['original_electrical_rejection_preserved']
        return dict(actual_main_entry=True,actual_finally_failure_preserved=True,archive_or_native_executed=False)

def main_result_failure_fixtures():
    """Exercise the actual controller save/except/finally path, never restoration or analysis."""
    class StopBeforeRestore(Exception):pass
    positives=[]
    for mode in ('body_result_limit','body_aggregate_limit','body_encoder_error','finally_result_limit'):
        with tempfile.TemporaryDirectory()as td:
            root=Path(td);out=root/'result';temp=root/'temp';temp.mkdir()
            original_stop='explicit restore stop '+('z'*2048 if mode=='finally_result_limit'else '')
            def precreated(*args):
                if mode=='body_result_limit':return dict(fixture='x'*2048)
                if mode=='body_encoder_error':return dict(fixture=object())
                if mode=='body_aggregate_limit':
                    remain=4*1024**2-1024**2-sum(c.resources.output_files(out).values())-128
                    assert remain>0
                    (out/'preserved-fixture.json').write_bytes(b'"'+b'e'*(remain-2)+b'"')
                return dict(fixture=True)
            def stop(*args):raise StopBeforeRestore(original_stop)
            with (
                mock.patch.object(c,'methods',return_value=dict(readback_authorized=True)),
                mock.patch.object(c,'completed_controls',return_value=dict(fixture=True)),
                mock.patch.object(c,'OUT',out),mock.patch.object(c.transport,'precreated',side_effect=precreated),
                mock.patch.object(c.shutil,'disk_usage',return_value=types.SimpleNamespace(free=32*1024**3)),
                mock.patch.object(c,'snapshot',return_value=(b'',{},{})),mock.patch.object(c,'restore_capture',side_effect=stop),
                mock.patch.object(c.resources,'MAX_RESULT_BYTES',1024),
                mock.patch.object(c.resources,'MAX_OUTPUT_BYTES',4*1024**2),
                mock.patch.object(c.resources,'FAILURE_RESERVE_BYTES',1024**2),
                mock.patch.dict(os.environ,dict(RUNNER_TEMP=str(temp),GITHUB_RUN_ID='1',GITHUB_SHA='a'*40)),
                mock.patch('sys.argv',['controller','--readback']),
            ):
                try:
                    with contextlib.redirect_stdout(io.StringIO()):c.main()
                except RuntimeError as error:
                    assert str(error)=='Complete terminal failure envelope preserved; diagnosis incomplete'
                else:raise AssertionError('Actual controller accepted failed result publication')
                assert sum(c.resources.output_files(out).values())<=c.resources.MAX_OUTPUT_BYTES
            raw=(out/'result.json').read_bytes();result=json.loads(raw)
            assert result['status']=='FAIL_INCOMPLETE_CURRENT_AVSS18_SAVED_CAPTURE_DIAGNOSIS'
            assert not result['complete_diagnosis']and not result['accepted']and not result['partial_result_accepted']
            assert result['original_electrical_rejection_preserved']and not result['new_simulation']
            assert result['previous_complete_and_partial_bytes_preserved']
            files=result['preserved_evidence']
            assert set(files)==set(result['outputs'])=={p.name for p in out.iterdir()if p.name!='result.json'}
            assert 'result.previous.json'in files and 'result.json.incomplete'in files
            assert json.loads((out/'result.previous.json').read_bytes())['status']=='RUNNING'
            for name,proof in files.items():
                assert (out/name).stat().st_size==proof['bytes']and c.sha(out/name)==proof['sha256']==result['outputs'][name]
            error=result['original_failure']['error']
            if mode=='body_encoder_error':assert 'TypeError'in error and 'JSON serializable'in error
            elif mode=='finally_result_limit':
                assert original_stop in error and 'StopBeforeRestore'in error
                assert result['result_write_failure']['type']=='ResourceLimit'
            else:assert 'ResourceLimit'in error
            assert result['original_failure']['traceback']and result['result_write_failure']['traceback']
            positives.append(dict(case=mode,actual_main_and_finally=True,complete_terminal_failure=True,
              evidence_files=len(files),envelope_bytes=len(raw),archive_or_native_executed=False))
    assert len(positives)==4
    return dict(positives=positives,normal_outputs_or_observations_not_truncated=True,
      previous_and_incomplete_evidence_hashes_verified=True)


def archive_fixtures():
    rejected=[]
    with tempfile.TemporaryDirectory()as td:
        root=Path(td);src=root/'fixture';src.mkdir()
        (src/'a').write_bytes(b'actual opaque\x1b bytes');(src/'b').write_bytes(b'unselected fully hashed')
        manifest=c.transport.pack(src,'fixture',root,32);expected={n:c.sha(src/n)for n in ('a','b')}
        positive=c.transport.audit_complete(manifest,root,root/'good',expected,{'a'})
        assert set(positive['all_original_files'])=={'a','b'}and positive['publication_addons']=={}
        for label,wants,chosen in [('missing',dict(expected,c='0'*64),{'a'}),('unknown',{'a':expected['a']},{'a'}),
          ('unselected_hash',dict(expected,b='0'*64),{'a'}),('selection',expected,{'c'})]:
            rejected.append(reject(label,lambda wants=wants,chosen=chosen,label=label:c.transport.audit_complete(manifest,root,root/label,wants,chosen)))
        import tarfile
        for label,path,kind in [('traversal','fixture/../x',tarfile.REGTYPE),('absolute','/fixture/x',tarfile.REGTYPE),
          ('backslash','fixture/\\x',tarfile.REGTYPE),('wrong_root','other/x',tarfile.REGTYPE),
          ('symlink','fixture/x',tarfile.SYMTYPE),('hardlink','fixture/x',tarfile.LNKTYPE),('noncanonical','fixture//x',tarfile.REGTYPE)]:
            entry=tarfile.TarInfo(path);entry.type=kind
            rejected.append(reject(label,lambda entry=entry:c.transport.safe_relative(entry,'fixture')))
    assert len(rejected)==11
    return dict(actual_complete_archive_positive=True,rejected=rejected,parts=c.transport.parts_controls(),
      selected_archive=c.transport.selected_archive_controls())

def permission_contract(template,active):
    """Exact reviewed workflow permission scope, independently checked on actual files."""
    assert type(template)is str and type(active)is str and active==template,'Active/template workflow differs'
    top='permissions:\n  contents: read\n  actions: read\n'
    scoped='    permissions:\n      contents: write\n      actions: read\n'
    assert template.count(top)==1,'Top-level permissions must remain read-only'
    assert template.count('jobs:\n')==1
    names=re.findall(r'^  ([a-z][a-z0-9-]*):\n',template.split('jobs:\n',1)[1],re.M)
    assert names==['source-controls','saved-capture-readback'],'Unexpected or duplicate job scope'
    controls=template.split('  source-controls:\n',1)[1].split('  saved-capture-readback:\n',1)[0]
    readback=template.split('  saved-capture-readback:\n',1)[1]
    assert not re.search(r'^\s+permissions:',controls,re.M),'Source controls must inherit read-only permissions'
    assert readback.count(scoped)==1,'Readback job requires exact contents-write/actions-read scope'
    assert re.findall(r'^[ \t]*permissions:.*$',template,re.M)==['permissions:','    permissions:'],'Unexpected permission block'
    return dict(source_controls=dict(contents='read',actions='read'),
      saved_capture_readback=dict(contents='write',actions='read'),active_template_byte_equal=True)

def permission_controls(m):
    template='.github/workflow-templates/tx-phase-reset334-tail-m4-saved-capture-cloud.yml'
    active='.github/workflows/tx-phase-reset334-tail-m4-saved-capture-cloud.yml'
    assert template in m['protected']and active in m['protected'],'Actual active/template files must both be protected'
    before=(c.ROOT/template).read_text();live=(c.ROOT/active).read_text()
    assert c.sha(c.ROOT/template)==m['protected'][template]and c.sha(c.ROOT/active)==m['protected'][active]
    proof=permission_contract(before,live)
    scoped='    permissions:\n      contents: write\n      actions: read\n'
    trials=[
      ('missing_readback_override',before.replace(scoped,'')),
      ('readback_contents_read',before.replace(scoped,scoped.replace('contents: write','contents: read'))),
      ('readback_actions_write',before.replace(scoped,scoped.replace('actions: read','actions: write'))),
      ('top_contents_write',before.replace('permissions:\n  contents: read','permissions:\n  contents: write',1)),
      ('source_controls_write',before.replace('  source-controls:\n','  source-controls:\n'+scoped,1)),
      ('wrong_job_scope',before.replace(scoped,scoped.replace('    permissions:','  permissions:',1))),
      ('duplicate_readback_permissions',before.replace(scoped,scoped+scoped))]
    refused=[]
    for name,bad in trials:
        assert bad!=before;refused.append(reject(name,lambda bad=bad:permission_contract(bad,bad)))
    refused.append(reject('active_template_mismatch',lambda:permission_contract(before,live+'\n')))
    assert len(refused)==8
    return dict(actual_file_positive=proof,refused=refused,actual_active_and_template_checked=True)


def authorization_controls(m):
    """Both actual method modes; every negative changes serialized input before invocation."""
    positive=[];refused=[]
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);path=root/'method.json';(root/'pinned.txt').write_bytes(b'fixture')
        base=copy.deepcopy(m);base['protected']={'pinned.txt':c.sha(root/'pinned.txt')}
        base.update(source_controls_authorized=True,readback_authorized=False,completed_source_controls=None)
        with mock.patch.object(c,'ROOT',root),mock.patch.object(c,'METHOD',path):
            for enabled in (False,True):
                good=copy.deepcopy(base);good.update(readback_authorized=enabled,
                  completed_source_controls={'synthetic_proof_only':True}if enabled else None)
                path.write_bytes(c.encode(good));assert c.methods()==good
                positive.append(dict(readback_authorized=enabled,actual_methods=True))
                changes=[(k,True)for k in ('native_simulation_authorized','native_extraction_authorized',
                  'geometry_generation_authorized','continuation_authorized')]
                flags=('source_controls_authorized','readback_authorized','native_simulation_authorized',
                  'native_extraction_authorized','geometry_generation_authorized','continuation_authorized')
                changes += [(k,int(good[k]))for k in flags]
                changes += [('readback_authorized',not enabled),
                  ('completed_source_controls',None if enabled else {'unexpected':True}),
                  ('original_first_fall_limit_s',63e-12),('minimum_signed_margin_v',.099)]
                assert len(changes)==14
                for index,(key,value)in enumerate(changes):
                    bad=copy.deepcopy(good);bad[key]=value
                    assert c.encode(bad)!=c.encode(good),(enabled,key,index)
                    path.write_bytes(c.encode(bad))
                    refused.append(reject(str(enabled)+':'+str(index)+':'+key,c.methods))
                path.write_bytes(c.encode(good));assert c.methods()==good
    assert len(positive)==2 and len(refused)==28
    return dict(positive=positive,refused=refused,actual_methods_in_both_modes=True,
      typed_serialized_mutations_all_changed=True,activation_or_network_performed=False)

def consumed_root_fixture():
    """Actual full controller through output save; no real archive, waveform or review collaborator."""
    with tempfile.TemporaryDirectory()as folder:
        root=Path(folder);out=root/'out';temp=root/'temp';temp.mkdir()
        case=root/'case';case.mkdir();contract={'synthetic_fixture_only':True}
        (case/'contract.json').write_bytes(c.encode(contract));(case/'bench.cir').write_text('fixture\n')
        for name in ('wave.raw','native.log','op.raw'):(case/name).write_bytes(b'fixture')
        calls=[]
        def restore(path):
            (path/'native').mkdir(parents=True)
            (path/'native/fixture.json').write_text('{}')
            calls.append(('restore',str(path)))
            return b'{}',{},dict(inventory=dict(files={'fixture':dict(bytes=2)}),transport=dict(bytes=2))
        def reconstruct(path,op,original):
            assert path==temp/'tx-current-tail-m4-saved-capture/qualified-current-OP/native'
            assert (path/'fixture.json').is_file()
            calls.append(('reconstruct',str(path)))
            return contract,'fixture\n',object(),{},{}
        diagnosis=dict(status='SYNTHETIC_GLUE_ONLY',frames={},original_failed_HBT_count=0,
          failed_hbt_same_row_extrema={},original17_current_minimum_frames={},first_fall_windows=[],
          source_bound_tail_topology={},native_pair_nodes={},native_pair_crossings={},
          pair_extrema_both_signs={},requested_fixed_samples=[])
        with (
          mock.patch.object(c,'methods',return_value=dict(readback_authorized=True)),
          mock.patch.object(c,'completed_controls',return_value=dict(synthetic=True)),
          mock.patch.object(c,'OUT',out),mock.patch.object(c.transport,'precreated',return_value={}),
          mock.patch.object(c.shutil,'disk_usage',return_value=types.SimpleNamespace(free=32*1024**3)),
          mock.patch.object(c,'snapshot',return_value=(b'{}',{},{})),
          mock.patch.object(c,'restore_capture',return_value=(case,{})),
          mock.patch.object(c.current.admission,'restore',side_effect=restore),
          mock.patch.object(c.resources,'input_budget',return_value=dict(synthetic=True)),
          mock.patch.object(c,'reconstruct',side_effect=reconstruct),
          mock.patch.object(c.prior,'validate_actual',return_value=True),
          mock.patch.object(c.observer,'actual_topology_controls',return_value={}),
          mock.patch.object(c.observer,'observe',return_value=diagnosis),
          mock.patch.dict(os.environ,dict(RUNNER_TEMP=str(temp),GITHUB_RUN_ID='1',GITHUB_SHA='a'*40)),
          mock.patch('sys.argv',['controller','--readback']),
        ):
            with contextlib.redirect_stdout(io.StringIO()):c.main()
        saved=json.loads((out/'result.json').read_bytes())
        assert saved['status']=='PASS_CURRENT_TAIL_M4_SAVED_DIAGNOSIS_ORIGINAL_ELECTRICAL_REJECTION_REMAINS'
        assert [x[0]for x in calls]==['restore','reconstruct']
        assert saved['accepted']is saved['new_simulation']is False
        assert all(c.sha(out/p)==h for p,h in saved['outputs'].items())
        return dict(actual_full_main=True,native_consumption_subdirectory_asserted=True,
          successful_stubbed_glue_not_capture_qualification=True,outputs=saved['outputs'])


def terminal_integrity_fixtures():
    positives=[]
    class BodyFailure(Exception):pass
    for mode in ('final_source','final_inventory'):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);out=root/'out';temp=root/'temp';temp.mkdir();calls=[]
            def methods():
                calls.append(True)
                if mode=='final_source'and len(calls)>1:raise AssertionError('actual source check fixture refusal')
                return dict(readback_authorized=True)
            original_sha=c.sha
            def sha(path):
                if mode=='final_inventory'and path.name=='retained-evidence.json':raise OSError('synthetic inventory hash failure')
                return original_sha(path)
            def stop(*args):
                if mode=='final_inventory':(out/'retained-evidence.json').write_bytes(b'{"partial":true}')
                raise BodyFailure('primary body fixture error')
            with (
              mock.patch.object(c,'methods',side_effect=methods),mock.patch.object(c,'sha',side_effect=sha),
              mock.patch.object(c,'completed_controls',return_value={}),
              mock.patch.object(c,'OUT',out),mock.patch.object(c.transport,'precreated',return_value={}),
              mock.patch.object(c.shutil,'disk_usage',return_value=types.SimpleNamespace(free=32*1024**3)),
              mock.patch.object(c,'snapshot',return_value=(b'',{},{})),
              mock.patch.object(c,'restore_capture',side_effect=stop),
              mock.patch.dict(os.environ,dict(RUNNER_TEMP=str(temp),GITHUB_RUN_ID='1',GITHUB_SHA='a'*40)),
              mock.patch('sys.argv',['controller','--readback']),
            ):
                try:
                    with contextlib.redirect_stdout(io.StringIO()):c.main()
                except RuntimeError as failure:
                    assert str(failure)=='Terminal source or inventory validation failed; diagnosis incomplete'
                else:raise AssertionError('Accepted terminal integrity failure')
            saved=json.loads((out/'result.json').read_bytes())
            assert saved['status']=='FAIL_CURRENT_TAIL_M4_SAVED_CAPTURE_DIAGNOSIS'
            assert saved['complete_diagnosis']is False and 'BodyFailure'in saved['error']
            assert len(saved['terminal_errors'])==1
            assert saved['terminal_errors'][0]['action']==('protected_sources'if mode=='final_source'else 'inventory')
            assert saved['accepted']is False
            positives.append(dict(case=mode,actual_main_finally=True,original_body_error_saved=True,
              complete_terminal_failure=True,terminal_errors=saved['terminal_errors']))
    return dict(positive=positives,source_or_inventory_error_never_keeps_diagnostic_PASS=True)

def controls():
    m=c.methods();permissions=permission_controls(m);closure=imports.closure(c.ROOT,m['protected'])
    raw,original,manifest=c.snapshot()
    op,opmetadata=c.current.admission.prerequisite()
    recorded=dict(run=json.loads((c.ROOT/(c.PREFIX+'.run.json')).read_bytes()),
      job=next(j for j in json.loads((c.ROOT/(c.PREFIX+'.jobs.json')).read_bytes())['jobs']if j['id']==c.SOURCE['job']),
      info=json.loads((c.ROOT/(c.PREFIX+'.release.json')).read_bytes()),
      ref=json.loads((c.ROOT/(c.PREFIX+'.tag.json')).read_bytes()))
    c.metadata(**recorded,manifest=manifest);badmeta=[]
    changes=[('run-'+k,'run',k,v)for k,v in [('id',0),('run_attempt',2),('status','in_progress'),('conclusion','success'),
      ('head_sha','0'*40),('head_branch','main'),('path','wrong')]]
    changes += [('job-'+k,'job',k,v)for k,v in [('id',0),('run_id',0),('head_sha','0'*40),('run_attempt',2),
      ('status','in_progress'),('conclusion','success')]]
    changes += [('release-'+k,'info',k,v)for k,v in [('id',0),('target_commitish','main'),('draft',True)]]
    for label,section,key,value in changes:
        q=copy.deepcopy(recorded);q[section][key]=value;assert q!=recorded
        badmeta.append(reject(label,lambda q=q:c.metadata(**q,manifest=manifest)))
    q=copy.deepcopy(recorded);q['ref']['object']['sha']='0'*40
    badmeta.append(reject('tag_sha',lambda:c.metadata(**q,manifest=manifest)))
    for key,value in [('id',0),('size',0),('digest','sha256:'+'0'*64)]:
        q=copy.deepcopy(recorded);next(a for a in q['info']['assets']if a['id']==682722333)[key]=value
        badmeta.append(reject('part_'+key,lambda q=q:c.metadata(**q,manifest=manifest)))
    q=copy.deepcopy(recorded);next(a for a in q['info']['assets']if a['id']==682721590)['size']=1
    badmeta.append(reject('summary_size',lambda:c.metadata(**q,manifest=manifest)))
    assert len(badmeta)==21
    badresult=[]
    for key,value in [('run_id',0),('source_head','0'*40),('controller_sha256','0'*64),('native_exit_code',1),
      ('native_process_saved',True),('full_capture',False),('sources_unchanged',False),('case','p-initial-low'),
      ('electrical_screen_passed',True),('full_PHY_accepted',True),('old_R_rescaled',True),
      ('new_extraction_performed',True),('geometry_generation_executed',True)]:
        q=copy.deepcopy(original);q[key]=value
        badresult.append(reject(key,lambda q=q:c.validate_result(q)))
    q=copy.deepcopy(original);q['continuation']['next_phase']='restore_and_continue'
    badresult.append(reject('continuation',lambda:c.validate_result(q)))
    q=copy.deepcopy(original);q['review']['measurement']['hbt_safety']['xdut.xd75']['passed']=False
    badresult.append(reject('unexpected_numeric_safety_failure',lambda:c.validate_result(q)))
    q=copy.deepcopy(original);q['review']['capture']['header_rows']-=1
    badresult.append(reject('capture_rows',lambda:c.validate_result(q)))
    assert len(badresult)==16
    analyze,derivation=d.analysis_program();assert analyze.__globals__['TARGETS']==d.TARGETS
    cc,payloads=synthetic_topology();topology=d.actual_topology_controls(cc,payloads)
    assert topology['target_groups']==12 and topology['passive_accesses']==168 and len(topology['rejected'])==14
    h=headroom_fixture();intervals=interval_fixture()
    mutations=[
      reject('wrong_steering_wire_sign',lambda:headroom_fixture(mutated_function('headroom',
        "-q[leaf][5]-(q[leaf][2]-c)","-q[leaf][5]+(q[leaf][2]-c)"))),
      reject('missing_left_censor',lambda:interval_fixture(mutated_function('intervals',
        "left_censored=bool(a==active[0])","left_censored=False"))),
      reject('missing_right_censor',lambda:interval_fixture(mutated_function('intervals',
        "right_censored=bool(b==len(t)-1)","right_censored=False")))]
    inherited=inherited_math.controls();assert len(inherited['rejected'])==20
    from check_tx_phase_reset334_tail_m4_saved_resources import controls as resource_controls
    resource_result=resource_controls()
    reconstruction=reconstruct_fixture()
    entry=main_entry_fixture();failure_entries=main_result_failure_fixtures()
    return dict(status='PASS_CURRENT_TAIL_M4_SAVED_CAPTURE_SOURCE_CONTROLS_ONLY',import_closure=closure,permission_controls=permissions,
      original_current_result_faults=badresult,metadata_faults=badmeta,observer_derivation=derivation,
      topology_fixture=dict(topology,real_restored_input_scope=False,synthetic_fixture_only=True),
      hand_numbered_headroom=h,interval_boundary_fixtures=intervals,actual_code_mutations=mutations,
      inherited_original_math=inherited,resource_controls=resource_result,reconstruction_completion=reconstruction,actual_main_entry=entry,actual_main_result_failures=failure_entries,authorization_controls=authorization_controls(m),terminal_integrity=terminal_integrity_fixtures(),
      actual_consumed_native_root=consumed_root_fixture(),
      archive_controls=archive_fixtures(),current_OP_admission=dict(run=op['run_id'],summary_sha256=c.current.admission.SOURCE['summary']),
      required_actual_restored_controls=dict(source=18,path=32,contract=24,topology=14),
      waveform_or_archive_input_read=False,native_simulator_invoked=False,new_geometry=False,
      original_17_and_prior_4_rejections_preserved=True,current_capture_all318_safety_passed=True,direct_complete_diagnostic_JSON_publication_required=True)
if __name__=='__main__':print(json.dumps(controls(),indent=2,allow_nan=False))
