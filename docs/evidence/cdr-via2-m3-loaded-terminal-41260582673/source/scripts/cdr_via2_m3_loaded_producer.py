#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pure current-producer checks for loaded nominal_late; this module grants no execution authority."""
import hashlib,json,re
from pathlib import Path,PurePosixPath

RUN=41251732540
SOURCE='9bf12d1e496f7d9192582175ab2fa714e3e8d41b'
MEMBERS=3091
CURRENT_ROOT='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-via2-m3-fresh-rc'
QUALIFICATION='PASS_CURRENT_VIA2_M3_FRESH_RC_NUMERICAL_QUALIFICATION_REQUIRES_LOADED_WAVES'

def require(ok,message):
    if not ok:raise RuntimeError(message)

def fingerprint(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def decode(raw):
    def unique(pairs):
        out={}
        for k,v in pairs:
            require(k not in out,'duplicate JSON key');out[k]=v
        return out
    def nonfinite(value):raise RuntimeError('nonfinite JSON value '+value)
    return json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=nonfinite)

def relative(name):
    require(isinstance(name,str) and name and not name.startswith('/') and chr(92) not in name, 'relative POSIX record')
    require(all(p not in('','.','..')for p in name.split('/'))and PurePosixPath(name).as_posix()==name,'canonical relative record')
    return name

def regular(root,name):
    root=Path(root);require(root.is_absolute()and root.resolve()==root and root.is_dir()and not root.is_symlink(),'real owned root')
    path=root/relative(name)
    for p in(path,*path.parents):
        require(not p.is_symlink(),'symlink refused')
        if p==root:break
    require(path.is_file()and path.resolve().is_relative_to(root),'regular owned record')
    return path

