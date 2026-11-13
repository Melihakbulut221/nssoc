# SPDX-License-Identifier: Apache-2.0
"""Cloud-only two-stage SRAM extraction audit; no body aliases or signoff claim.
Arguments: manifest.json. All archives must already exist on the cloud runner.
The manifest binds each archive digest and exact member digest independently.
"""
import hashlib,json,pathlib,sys,zipfile
sys.path.insert(0,'hw/soc/flow')
from audit_sram_flat_rc import parse,audit,require
from sram_independent_mos_projection import canonical_reference,graph_from_flat
from mos_graph_equivalence import load_mos_netlist,prove_mos_graph

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def member(spec):
 require(set(spec)=={'archive','archive_sha256','member','member_sha256'},'incomplete artifact binding')
 require(digest(spec['archive'])==spec['archive_sha256'],'archive digest differs')
 with zipfile.ZipFile(spec['archive']) as z:
  require(z.namelist().count(spec['member'])==1,'missing or duplicate member')
  raw=z.read(spec['member'])
 require(hashlib.sha256(raw).hexdigest()==spec['member_sha256'],'member digest differs')
 return raw

def run(config):
 r=dict(status='FAIL_OR_INCONCLUSIVE',qualified_pex=False,full_chip_lvs=False,manufacturing_approval=False,
        scope='Named archived macro only. CC/RC conservation and independent MOS topology, excluding junction parasitics, PVT/RC calibration, current routed-chip binding and foundry signoff.',stages={})
 try:
  require(set(config)=={'expected_mos','source_geometry_sha256','geometry','cc','rc','reference'},'incomplete manifest')
  require(type(config['expected_mos']) is int and config['expected_mos']>0,'invalid expected count')
  geometry=config['source_geometry_sha256'];require(len(geometry)==64 and all(c in '0123456789abcdef' for c in geometry),'invalid geometry identity')
  r['bindings']=config
  require(set(config['geometry'])=={'cc','rc'},'need geometry from both extraction archives')
  for mode in ['cc','rc']:
   g=config['geometry'][mode];net=config[mode]
   require(g['archive']==net['archive'] and g['archive_sha256']==net['archive_sha256'],'geometry and netlist archives differ')
   require(g['member_sha256']==geometry,'declared geometry differs')
   member(g)
  r['geometry_verified_in_both_archives']=True
  payload={key:member(config[key]) for key in ['cc','rc','reference']}
  # Compare reference to CC even if the RC audit fails, preserving both findings.
  cc,rc=parse(payload['cc'].decode()),parse(payload['rc'].decode())
  try:
   conservation,passed=audit(cc,rc,config['expected_mos'])
   r['stages']['cc_rc_conservation']={'passed':passed,'measurements':conservation}
  except Exception as e:r['stages']['cc_rc_conservation']={'passed':False,'error':type(e).__name__+': '+str(e)}
  try:
   p=pathlib.Path('native-reference-for-comparison.spice');p.write_bytes(payload['reference'])
   ref=canonical_reference(load_mos_netlist(p))
   require(len(ref['devices'])==config['expected_mos'],'independent reference count differs')
   extracted=graph_from_flat(cc,config['expected_mos'])
   r['independent_inventory']={'reference_mos':len(ref['devices']),'extracted_mos':len(extracted['devices']),'reference_nets':len(ref['nets']),'extracted_nets':len(extracted['nets']),'reference_ports':sorted(ref['pins'].values()),'extracted_ports':sorted(extracted['pins'].values())}
   proof=prove_mos_graph(ref,extracted);proof.pop('mapping')
   r['stages']['independent_mos_topology']={'passed':True,'proof':proof}
  except Exception as e:r['stages']['independent_mos_topology']={'passed':False,'error':type(e).__name__+': '+str(e)}
  if len(r['stages'])==2 and all(s['passed'] for s in r['stages'].values()):r['status']='PASS_ARCHIVED_MACRO_CONSERVATION_AND_MOS_TOPOLOGY'
 except Exception as e:r['error']=type(e).__name__+': '+str(e)
 return r
if __name__=='__main__':
 output=pathlib.Path('out');output.mkdir(exist_ok=True)
 result=run(json.loads(pathlib.Path(sys.argv[1]).read_text()))
 (output/'independent-extraction-audit.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result));raise SystemExit(0 if result['status'].startswith('PASS_') else 1)
