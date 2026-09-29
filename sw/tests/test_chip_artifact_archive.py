# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import archive_chip_run_artifacts as archive


def plan():
    return dict(source_run=123, source_commit='a'*40,
                source_branch='codex/complete-open-work',
                source_workflow='.github/workflows/chip-ring-offset-fill.yml',
                source_event='push', artifacts=[dict(artifact_name='fill-result', asset_name='fill.zip')])


def producer():
    p = plan()
    return dict(id=p['source_run'], head_sha=p['source_commit'],
                head_branch=p['source_branch'], path=p['source_workflow'], event='push',
                repository=dict(full_name=archive.REPO), head_repository=dict(full_name=archive.REPO),
                status='completed', conclusion='success')


def listing():
    return dict(total_count=1, artifacts=[dict(id=42, name='fill-result', expired=False,
                size_in_bytes=20, digest='sha256:'+'b'*64,
                workflow_run=dict(id=123, head_sha='a'*40, head_branch='codex/complete-open-work'))])


def test_only_exact_successful_producer_and_artifact_are_selected():
    p = archive.validate_plan(plan())
    assert archive.producer_ready(producer(), p)
    row = archive.resolve_artifacts(listing(), p)[0]
    assert (row['source_artifact_id'], row['name'], row['bytes'], row['sha256']) == (42, 'fill.zip', 20, 'b'*64)
    waiting = producer()
    waiting.update(status='in_progress', conclusion=None)
    assert not archive.producer_ready(waiting, p)


@pytest.mark.parametrize('defect', ['path', 'duplicate_source', 'duplicate_destination', 'boolean_id', 'commit', 'event'])
def test_invalid_plan_is_rejected_before_network_or_publication(defect):
    p = plan()
    if defect == 'path': p['artifacts'][0]['asset_name'] = '../fill.zip'
    elif defect.startswith('duplicate'):
        row = copy.deepcopy(p['artifacts'][0])
        row['asset_name' if defect == 'duplicate_source' else 'artifact_name'] = 'different.zip' if defect == 'duplicate_source' else 'different'
        p['artifacts'].append(row)
    elif defect == 'boolean_id': p['source_run'] = True
    elif defect == 'commit': p['source_commit'] = 'main'
    else: p['source_event'] = 'pull_request'
    with pytest.raises(ValueError): archive.validate_plan(p)


@pytest.mark.parametrize('defect', ['commit', 'branch', 'workflow', 'fork', 'run', 'failure', 'cancelled'])
def test_wrong_or_unsuccessful_producer_cannot_authorize_archiving(defect):
    source = producer()
    if defect == 'commit': source['head_sha'] = 'c'*40
    elif defect == 'branch': source['head_branch'] = 'codex/another'
    elif defect == 'workflow': source['path'] = '.github/workflows/unrelated.yml'
    elif defect == 'fork': source['head_repository']['full_name'] = 'other/fork'
    elif defect == 'run': source['id'] = 124
    else: source['conclusion'] = defect
    with pytest.raises(ValueError): archive.producer_ready(source, plan())


@pytest.mark.parametrize('defect', ['expired', 'digest', 'size', 'other_run', 'other_commit', 'duplicate', 'incomplete', 'missing'])
def test_ambiguous_or_unbound_artifact_is_rejected(defect):
    value = listing()
    row = value['artifacts'][0]
    if defect == 'expired': row['expired'] = True
    elif defect == 'digest': row['digest'] = None
    elif defect == 'size': row['size_in_bytes'] = True
    elif defect == 'other_run': row['workflow_run']['id'] = 124
    elif defect == 'other_commit': row['workflow_run']['head_sha'] = 'c'*40
    elif defect == 'duplicate': value['artifacts'].append(copy.deepcopy(row)); value['total_count'] = 2
    elif defect == 'incomplete': value['total_count'] = 2
    else: row['name'] = 'not-requested'
    with pytest.raises(ValueError): archive.resolve_artifacts(value, plan())
