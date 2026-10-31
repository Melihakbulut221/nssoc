#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pure current-producer checks for fresh RC; this module grants no execution authority."""
import hashlib,json,re
from pathlib import Path,PurePosixPath

RUN=41243752186
SOURCE='394b6e2c5e6fffbbc1a8d92fbdf41bd5d3a93356'
MEMBERS=665
CURRENT_PREFIX='native/view/candidate/'
CURRENT_ROOT='/home/runner/work/nssoc/nssoc/hw/soc/out/cloud-cdr-via2-m3-canonical-view/native/view/candidate'
QUALIFICATION='PASS_CANDIDATE_BOUND_CANONICAL_VIEW_REQUIRES_FRESH_RC'

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
    require(receipt['schema']=='cdr-via2-m3-canonical-view-terminal-proof-v1'and receipt['run_id']==RUN and receipt['source']==SOURCE and receipt['attempt']==1,'actual canonical producer proof')
    require(receipt['run_conclusion']=='success'and receipt['native_view_executed']is True and receipt['complete_native_members']==MEMBERS,'complete successful native view')
    require(receipt['complete_native_inventory_matches_published_index']is True and receipt['verified_derived_output_records']==116 and receipt['verified_derived_admission_records']==8,'full transport scope')
    require(receipt['whole_native_archive_locally_acquired']is False and receipt['whole_native_archive_locally_verified']is False and receipt['external_native_members_remain_cloud_only']==549,'honest native transport boundary')
    for flag in('RC_executed','simulation_executed','layout_regenerated','full_phy_accepted','electrical_accepted'):require(receipt[flag]is False,'no transferred acceptance')
    require(len(receipt['records'])+1==binding['files']==186,'complete proof census')
    for name,pin in receipt['records'].items():exact_record(root,prefix+relative(name),pin)
    return receipt

def metadata(root,p):
    receipt=complete_proof(root,p['proof']);prefix=p['proof']['prefix']
    read=lambda n:decode(exact_record(root,prefix+n,receipt['records'][n]))
    index=read('direct/complete-output-index.json');parts=read(p['parts_record']);q=read('readback/native/view/canonical-view-qualification.json')
    require(index['context']==p['index_context']and index['files']==p['complete_members']and len(index['files'])==MEMBERS,'complete current output map')
    require(parts['source_directory']==p['archive_root']and parts['bytes']==p['archive_bytes']and parts['sha256']==p['archive_sha256'],'actual archive identity')
    require(len(parts['parts'])==1 and parts['parts'][0]['index']==0 and parts['parts'][0]['bytes']==parts['bytes']and parts['parts'][0]['sha256']==parts['sha256'],'one original part')
    require(parts['verification']==dict(parts=1,bytes=parts['bytes'],sha256=parts['sha256'],all_parts_and_combined_bytes_verified=True),'original part verification')
    require(q['status']==QUALIFICATION and q['native_view_executed']is True and q['rc_extracted']is False,'new view only')
    require(q['current_files']==p['current_files']and len(q['current_files'])==q['complete_current_file_count']==78,'all current view files')
    for name,pin in q['current_files'].items():require(index['files'][CURRENT_PREFIX+relative(name)]==pin,'current view ownership')
    ni=q['native_identity'];require(ni['devices']==500 and ni['terminals']==1446 and ni['ports']==25 and ni['anchors']==978 and ni['native_nets']==238,'actual complete native scope')
    require(ni['status']=='PASS_COMPLETE_NATIVE_IDENTITIES_WITH_OBSERVED_TOPOLOGY_COUNTS'and ni['all_levels_and_instance_ordinals_and_transforms_equal']is True,'actual complete semantic identities')
    require(ni['new_native_port_order']==p['native_port_order']and ni['native_port_ids_preserved_as_evidence_not_assumed_equal']is True,'actual new port ordering')
    require(q['candidate_gds']==p['candidate_gds']and q['candidate_flat_lvs']==p['candidate_flat_lvs'],'same physical candidate')
    for group,refs in q['fresh_report_bindings'].items():
        for absolute,pin in refs.items():
            require(absolute.startswith(CURRENT_ROOT+'/'),'actual current absolute input root')
            require(q['current_files'][relative(absolute[len(CURRENT_ROOT)+1:])]==pin,'complete original absolute binding')
    return dict(index=index,parts=parts,qualification=q,run=read('run.json'),jobs=read('jobs.json'),release=read('release.json'),tag=read('tag-ref.json'))

