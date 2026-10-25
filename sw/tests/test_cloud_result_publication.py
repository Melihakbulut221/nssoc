# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Keep parallel results isolated and reject ambiguous publication identities."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from publish_cloud_results import result_tag


def test_parallel_jobs_attempts_and_runs_have_distinct_destinations():
    tags = {result_tag(group, dict(GITHUB_ACTIONS='true', GITHUB_RUN_ID=run,
            GITHUB_RUN_ATTEMPT=attempt))
            for group in ('tx-4', 'tx-8', 'route-local_optimize')
            for run in ('123', '124') for attempt in ('1', '2')}
    assert len(tags) == 12


@pytest.mark.parametrize('changes,group', [
    ({'GITHUB_ACTIONS': 'false'}, 'tx-4'),
    ({'GITHUB_RUN_ID': '../123'}, 'tx-4'),
    ({'GITHUB_RUN_ATTEMPT': '1/2'}, 'tx-4'),
    ({}, '../unsafe'), ({}, ''), ({}, 'x' * 81)])
def test_reject_unsafe_or_nonhosted_identity(changes, group):
    env = dict(GITHUB_ACTIONS='true', GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='1')
    env.update(changes)
    with pytest.raises(ValueError):
        result_tag(group, env)
