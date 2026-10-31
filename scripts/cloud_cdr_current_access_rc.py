#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read four authentic RC networks on a hosted runner, preserving original rejection."""
import argparse,copy,json,os,shutil,subprocess,tempfile,traceback
from pathlib import Path
import cloud_cdr_current_eight_drain_wave_replay as q
import cdr_current_access_rc as analysis
ROOT=Path(__file__).resolve().parents[1]
BRANCH='codex/cdr-current-access-rc-readback'
CONFIG='scripts/cdr-current-access-rc-inputs.json'
MANIFEST='scripts/cdr-current-access-rc-source-pins.json'
GROUP='cdr-current-access-rc-readback'
FLAGS=dict(accepted=False,electrical_accepted=False,timing_accepted=False,full_phy_accepted=False,physical_acceptance=False,qualified_pex=False,new_simulation=False,geometry_changed=False,causality_proven=False)
require=q.require
encode=q.encode

def context(env,case=None):
    require(env.get('GITHUB_ACTIONS')=='true'and env.get('GITHUB_EVENT_NAME')=='workflow_dispatch','hosted manual only')
    require(env.get('GITHUB_REPOSITORY')==q.REPOSITORY and env.get('GITHUB_REF')=='refs/heads/'+BRANCH,'repository/branch')
    require(env.get('GITHUB_RUN_ATTEMPT')=='1','attempt one')
    source=env.get('GITHUB_SHA','');run=env.get('GITHUB_RUN_ID','')
    require(q.re.fullmatch('[0-9a-f]{40}',source)and q.re.fullmatch('[1-9][0-9]*',run),'source/run')
    c=dict(source=source,run_id=int(run),attempt=1)
    if case is not None:
        require(case=='nominal_late','one pinned existing case')
        c.update(case=case,group=GROUP+'-'+case,token=run+'-1')
    return c

def source_guard(root=ROOT):
    c=q.decode(q.regular(root,CONFIG).read_bytes())
    require(c['schema']=='cdr-current-access-rc-inputs-v1'and c['branch']==BRANCH and c['case']=='nominal_late','collector identity')
    require(c['source_controls_authorized']is True and type(c['readback_authorized'])is bool,'typed authority')
    require(c['all_acceptance_false']is True and c['native_simulation']is False,'collector scope')
    prior=q.source_guard(root)
    require(q.fingerprint(q.regular(root,q.CONFIG).read_bytes())['sha256']==c['qualified_case_reader']['sha256'],'qualified reader config')
    require(prior['producer']==c['original_producer'],'same original producer')
    return c

def checkout_binding(ctx,c,root=ROOT):
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==ctx['source'],'exact current checkout')
    raw=q.regular(root,MANIFEST).read_bytes()
    require(raw==subprocess.check_output(['git','show',ctx['source']+':'+MANIFEST],cwd=root),'manifest changed')
    m=q.decode(raw);require(m['schema']=='cdr-current-access-rc-source-pins-v1','manifest schema')
    for path,pin in m['files'].items():require(q.file_pin(q.regular(root,path))==pin,'source changed: '+path)
    require(m['readback_authorized']is c['readback_authorized'],'authority consistent')
    analysis.solver_source_guard(root/c['linear_solver']['path'])
    require(q.file_pin(root/c['linear_solver']['path'])['sha256']==c['linear_solver']['sha256'],'original solver source')
    return dict(manifest=q.fingerprint(raw),files=m['files'],source=ctx['source'])

def controls_binding(raw,ctx):
    r=q.decode(raw)
    require(r['status']=='PASS_CDR_CURRENT_ACCESS_RC_SOURCE_CONTROLS'and r['passed']is True,'source controls status')
    require(r['current_context']==dict(source=ctx['source'],run_id=ctx['run_id'],attempt=1),'same-source controls')
    require(r['actual_native_acquired']is False and r['physical_acceptance']is False,'source control scope')
    require(r['inherited_counts']==dict(groups=10,refusals=86,lifecycle=4)and r['sampler_test_methods']==6,'qualified reader controls')
    require(r['access_test_methods']==12 and r['access_tests_successful']is True,'complete new RC controls')
    return q.fingerprint(raw)

