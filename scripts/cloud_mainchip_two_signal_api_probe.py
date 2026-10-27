#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Closed four-command read-only derivation of the qualified failure-preserving driver."""
import ast,hashlib,json,types
from pathlib import Path
import mainchip_two_signal_api_probe as contract
ROOT=contract.ROOT
FROZEN='scripts/cloud_mainchip_two_signal_repair.py'
FROZEN_SHA='e5b2d952dd859e5fc297a4240565488dc748b29b7ccbf1d62adc587ffac1a45e'
GROUP='mainchip-two-signal-api-probe'
EDITS=[
  [
    "SHORT_PHASES=frozenset(('bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version',\n    'ownership','prepare-fixed','paired-all-nontarget-fixed-import','fixed-audit','route-audit',\n    'paired-original-class-return','unfix-audit','full-original-class-read-only-DRT','drc-audit'))\n",
    "SHORT_PHASES=frozenset(('bootstrap-exact-runtime','restore-complete-saved-inputs','actual-runtime-version','api-identity-census'))\n",
    1
  ],
  [
    "    if label=='one-two-signal-routing-attempt':return 14400\n",
    "",
    1
  ],
  [
    "('cloud_restore_authorized','native_execution_authorized','native_routing_authorized')",
    "('cloud_restore_authorized','native_execution_authorized','native_api_probe_authorized')",
    1
  ],
  [
    "str(ROOT/'scripts/mainchip_two_signal_repair_native.py')",
    "str(ROOT/'scripts/mainchip_two_signal_api_probe_native.py')",
    1
  ],
  [
    "            phase('ownership')\n            ownership=json.loads(c.regular(OUT/'work/ownership.json').read_bytes())\n            result['ownership']=ownership;save(OUT/'result.json',result)\n            s.require_actionable(ownership) # No mutation or router launch before actual native evidence.\n            phase('prepare-fixed')\n            command([str(app),'openroad','-exit',str(OUT/'work/fixed.tcl')],'paired-all-nontarget-fixed-import')\n            phase('fixed-audit')\n            result['native_routing_started']=True;save(OUT/'result.json',result)\n            command([str(app),'openroad','-exit',str(OUT/'work/repair.tcl')],'one-two-signal-routing-attempt')\n            result['route_log']=qualified.s.route_log(c.regular(sup.TRACE/'one-two-signal-routing-attempt.stdout').read_bytes())\n            phase('route-audit')\n            command([str(app),'openroad','-exit',str(OUT/'work/unfix.tcl')],'paired-original-class-return')\n            phase('unfix-audit')\n            command([str(app),'openroad','-exit',str(OUT/'work/final-drc.tcl')],'full-original-class-read-only-DRT')\n            phase('drc-audit')\n        result['native_result']=json.loads(c.regular(OUT/'work/drc-audit-result.json').read_bytes())\n        result['next_stage']=s.require_complete(result['native_result'])\n",
    "            phase('api-identity-census')\n        result['api_probe']=json.loads(c.regular(OUT/'work/api-identity-census.json').read_bytes())\n        result['diagnostic_disposition']=validate_report(result['api_probe'])\n",
    1
  ],
  [
    "RUNNING_OWNERSHIP_BEFORE_CONDITIONAL_TWO_SIGNAL_REPAIR",
    "RUNNING_READ_ONLY_API_IDENTITY_CENSUS",
    1
  ],
  [
    "COMPLETE_CONDITIONAL_TWO_SIGNAL_ATTEMPT_NOT_RC_STA_OR_PHY_ACCEPTANCE",
    "COMPLETE_READ_ONLY_API_IDENTITY_CENSUS_NOT_REPAIR",
    1
  ],
  [
    "FAIL_OR_BLOCKED_TWO_SIGNAL_ATTEMPT",
    "FAIL_OR_BLOCKED_READ_ONLY_API_CENSUS",
    2
  ],
  [
    "        if terminal_errors:\n",
    "        terminal_check('preserve-api-diagnostic',lambda:capture_probe(result,OUT))\n        if terminal_errors:\n",
    1
  ]
]

def derive():
    raw=(ROOT/FROZEN).read_bytes();assert hashlib.sha256(raw).hexdigest()==FROZEN_SHA
    original=raw.decode();text=original
    for old,new,count in EDITS:
        assert text.count(old)==count and count>0
        text=text.replace(old,new)
    reverse=text
    for old,new,count in reversed(EDITS):
        if new:
            assert reverse.count(new)==count
            reverse=reverse.replace(new,old)
        else:
            # This one removal is restored at its original closed-label selector.
            assert old=="    if label=='one-two-signal-routing-attempt':return 14400\n"
            needle="    assert label in SHORT_PHASES,('Unknown command label',label)\n"
            assert reverse.count(needle)==1
            reverse=reverse.replace(needle,old+needle)
    assert reverse==original,'Driver derivation is not exactly reversible'
    tree=ast.parse(text)
    result=dict(frozen_path=FROZEN,frozen_sha256=FROZEN_SHA,
        derived_sha256=hashlib.sha256(text.encode()).hexdigest(),literal_edits=len(EDITS))
    assert result==contract.methods()['driver_derivation']
    return text,result

def capture_probe(result,out):
    path=out/'work/api-identity-census.json'
    if not path.exists():
        result['api_probe_saved_file']=dict(present=False,complete=False)
        return
    raw=contract.c.regular(path).read_bytes()
    evidence=dict(present=True,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    result['api_probe_saved_file']=evidence
    assert len(raw)<=268435456,'API diagnostic exceeds explicit 256 MiB JSON bound'
    try:parsed=json.loads(raw)
    except (UnicodeError,ValueError)as exc:
        evidence.update(complete=False,parse_error=repr(exc));raise
    assert type(parsed)is dict,'API diagnostic must be a JSON object'
    result['api_probe']=parsed
    evidence['complete']=parsed.get('status')=='COMPLETE_READ_ONLY_API_IDENTITY_CENSUS_NOT_OWNERSHIP_QUALIFICATION'

def namespace():
    text,proof=derive()
    ns=dict(__name__='qualified_readonly_api_driver',__file__=str(Path(__file__).resolve()))
    exec(compile(text,str(ROOT/FROZEN),'exec'),ns)
    cloned=types.SimpleNamespace(**dict(vars(ns['s']),methods=contract.methods))
    ns.update(s=cloned,OUT=ROOT/'cloud-mainchip-two-signal-api-probe',
        TRANSPORT=ROOT/'transport-mainchip-two-signal-api-probe',GROUP=GROUP,
        validate_report=contract.validate_report,capture_probe=capture_probe)
    assert ns['SHORT_PHASES']==frozenset(contract.LABELS)
    return ns,proof

def main():
    namespace()[0]['main']()
if __name__=='__main__':main()
