#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pin the unchanged native MIM semantics and explicit new parent provenance."""
import ast,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'scripts/cloud_cdr_follower_v23_mim_parent_rc.py': '1db1e40c227f902cdeabe1481a1bb7c9b8a407ecf479943dcfc237738cdf8771', 'scripts/cloud_cdr_follower_v23_mim_capture_stage.py': '855f1bd5b4a4e9e93b432b26a6b85fb57eaac109c7cde3375118fe9d49e6782a', 'docs/evidence/cdr-follower-v23-mim-capture-input-20261020.json': 'f8106b3494f763c784bb16ebbd509c0bff7ac3156707b5ad48716b446fa707cf', '.github/workflows/cdr-follower-v23-mim-parent-rc-cloud.yml': '43bd78e5227eabae873259b90ce0d313538df5f4072872415bc98f7ce3822e96', 'scripts/cdr-follower-v23-mim-capture-methods.json': 'ba845270dc00cb5de4484807eb60221eb3b72a1297eccae3546ce4019a1faf5c'}
def check():
    for name,digest in PINS.items():
        data=(ROOT/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==digest,name
        if name.endswith('.py'):ast.parse(data,filename=name)
    print('PASS_FROZEN_PD476_MIM_CAPTURE_INPUTS_NOT_RAW_RC_OR_ELECTRICAL_ACCEPTANCE')
if __name__=='__main__':check()