def graph_binding(c,root):
    g=q.decode(q.regular(root,c['graph']['path']).read_bytes())
    require(q.file_pin(root/c['graph']['path'])=={k:c['graph'][k]for k in ('bytes','sha256')},'complete graph evidence bytes')
    bound=[]
    for t in c['targets']:
        rows=[x for x in g['records']if x['new_component']==t['component']]
        require(rows and all(x['new_native_cluster']==t['native_cluster']and x['partition']==t['partition']for x in rows),'full graph target partition')
        bound.append(dict(component=t['component'],native_cluster=t['native_cluster'],partition=t['partition'],material_records=rows))
    return bound

def perform(ctx,reserved,controls_raw,out,c,root=ROOT,api_call=q.api,fetch=q.download):
    require(c['readback_authorized']is True,'readback disabled')
    binding=checkout_binding(ctx,c,root);controls=controls_binding(controls_raw,ctx)
    q.write_new(out/'current-source-binding.json',encode(binding));q.write_new(out/'source-controls.json',controls_raw)
    tag='cloud-results-'+ctx['token']+'-'+ctx['group']
    fresh=q.reservation(ctx,reserved,api_call('releases/tags/'+tag),api_call('git/ref/tags/'+tag))
    q.write_new(out/'reservation.json',encode(fresh))
    prior=q.source_guard(root);case=c['case'];e=prior['cases'][case]
    def live(suffix):
        run=api_call('actions/runs/'+str(prior['producer']['run_id']))
        jobs=api_call('actions/runs/'+str(prior['producer']['run_id'])+'/attempts/1/jobs?per_page=100')
        release=api_call('releases/'+str(e['release_id']));ref=api_call('git/ref/tags/'+e['tag'])
        for name,obj in (('run',run),('jobs',jobs),('release',release),('ref',ref)):q.write_new(out/('producer-'+name+suffix+'.json'),encode(obj))
        result=q.validate_current_case_live(prior,case,run,jobs,release,ref)
        q.write_new(out/('live-binding'+suffix+'.json'),encode(result));return result
    producer=live('');summary,parts,report=q.metadata(prior,case,root)
    require(all(summary['outputs'].get(k)==v for k,v in c['selected'].items()),'selected current model inventory')
    require(not any('wave.raw'in k or k.endswith(('.gds','.mag','.gz'))for k in c['selected']),'no waveform/layout selection')
    for suffix,key in (('summary','summary_path'),('parts','parts_path'),('native-result','report_path'),('original-publication','publication_path')):q.write_new(out/('producer-'+suffix+'.json'),q.pinned(prior,root,e[key]))
    graph=graph_binding(c,root);q.write_new(out/'graph-target-partitions.json',encode(graph))
    require(shutil.disk_usage(out.parent).free>=parts['bytes']+2*1024**3,'runner space')
    primary=None;temp=tempfile.TemporaryDirectory(prefix='cdr-access-rc-',dir=out.parent)
    try:
        work=Path(temp.name);archive,transport=q.acquire(prior,case,parts,work,fetch)
        q.write_new(out/'transport-proof.json',encode(transport))
        full=q.select_archive(archive,summary['outputs'],list(c['selected']),parts['source_directory'],work/'selected')
        q.write_new(out/'complete-input-census.json',encode(full));saved=work/'selected'
        def raw(key):return q.regular(saved,c['members'][key]).read_bytes()
        def js(key):return q.decode(raw(key))
        require(q.regular(saved,e['report_member']).read_bytes()==q.pinned(prior,root,e['report_path']),'actual archived native report')
        require(q.file_pin(q.regular(saved,'result.json'))=={k:summary['raw_terminal'][k]for k in ('bytes','sha256')},'original raw outer result')
        contract=js('composition');require(contract['counts']==c['expected_counts'],'actual counts')
        numeric=q.load_numeric(prior,root);q.validate_binding(numeric,report,contract,js('planes'),raw('model').decode())
        edges,projection=analysis.bind_wire_projection(raw('model').decode(),raw('wires').decode(),contract)
        census=analysis.networks(edges,contract,js('anchors'),js('geometry'),c['targets'])
        nodes={n for edge in census['edges']for n in edge['nodes']}
        locations=analysis.native_locations([(Path(c['members'][k]).name,raw(k).decode())for k in ('ext','res_ext')],nodes)
        solutions=analysis.evaluate(census)
        q.write_new(out/'complete-target-networks.json',encode(census))
        q.write_new(out/'exact-native-node-records.json',encode(locations))
        q.write_new(out/'linear-wire-solutions.json',encode(solutions))
        q.write_new(out/'global-wire-projection.json',encode(projection))
        q.write_new(out/'native-rc-result.json',raw('rc_result'))
        q.write_new(out/'geometry-source-binding.json',encode(dict(input_pins={k:full['selected'][v]for k,v in c['members'].items()},graph=c['graph'],geometry_status=js('geometry').get('status'),read_only=True,**FLAGS)))
        for name in c['selected']:require(q.file_pin(q.regular(saved,name))==full['selected'][name],'selected bytes changed')
        live('-after');source_guard(root);checkout_binding(ctx,c,root)
        return dict(status='PASS_AUTHENTIC_CURRENT_FOUR_NET_RC_READBACK_ONLY',context=ctx,producer=producer,controls=controls,complete_input_members=full['full_member_count'],selected_members=len(full['selected']),global_counts=projection['counts'],target_nets=len(census['networks']),incident_edges=len(census['edges']),pairwise_DC_evaluations=len(solutions['evaluations']),unresolved_coordinate_nodes=len(locations['unresolved_coordinate_nodes']),original_electrical_status=report['status'],original_rejection_preserved=True,**FLAGS)
    except BaseException as error:primary=error;raise
    finally:
        try:temp.cleanup()
        except BaseException as error:
            q.preserve_error(out,'cleanup-error.json',error,primary)
            if primary is None:raise

