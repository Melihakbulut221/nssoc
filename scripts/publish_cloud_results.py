#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Publish immutable results to a separate release per hosted run and job group."""
import argparse
import json
import os
from pathlib import Path
import re
from migrate_outputs_to_cloud import publish


def result_tag(group, env):
    if env.get('GITHUB_ACTIONS') != 'true':
        raise ValueError('Hosted publication requires GitHub Actions context')
    run, attempt = env['GITHUB_RUN_ID'], env['GITHUB_RUN_ATTEMPT']
    if not re.fullmatch(r'[0-9]+', run) or not re.fullmatch(r'[0-9]+', attempt):
        raise ValueError('Invalid run identity')
    if not re.fullmatch(r'[a-z0-9_-]{1,80}', group):
        raise ValueError('Invalid job group')
    return f'cloud-results-{run}-{attempt}-{group}'


def publish_results(group, paths):
    tag = result_tag(group, os.environ)
    return dict(tag=tag, assets=[publish(Path(path), tag) for path in paths])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--group', required=True)
    parser.add_argument('paths', nargs='+')
    args = parser.parse_args()
    print(json.dumps(publish_results(args.group, args.paths)), flush=True)