def validate_live(p,original,run,jobs,release,tag):
    for field in('id','head_sha','head_branch','run_attempt','event','workflow_id','path','status','conclusion'):require(run[field]==original['run'][field],'immutable producer run '+field)
    require(run['id']==RUN and run['head_sha']==SOURCE and run['run_attempt']==1 and run['conclusion']=='success'and run['status']=='completed','successful exact producer')
    require(jobs['total_count']==len(jobs['jobs'])==len(original['jobs']['jobs'])==3,'complete producer jobs')
    old={j['id']:j for j in original['jobs']['jobs']};require({j['id']for j in jobs['jobs']}==set(old),'producer job identities')
    for job in jobs['jobs']:
        for field in('id','run_id','run_attempt','head_sha','name','status','conclusion','steps'):require(job[field]==old[job['id']][field],'producer terminal job '+field)
        require(job['conclusion']=='success'and all(s['conclusion']in('success','skipped')for s in job['steps']),'successful producer steps')
    require(release['id']==p['release_id']==430197123 and release['tag_name']==p['tag']and release['draft']is False and release['prerelease']is True,'exact original public prerelease')
    require(tag['object']['type']=='commit'and tag['object']['sha']==SOURCE and tag['ref']=='refs/tags/'+p['tag'],'exact immutable producer tag')
    assets={a['name']:a for a in release['assets']};require(len(assets)==len(release['assets'])==3 and set(assets)=={a['name']for a in p['assets']},'complete original assets')
    for pin in p['assets']:
        row=assets[pin['name']]
        require(row['id']==pin['id']and row['size']==pin['bytes']and row['digest']=='sha256:'+pin['sha256'],'actual original asset bytes')
        for field in('state','content_type','created_at','updated_at'):require(row[field]==pin[field],'immutable original asset '+field)
    return dict(run_id=RUN,source=SOURCE,attempt=1,release_id=430197123,members=MEMBERS,accepted=False)

def validate_restored(restore,p,full,original):
    restore=Path(restore);require(restore.is_absolute()and restore.resolve()==restore and not restore.is_symlink(),'owned original restore')
    members=p['complete_members'];require(full['every_member_authenticated']is True and full['full_member_count']==MEMBERS and full['full_members']==members and full['selected']==members,'all native archive members authenticated')
    observed={}
    for path in restore.rglob('*'):
        require(not path.is_symlink(),'no restored links')
        if path.is_file():observed[path.relative_to(restore).as_posix()]=fingerprint(path.read_bytes())
        else:require(path.is_dir(),'no restored special file')
    require(observed==members,'no omitted changed or extra restored member')
    q=decode(regular(restore,'native/view/canonical-view-qualification.json').read_bytes());require(q==original['qualification'],'original qualification retained')
    view=restore/CURRENT_PREFIX.rstrip('/');require(str(view)==CURRENT_ROOT,'restore original absolute report paths')
    for name,pin in q['current_files'].items():exact_record(view,name,pin)
    graph=decode(regular(view,'wire/native05/result.json').read_bytes());anchors=decode(regular(view,'wire/anchors08.json').read_bytes())
    require((graph['wire_component_count'],graph['native_net_count'],graph['native_electrical_net_count'],graph['native_terminal_count'],graph['native_device_count'])==(113,238,114,1446,500),'actual graph counts')
    require((anchors['logical_anchor_count'],anchors['physical_anchor_count'],anchors['public_ports'])==(978,978,25)and anchors['point_quantization_used_to_merge']is False,'actual complete anchors')
    require(graph['wire_rc_extracted']is anchors['wire_rc_extracted']is False,'no old RC promoted')
    return dict(source=SOURCE,run_id=RUN,complete_members=MEMBERS,current_files=78,current_view=str(view),original_bytes_unchanged=True,RC_executed=False,electrical_accepted=False)

if __name__=='__main__':
    raise SystemExit('Producer validation library only; native execution has no standalone authority')
