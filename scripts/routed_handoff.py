#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Hand a LibreLane design state from one hosted job to the next.

docs/combined-timing.md, routed measurement. `pack RUN STATE_OUT TAR [--odb
ODB] [EXTRA...]`: take the state after the last step of RUN, optionally replace its database, write it
as STATE_OUT, and archive STATE_OUT, every file the state names and the
EXTRA paths with absolute paths, so `tar -xzf TAR -C /` on the next runner
(same workspace path) restores them where the state and the configuration
expect them. Nothing outside the workspace is archived.
"""
import json
import os
import sys
import tarfile
from pathlib import Path


def latest_state(run):
    """The state after the last step that ran (its state_out is cumulative)."""
    def number(path):
        head = path.parent.name.split('-', 1)[0]
        return int(head) if head.isdigit() else -1
    states = sorted(Path(run).glob('*/state_out.json'), key=number)
    if not states:
        raise SystemExit(f'no step state in {run}')
    state = json.loads(states[-1].read_text())
    if not state.get('odb'):
        raise SystemExit(f'no database in {states[-1]}')
    print('state of', states[-1].parent.name)
    return state


def files_of(value):
    if isinstance(value, str):
        if os.path.isabs(value) and Path(value).exists():
            yield Path(value)
    elif isinstance(value, dict):
        for v in value.values():
            yield from files_of(v)
    elif isinstance(value, list):
        for v in value:
            yield from files_of(v)


def pack(argv):
    run, state_out, tar = argv[:3]
    rest = argv[3:]
    odb = None
    if rest[:1] == ['--odb']:
        odb, rest = rest[1], rest[2:]
    state = latest_state(run)
    if odb:
        state['odb'] = str(Path(odb).resolve())
    Path(state_out).write_text(json.dumps(state, indent=2) + '\n')
    root = Path(os.environ.get('GITHUB_WORKSPACE', os.getcwd())).resolve()
    paths = [Path(state_out).resolve()]
    paths += [p.resolve() for k, v in state.items() if k != 'metrics' for p in files_of(v)]
    paths += [Path(p).resolve() for p in rest]
    paths = list(dict.fromkeys(paths))
    for p in paths:
        if not p.is_relative_to(root):
            raise SystemExit(f'outside the workspace: {p}')
    with tarfile.open(tar, 'w:gz') as archive:
        for p in paths:
            archive.add(p, arcname=str(p).lstrip('/'))
    for p in paths:
        print('packed', p)
    print('odb', state['odb'])


if __name__ == '__main__':
    {'pack': pack}[sys.argv[1]](sys.argv[2:])
