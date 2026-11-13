# SPDX-License-Identifier: Apache-2.0
"""Independent flat MOS/RC connectivity and collapsed pair-capacitance check.
No calibrated extraction, spatial C placement, body RC or Liberty approval.
"""
import collections,copy,hashlib,io,json,math,pathlib,re,zipfile
OUT=pathlib.Path('out');OUT.mkdir(exist_ok=True)
from audit_sram_flat_rc import Rejected, require, parse
from audit_sram_flat_rc import audit as audit_counted
def audit(cc,rc):
 return audit_counted(cc,rc,expected_mos=8)
def main():
 raw=pathlib.Path('native.zip').read_bytes();require(hashlib.sha256(raw).hexdigest()=='35be261afbc97cb1b555e2678090caf4624424a47127aba3695e5411e8093b33','artifact hash mismatch')
 z=zipfile.ZipFile(io.BytesIO(raw));models={};sha={}
 for mode,expected in [('CC','cbc7dca6e387a67db742336a5f232184ea30e044c18c33c0c5fd77b516c0d57d'),('RC','77b35e72ed46865efaaf440cecfad07c78e4468fc1dad193cc94f19651c94dde')]:
  matches=[n for n in z.namelist() if n.startswith(mode+'/') and n.endswith('_k25d_pex_netlist.spice')];require(len(matches)==1,'netlist selection ambiguous')
  b=z.read(matches[0]);sha[mode]=hashlib.sha256(b).hexdigest();require(sha[mode]==expected,'netlist hash mismatch');models[mode]=parse(b.decode())
 cc,rc=models['CC'],models['RC'];result,passed=audit(cc,rc)
 controls={}
 # Remove the largest capacitor: a physical coupling loss must be rejected.
 key=max(rc['C'],key=lambda k:rc['C'][k][2]);bad=copy.deepcopy(rc);del bad['C'][key]
 try:_,accepted=audit(cc,bad)
 except Rejected:accepted=False
 controls['removed_capacitor']={'instance':key,'rejected':not accepted}
 # Seek a bridge resistance whose removal disconnects a real terminal/port net.
 for key in rc['R']:
  bad=copy.deepcopy(rc);del bad['R'][key]
  try:audit(cc,bad)
  except Rejected as e:
   if 'split' in str(e):controls['disconnected_resistor']={'instance':key,'rejected':True,'reason':str(e)};break
 controls.setdefault('disconnected_resistor',{'rejected':False,'reason':'no terminal-disconnecting bridge found'})
 bad=copy.deepcopy(rc);first=next(iter(bad['mos']));bad['mos'][first]['model']='deliberately_wrong_model'
 try:audit(cc,bad);rejected=False
 except Rejected:rejected=True
 controls['changed_mos_model']={'rejected':rejected}
 result.update(status='PASS_SCOPED_COLLAPSED_RC_CHECKS' if passed and all(x['rejected'] for x in controls.values()) else 'FAIL_SCOPED_RC_CHECKS',source_artifact=14067369661,netlist_sha256=sha,controls=controls,qualified_pex=False,manufacturing_approval=False,scope='Eight-device leaf only; same-engine CC versus resistor-collapsed RC with exact MOS identities/parameters and terminal anchors. No independent schematic LVS, spatial C proof, calibrated physical model, full well/body RC or full-macro qualification.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));return result['status'].startswith('PASS_')
try:ok=main()
except Exception as e:
 (OUT/'result.json').write_text(json.dumps(dict(status='ERROR',error=type(e).__name__+': '+str(e),qualified_pex=False,manufacturing_approval=False),indent=2));raise
raise SystemExit(0 if ok else 1)