def exact_record(root,name,pin):
    require(set(pin)>={'bytes','sha256'}and type(pin['bytes'])is int and pin['bytes']>=0 and re.fullmatch('[0-9a-f]{64}',pin['sha256']),'complete byte pin')
    raw=regular(root,name).read_bytes();require(fingerprint(raw)=={k:pin[k]for k in('bytes','sha256')},'record bytes changed '+name)
    if 'canonical_object_sha256'in pin:
        canonical=json.dumps(decode(raw),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        require(hashlib.sha256(canonical).hexdigest()==pin['canonical_object_sha256'],'canonical object changed '+name)
    return raw


def complete_proof(root,binding):
    prefix=binding['prefix'];require(prefix.endswith('/'),'proof prefix')
    raw=exact_record(root,prefix+'receipt.json',binding['receipt']);receipt=decode(raw)
    require(receipt['schema']=='complete-current-via2-m3-fresh-rc-terminal-proof-v1'and receipt['run_id']==RUN and receipt['run']==RUN and receipt['source']==SOURCE and receipt['attempt']==1,'actual fresh RC producer proof')
    require(receipt['conclusion']=='success'and receipt['native_execution_success']is True and receipt['complete_native_members']==MEMBERS,'successful actual fresh RC')
    for key,value in dict(full_job_logs=3,source_capsules=47,source_control_primary_records=3,source_control_fixture_records=95,actual_derived_records=274,admission_derived_records=8).items():require(receipt[key]==value,'complete proof scope '+key)
    for flag in('native_archive_acquired_locally','loaded_simulation_executed','qualified_pex','electrical_accepted','full_phy_accepted'):require(receipt[flag]is False,'honest proof scope '+flag)
    require(len(receipt['files'])+1==binding['files']==454,'complete proof census')
    total=len(raw)
    for name,pin in receipt['files'].items():total+=len(exact_record(root,prefix+relative(name),pin))
    require(total==binding['bytes'],'complete proof bytes')
    return receipt

def metadata(root,p):
    require(p['schema']=='cdr-via2-m3-loaded-current-producer-inputs-v1','producer input schema')
    require(p['producer_run_id']==RUN and p['producer_source']==SOURCE and p['producer_attempt']==1 and p['loaded_case_scope']=='nominal_late','exact original RC and loaded case')
    for flag in('native_authorization_asserted_by_this_record','qualified_pex','electrical_accepted','full_phy_accepted'):require(p[flag]is False,'no transferred authority '+flag)
    receipt=complete_proof(root,p['proof']);prefix=p['proof']['prefix']
    read=lambda n:decode(exact_record(root,prefix+n,receipt['files'][n]))
    index=read('direct/complete-output-index.json');parts=read(p['parts_record'])
    require(index['context']==p['index_context']and index['files']==p['complete_members']and len(index['files'])==MEMBERS,'complete actual RC output map')
    require(parts['source_directory']==p['archive_root']and parts['bytes']==p['archive_bytes']and parts['sha256']==p['archive_sha256'],'actual RC archive identity')
    require(len(parts['parts'])==1 and parts['parts'][0]['index']==0 and parts['parts'][0]['bytes']==parts['bytes']and parts['parts'][0]['sha256']==parts['sha256'],'one exact original part')
    require(parts['verification']==dict(parts=1,bytes=parts['bytes'],sha256=parts['sha256'],all_parts_and_combined_bytes_verified=True),'original part verification')
    reports={}
    require(len(p['required_reports'])==34,'complete required report scope')
    for name,pin in p['required_reports'].items():
        require(index['files'][relative(name)]=={k:pin[k]for k in('bytes','sha256')},'report inventory ownership '+name)
        require(receipt['files'][pin['proof_path']]=={k:pin[k]for k in('bytes','sha256')},'report proof ownership '+name)
        reports[name]=decode(exact_record(root,prefix+relative(pin['proof_path']),pin))
    for key in('model','composition','planes'):
        pin=p[key];require(index['files'][relative(pin['path'])]=={k:pin[k]for k in('bytes','sha256')},'original '+key+' identity')
    q=reports['fresh-rc-qualification.json'];result=reports['result.json']
    ctx=dict(source=SOURCE,run_id=RUN,attempt=1)
    require(q['status']==QUALIFICATION and q['context']==ctx and q['execution_scope']=='ACTUAL_AUTHORIZED_NATIVE_PHASE'and q['fresh_RC_pipeline_complete']is True,'actual numerical RC qualification')
    require(q['counts']==p['actual_numerical_counts']==dict(devices=500,R=24360,C=15568),'actual observed RC counts')
    for flag in('qualified_pex','electrical_accepted','full_phy_accepted','loaded_simulation_passed'):require(q[flag]is False,'no electrical acceptance '+flag)
    phases={'prepare','binding-export','binding-validate','wire-audit','compose'}|{phase+'-'+variant for phase in('mim-generate','mim-finish','mim-audit')for variant in('precise','precise_reversed')}
    require(set(q['phase_receipts'])==phases and len(phases)==11,'all actual phase receipts')
    for label,pin in q['phase_receipts'].items():
        path='native-phase-reports/'+label+'.json';phase=reports[path]
        require(index['files'][path]==pin and phase['status']=='PASS_PHASE'and phase['label']==label and phase['context']==ctx and phase['execution_scope']=='ACTUAL_AUTHORIZED_NATIVE_PHASE','actual completed phase '+label)
    require(result['status']=='PASS_CURRENT_VIA2_M3_FRESH_RC_REQUIRES_UNCHANGED_ELECTRICAL_WAVES'and result['qualification']==q,'complete original root result')
    require(result['original_absolute_proofs_retained']is True and result['complete_view_producer_members']==665 and result['current_view_files']==78,'original view proofs retained')
    for flag in('electrical_accepted','full_phy_accepted','physical_accepted','qualified_pex','simulation_executed','layout_regenerated','original_electrical_rejection_overridden'):require(result[flag]is False,'no transferred root acceptance '+flag)
    comp=reports[p['composition']['path']];planes=reports[p['planes']['path']]
    require(comp['counts']==q['counts']and len(comp['device_records'])==500 and len(comp['wire_node_map'])==15489,'complete actual composition')
    require(len(comp['interface'])==len(set(comp['interface']))==26 and comp['interface'][-1]=='wire_cref','actual public semantic interface')
    require(comp['intrinsic_mim_models_in_final_netlist']==len(comp['native_extracted_mim_cards_projected_once'])==7 and comp['explicit_mim_device_estimate_double_count_removed']is True and comp['all_raw_wire_tokens_preserved']is True,'actual MIM and wire separation')
    require(comp['qualified_pex']is False and comp['mim_device_wire_capacitance_separation_qualified']is False,'no qualified PEX claimed')
    require(planes['status']=='PASS_PD500_NATIVE160_PLANES_51_NETS_19_FAULTS'and len(planes['anchors'])==160 and planes['native_terminal_count']==1446,'actual complete native planes')
    dp=p['derived_loaded_projection'];projection=decode(exact_record(root,prefix+relative(dp['proof_path']),dp))
    require(projection['source']==SOURCE and projection['run_id']==RUN and projection['counts']==dp['counts'],'derived projection identity')
    require(projection['contract']==p['composition']and {k:projection['native_planes'][k]for k in('path','bytes','sha256')}==p['planes'],'projection original owners')
    require(projection['native_model_card_validation_executed']is False and projection['loaded_simulation_executed']is False and dp['actual_loaded_run_executed']is False,'projection is not a loaded simulation')
    require(len(projection['voltage_nodes'])==977 and len(projection['hbt_current_instances'])==124 and len(projection['mos_current_instances'])==50 and len(projection['vectors'])==len(set(projection['vectors']))==1151,'derived vector census')
    require(len(projection['terminals'])==1446 and len(projection['aliases'])==16 and projection['aliases_are_terminal_nodes']is True,'complete derived terminal and alias projection')
    return dict(index=index,parts=parts,qualification=q,reports=reports,projection=projection,run=read('run.json'),jobs=read('jobs.json'),release=read('release.json'),tag=read('tag-ref.json'))

def validate_live(p,original,run,jobs,release,tag):
    for field in('id','head_sha','head_branch','run_attempt','event','workflow_id','path','status','conclusion'):require(run[field]==original['run'][field],'immutable producer run '+field)
    require(run['id']==RUN and run['head_sha']==SOURCE and run['run_attempt']==1 and run['conclusion']=='success'and run['status']=='completed','successful exact producer')
    require(jobs['total_count']==len(jobs['jobs'])==len(original['jobs']['jobs'])==3,'complete producer jobs')
    old={j['id']:j for j in original['jobs']['jobs']};require({j['id']for j in jobs['jobs']}==set(old),'producer job identities')
    for job in jobs['jobs']:
        for field in('id','run_id','run_attempt','head_sha','name','status','conclusion','steps'):require(job[field]==old[job['id']][field],'producer terminal job '+field)
        require(job['conclusion']=='success'and all(s['conclusion']in('success','skipped')for s in job['steps']),'successful producer steps')
    require(release['target_commitish']==SOURCE==original['release']['target_commitish'],'immutable producer release target')
    require(release['id']==p['release_id']==430243359 and release['tag_name']==p['tag']and release['draft']is False and release['prerelease']is True,'exact original public prerelease')
    require(tag['object']['type']=='commit'and tag['object']['sha']==SOURCE and tag['ref']=='refs/tags/'+p['tag'],'exact immutable producer tag')
    assets={a['name']:a for a in release['assets']};require(len(assets)==len(release['assets'])==3 and set(assets)=={a['name']for a in p['assets']},'complete original assets')
    for pin in p['assets']:
        row=assets[pin['name']]
        require(row['id']==pin['id']and row['size']==pin['bytes']and row['digest']=='sha256:'+pin['sha256'],'actual original asset bytes')
        for field in('state','content_type','created_at','updated_at'):require(row[field]==pin[field],'immutable original asset '+field)
    return dict(run_id=RUN,source=SOURCE,attempt=1,release_id=430243359,members=MEMBERS,accepted=False)


def validate_restored(restore,p,full,original):
    restore=Path(restore)
    require(restore.is_absolute()and restore.resolve()==restore and not restore.is_symlink()and str(restore)==CURRENT_ROOT==p['original_output_root'],'owned original absolute RC restore')
    members=p['complete_members']
    require(full['every_member_authenticated']is True and full['full_member_count']==MEMBERS and full['full_members']==members and full['selected']==members,'all original native archive members authenticated')
    observed={}
    for path in restore.rglob('*'):
        require(not path.is_symlink(),'no restored links')
        if path.is_file():observed[path.relative_to(restore).as_posix()]=fingerprint(path.read_bytes())
        else:require(path.is_dir(),'no restored special file')
    require(observed==members,'no omitted changed or extra restored member')
    for name,pin in p['required_reports'].items():require(decode(exact_record(restore,name,pin))==original['reports'][name],'original report retained '+name)
    for key in('model','composition','planes'):
        pin=p[key];exact_record(restore,pin['path'],pin)
    return dict(source=SOURCE,run_id=RUN,complete_members=MEMBERS,model=dict(p['model']),composition=dict(p['composition']),planes=dict(p['planes']),original_root=str(restore),original_bytes_unchanged=True,loaded_simulation_executed=False,electrical_accepted=False)

if __name__=='__main__':
    raise SystemExit('Producer validation library only; no standalone loaded execution authority')
