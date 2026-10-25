#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import hashlib,json,os,sys
from pathlib import Path
from librelane.common import get_script_dir
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'hw/soc/pnr'))
from replay_onehot_antenna_round2_flow import resume_script
assert os.environ.get('GITHUB_ACTIONS')=='true'
p=Path(get_script_dir())/'openroad/drt.tcl';source=p.read_text();changed=resume_script(source)
assert changed.count('drt_run $i {*}$drt_args')==1 and changed.count('write_views')==source.count('write_views')==1
assert 'set i 2'in changed and 'DRT_OPT_ITERS'in changed
faults=[]
for name,bad in [('missing_initial_route',source.replace('set i 0\n','')),('duplicate_iteration',source+'set i 0\n'),('missing_antenna_loop',source.replace('while {$i <=','while {0 && $i <='))]:
    try:resume_script(bad)
    except AssertionError:faults.append(name)
    else:raise AssertionError('Accepted '+name)
print(json.dumps(dict(status='PASS_ACTUAL_NATIVE_ROUND2_TRANSFORM_NOT_ROUTE_ACCEPTANCE',runtime_script_sha256=hashlib.sha256(source.encode()).hexdigest(),rejected=faults)))
