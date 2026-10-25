#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted logical archive roundtrips around the exact bounded native checkpoint."""
import json,os
from pathlib import Path
import cloud_logical_native_archive as logical
import cloud_native_sparse_prefix_store as sparse
import cloud_streamed_native_archive as archive
from publish_cloud_results import result_tag
from migrate_outputs_to_cloud import publish
from route_cloud_newer_postcts import fetch

def files(root):
    return {str(p.relative_to(root)):archive.sha(p)for p in root.rglob('*')if p.is_file()}

def hosted(directory,member,prefix,contract,plan,out,stop_check,group):
    out.mkdir(exist_ok=False);stage=out/'stage';stage.mkdir()
    tag=result_tag(group,os.environ);stem=group+'-'+os.environ['GITHUB_RUN_ID']
    packed=logical.stream_pack(directory,stem,stage,lambda p:publish(p,tag),
        {member:dict(source=contract,plan=plan,open_source=lambda:logical.file_chunks(prefix))},
        stop_check,4*1024*1024)
    receipt=publish(stage/(stem+'.parts.json'),tag)
    receipts={r['name']:r for r in packed['hosted_receipts']}
    def get(row,path):fetch(receipts[row['name']]['url'],row['sha256'],path)
    return packed,receipt,get

def checkpoint_roundtrip(source,contract,out,stop_check):
    source=Path(source);out=Path(out);raw=source/'resumed/actual-acquisition.raw'
    prefix=source/'checkpoint-prefix.raw'
    assert stop_check()is True and archive.sha(raw)==contract['sha256']==archive.sha(prefix)
    expected=files(source);assert expected
    temp=raw.parent/'new-owned-sparse.raw'
    plan=sparse.materialize(temp,logical.file_chunks(prefix),contract,sparse.BLOCK,sparse.BLOCK)
    temp.replace(raw)
    packed,receipt,get=hosted(source,'resumed/actual-acquisition.raw',prefix,contract,plan,
        out,stop_check,'native-logical-checkpoint-capsule')
    assert packed['verification']['logical_members']['resumed/actual-acquisition.raw']['sha256']==expected['resumed/actual-acquisition.raw']
    # Keep the original cloud copy for failure evidence. A new empty target is
    # mandatory; no native process is started until all archive parts and files
    # have been checked after restoration at the checkpoint's original paths.
    backup=out/'before-hosted-restore';assert not backup.exists()
    source.rename(backup)
    proof=logical.extract_sparse(packed,out/'download',source.parent,get,
        {'resumed/actual-acquisition.raw':dict(source=contract,head_keep=sparse.BLOCK,tail_keep=sparse.BLOCK)})
    logical_proof=sparse.inspect_logical(raw,logical.file_chunks(prefix),
        proof['plans']['resumed/actual-acquisition.raw'],contract)
    observed=files(source);observed['resumed/actual-acquisition.raw']=logical_proof['sha256']
    assert observed==expected and stop_check()is True
    result=dict(manifest=receipt,archive_sha256=packed['sha256'],parts=len(packed['parts']),
        restore=proof,logical=logical_proof,all_checkpoint_runtime_reference_files_byte_exact=True,
        original_source_backup_retained=True,files=expected,native_activation_performed=False)
    (out/'roundtrip.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def completed_roundtrip(case,prefix,contract,plan,out,stop_check):
    case=Path(case);out=Path(out);prefix=Path(prefix)
    assert stop_check()is True
    expected=files(case)
    packed,receipt,get=hosted(case,'actual-acquisition.raw',prefix,contract,plan,
        out,stop_check,'native-logical-completed-capture')
    target=out/'ordinary-restored'
    proof=archive.extract_verified(packed,out/'download',target,get)
    restored=target/case.name
    expected['actual-acquisition.raw']=packed['verification']['logical_members']['actual-acquisition.raw']['sha256']
    assert files(restored)==expected and stop_check()is True
    result=dict(manifest=receipt,archive_sha256=packed['sha256'],parts=len(packed['parts']),
        ordinary_restore=proof,all_completed_native_files_byte_exact=True,
        logical_raw=packed['verification']['logical_members']['actual-acquisition.raw'])
    (out/'roundtrip.json').write_text(json.dumps(result,indent=2)+'\n')
    return restored,result