def run(ctx,reserved,controls_raw,out,root=ROOT,api_call=q.api,fetch=q.download):
    require(not out.exists()and not out.is_symlink(),'output no overwrite');out.mkdir(parents=True);primary=None
    try:
        c=source_guard(root);result=perform(ctx,reserved,controls_raw,out,c,root,api_call,fetch)
        q.write_new(out/'readback-result.json',encode(result));return result
    except BaseException as error:
        primary=error
        failure=dict(status='FAIL_CURRENT_FOUR_NET_RC_READBACK',context=ctx,error=repr(error),traceback=traceback.format_exc(),**FLAGS)
        try:q.write_new(out/'readback-failure.json',encode(failure))
        except BaseException as secondary:print(encode(dict(failure,save_error=repr(secondary))).decode(),flush=True)
        for name in (CONFIG,MANIFEST,'scripts/cloud_cdr_current_access_rc.py','scripts/cdr_current_access_rc.py'):
            try:q.write_new(out/('retained-source/'+name),q.regular(root,name).read_bytes())
            except BaseException as secondary:q.preserve_error(out,'retain-'+Path(name).name+'.error.json',secondary,error)
        raise
    finally:
        try:q.emit(out)
        except BaseException as error:
            q.preserve_error(out,'emission-error.json',error,primary)
            if primary is None:raise

def main():
    p=argparse.ArgumentParser();p.add_argument('--readback',action='store_true',required=True);p.add_argument('--case',choices=['nominal_late'],required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reservation',type=Path,required=True);p.add_argument('--controls-proof',type=Path,required=True);a=p.parse_args()
    ctx=context(os.environ,a.case);run(ctx,q.decode(q.regular(a.reservation.parent,a.reservation.name).read_bytes()),q.regular(a.controls_proof.parent,a.controls_proof.name).read_bytes(),a.output)
if __name__=='__main__':main()
