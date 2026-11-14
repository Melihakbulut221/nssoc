# SPDX-License-Identifier: Apache-2.0
"""Independent full archived SRAM CC MOS comparison; no substrate aliases."""
import collections,hashlib,json,pathlib,sys,zipfile
sys.path.insert(0,'hw/soc/flow')
from audit_sram_flat_rc import parse,audit
from sram_independent_mos_projection import graph_from_flat,canonical_reference
from mos_graph_equivalence import load_mos_netlist,prove_mos_graph
out=pathlib.Path('out');out.mkdir(exist_ok=True)
r={'status':'FAIL_OR_INCONCLUSIVE','source_extraction_run':43534692191,'source_extraction_commit':'2b9714c3c9c9ffb6e47313c7b96d09f74435dd98','full_chip_lvs':False,'rc_qualified':False,'manufacturing_approval':False,'scope':'Archived alternative DP256x16 macro independent CC MOS topology plus exact RC terminal connectivity and pair-capacitance conservation. No body aliases. Not current-chip SRAM; resistance/capacitance calibration, corners, Liberty and manufacturing acceptance remain open.'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def open_archive(path,expected):
 with open(path,'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected
 return zipfile.ZipFile(path)
def member(z,suffix):
 names=[n for n in z.namelist() if ('/'+n).endswith('/'+suffix)];assert len(names)==1,(suffix,len(names))
 data=z.read(names[0]);return data,names[0]
try:
 z=open_archive('cc.zip','d266fe1a64e0c09716552f44a8ebb27c13e39a461c208d7153386b59429f7d90')
 gds,_=member(z,'DP8TSRAMDP256x16.gds');assert sha(gds)=='c6a1be71d0439e88e2c08729345eb8d8001f773266cb7a8b939446e54999ff45'
 net,name=member(z,'DP8TSRAMDP256x16_k25d_pex_netlist.spice')
 r.update(gds_sha256=sha(gds),cc_netlist_sha256=sha(net),cc_member=name)
 a=open_archive('reference.zip','124f6a92fa56346b1c471efb84750878180ef0c8056b2c940c5c6fce0e41e29b');ref,_=member(a,'reference.spice');assert sha(ref)=='64d041383d0ebee7b54dab0bc10d651d31262a2a41ccd15a9c0727dac06e0dd9'
 pathlib.Path('reference.spice').write_bytes(ref)
 # Confirm a single independent top before flattening.
 import klayout.db as db
 n=db.Netlist();n.read('reference.spice',db.NetlistSpiceReader());tops=list(n.top_circuits());assert len(tops)==1 and tops[0].name.lower()=='dp8tsramdp256x16'
 reference=canonical_reference(load_mos_netlist(pathlib.Path('reference.spice')));assert len(reference['devices'])==37076
 flat=parse(net.decode());r['extracted_inventory']={'mos':len(flat['mos']),'R':len(flat['R']),'C':len(flat['C']),'ports':flat['ports'],'models':dict(collections.Counter(d['model'] for d in flat['mos'].values()))}
 rc_archive=open_archive('rc.zip','d937d7733a8fb8ffebed9ee61b6923c5d66c75284ed33e549a3493e8eb2e3404')
 rc_gds,_=member(rc_archive,'DP8TSRAMDP256x16.gds');assert sha(rc_gds)==sha(gds)
 rc_net,rc_name=member(rc_archive,'DP8TSRAMDP256x16_k25d_pex_netlist.spice')
 rc_flat=parse(rc_net.decode());r.update(rc_netlist_sha256=sha(rc_net),rc_member=rc_name)
 r['rc_inventory']={'mos':len(rc_flat['mos']),'R':len(rc_flat['R']),'C':len(rc_flat['C']),'ports':rc_flat['ports']}
 r['rc_pair_conservation'],conserved=audit(flat,rc_flat,37076)
 r['rc_terminal_and_pair_conservation_passed']=conserved
 assert conserved,'RC pair capacitance conservation failed'
 extracted=graph_from_flat(flat,37076)
 r['inventories']={}
 for label,g in [('reference',reference),('extracted',extracted)]:
  r['inventories'][label]={'mos':len(g['devices']),'nets':len(g['nets']),'ports':sorted(g['pins'].values()),'bulks':dict(collections.Counter(g['pins'].get(d['B'],'INTERNAL') for d in g['devices']))}
 proof=prove_mos_graph(reference,extracted);proof.pop('mapping');r.update(status='PASS_ARCHIVED_FULL_MACRO_RC_CONSERVATION_AND_MOS_TOPOLOGY',proof=proof)
except Exception as e:r['error']=type(e).__name__+': '+str(e)
(out/'independent-macro-rc.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(0 if r['status'].startswith('PASS_') else 1)
