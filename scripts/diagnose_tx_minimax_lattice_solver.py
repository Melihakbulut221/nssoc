#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only original31macro optimization diagnostics; never physical acceptance."""
import json,os,traceback
from pathlib import Path
import numpy as np
import plan_tx_v5_minimax_rows as p
assert os.environ.get('GITHUB_ACTIONS')=='true'
native=p.milp
calls=[]
def observe(c,**kw):
    a=np.array(kw['constraints'].A,copy=True);b=np.array(kw['constraints'].ub,copy=True)
    modes=[]
    for presolve in (True,False):
        opts=dict(kw['options'],presolve=presolve)
        r=native(c,**dict(kw,options=opts))
        v=dict(presolve=presolve,status=int(r.status),message=r.message,success=bool(r.success))
        if r.x is not None:
            v.update(objective=float(c@r.x),max_linear_residual=float(np.max(a@r.x-b)),
                max_lower_bound_residual=float(np.max(kw['bounds'].lb-r.x)),
                max_upper_bound_residual=float(np.max(r.x-kw['bounds'].ub)),
                max_integrality_residual=float(np.max(np.abs(r.x[:31]-np.round(r.x[:31])))),
                mip_dual_bound=float(r.mip_dual_bound),mip_gap=float(r.mip_gap),x=list(map(float,r.x)))
        modes.append(v)
        if presolve:original=r
    calls.append(dict(objective=list(map(float,c)),bounds_lower=list(map(float,kw['bounds'].lb)),
        bounds_upper=[None if not np.isfinite(x)else float(x)for x in kw['bounds'].ub],modes=modes))
    print(json.dumps(calls[-1]),flush=True)
    return original
p.milp=observe
try:
    record=json.loads(Path('docs/evidence/tx-v5-final-strap6-physical-pass-20261019.json').read_text())['report']['layout']
    result=p.plan_candidate(record)
    print(json.dumps(dict(status='DIAGNOSTIC_PLAN_RETURNED_NOT_ACCEPTANCE',plan=result)))
except BaseException as error:
    print(json.dumps(dict(status='DIAGNOSTIC_ORIGINAL_FAILURE_REPRODUCED_NOT_ACCEPTANCE',error=repr(error))))
    traceback.print_exc()
finally:
    Path('solver-diagnosis.json').write_text(json.dumps(dict(calls=calls,accepted=False),indent=2)+'\n')
