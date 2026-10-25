"""Independent source/byte/read-only review; no producer or HDL imports."""
from pathlib import Path
import ast,hashlib,json,re,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb')as s:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(s,'sha256').hexdigest())
def read(p):return json.loads(Path(p).read_text())
def literals(p):
 out={}
 for n in ast.parse(Path(p).read_text()).body:
  if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
   try:out[n.targets[0].id]=ast.literal_eval(n.value)
   except(ValueError,TypeError):pass
 return out
def patch(old,diff):
 lines=old.splitlines(keepends=True);d=diff.splitlines(keepends=True);out=[];at=0;i=2
 while i<len(d):
  m=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',d[i]);assert m,d[i]
  start=int(m[1])-1;assert start>=at;out+=lines[at:start];at=start;i+=1
  while i<len(d)and not d[i].startswith('@@ '):
   line=d[i];tag=line[0];body=line[1:]
   assert tag in ' +-'
   if tag in ' -':assert lines[at]==body;(at:=at+1)
   if tag in ' +':out.append(body)
   i+=1
 out+=lines[at:];return ''.join(out)
fpath=B/'source-freeze02.json';f=read(fpath)
for p,h in f['sources'].items():assert pin(R/p)==h,p
for p,h in f['product_sources'].items():assert pin(R/p)==h,p
assert len(f['product_sources'])==10 and f['functional_predicates']==42 and f['excluded_MAX4118_predicates']==2
assert f['product_sources']==read(B/'source-freeze01.json')['product_sources']
G=R/'scripts/generate_pcie_integrity_prefix_v24.py';V=R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v24.v';O=V.with_name(V.name.replace('v24','v23'));gv=literals(G);assert len(gv['EDITS'])==7 and pin(O)['sha256']==gv['SOURCE_SHA']
s=O.read_text()
for old,new in gv['EDITS']:assert s.count(old)==1;s=s.replace(old,new)
assert s.replace('integrity_v23','integrity_v24')==V.read_text();s=V.read_text().replace('integrity_v24','integrity_v23')
for old,new in reversed(gv['EDITS']):assert s.count(new)==1;s=s.replace(new,old)
assert s==O.read_text()
fragment=(B/'prefix_candidate01.vh').read_text()
def function(text,n):return re.search(r'function automatic \[[^\]]+\] '+n+r';.*?endfunction',text,re.S).group()
for n in ('token_prefix_context','context_prefix_modes'):assert function(V.read_text(),n)==function(fragment,n)
bridges=read(B/'source-bridges01.json')
for name,rec in bridges['support'].items():
 assert pin(rec['parent'])==rec['parent_pin'] and pin(B/name)==rec['candidate_pin']
 assert patch(Path(rec['parent']).read_text(),rec['full_diff'])==(B/name).read_text()
for name,diff in bridges['source_differences'].items():
 assert patch((R/name.replace('v24','v23')).read_text(),diff)==(R/name).read_text()
for name in ('hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v24.v','hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v24','scripts/check_pcie_gen3_continuous_rx_integrity_v24.py','hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v24.py','sw/tests/test_pcie_gen3_continuous_rx_integrity_v24.py'):
 assert (R/name).read_text().replace('v24','v23').replace('V24','V23')==(R/name.replace('v24','v23')).read_text(),name
miter=R/'sw/tests/test_pcie_gen3_integrity_v24_miter.py';mv=literals(miter);assert mv['CONTEXT_OBSERVER']==(B/'context_observer01.vh').read_text()
assert mv['HEADER_OBSERVER'].replace('v24','v23').replace('V24','V23')==literals(miter.with_name(miter.name.replace('v24','v23')))['HEADER_OBSERVER']
assert mv['OLD_FRAMER']=='soc_pcie_gen3_framer_rx_integrity_v23' and mv['NEW_FRAMER']=='soc_pcie_gen3_framer_rx_integrity_v24'
assert len(mv['HEADER_FAULTS'])==6
burst=R/'sw/tests/test_pcie_gen3_integrity_v24_block_burst.py';bv=literals(burst);assert len(bv['CONTEXT_FAULTS'])==4
for name,(before,after)in bv['CONTEXT_FAULTS'].items():assert V.read_text().count(before)==1 and before!=after,name
component=read(B/'component-status01.json');assert component['returncode']==0 and component['status']=='COMPLETE_PENDING_INDEPENDENT_CONTROL_RECOUNT'
cases=list(ET.parse(B/'component-controls01.xml').getroot().iter('testcase'));assert len(cases)==5 and all(c.find('failure')is None and c.find('error')is None and c.find('skipped')is None for c in cases)
assert len(re.findall(r'^async def .*', (R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v24.py').read_text(),re.M))>=18
# Actual selected test census: direct(2+12-1MAX), miter(2+12+inverse+observer-1MAX), burst(1+4), prefix(5+1+3).
assert (2+12-1)+(2+12+1+1-1)+(1+4)+(5+1+3)==42
for p in ['hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v23.v','hw/soc/rtl/pcie/soc_pcie_gen3_ingress.v','hw/soc/rtl/pcie/soc_pcie_gen3_ingress_integrity_v11.v','hw/soc/rtl/pcie/soc_pcie_gen3_data_descrambler.v','scripts/check_pcie_integrity.py','scripts/check_pcie_integrity_native.py','scripts/cocotb_results.py','scripts/generate_pcie_integrity_ingress_v11.py','hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v23','scripts/check_pcie_gen3_continuous_rx_integrity_v23.py','hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py','.venv/bin/python','.venv/pyvenv.cfg']:
 assert str(R/p)in f['sources'],p
supplement=read(B/'source-bridges02.json')
assert supplement['previous_freeze']==pin(B/'source-freeze01.json') and supplement['freeze']==pin(fpath)
for name,rec in supplement['support'].items():
 old=B/name.replace('02.py','01.py');new=B/name
 assert pin(old)==rec['parent_pin'] and pin(new)==rec['candidate_pin']
 assert patch(old.read_text(),rec['whole_diff'])==new.read_text()
assert not(B/'status01.json').exists() and not Path('/dev/shm/nssoc-integrity-v24-full-controls01').exists()

out=dict(status='PASS_SOURCE_ONLY_V24_PREFIX_CONTEXT_IMPLEMENTATION',freeze=pin(fpath),launcher=pin(B/'launch_controls02.py'),detacher=pin(B/'detach_controls02.py'),findings=[],reviewer='vco_loaded_feedback',method=pin(__file__),source_pins=f['product_sources'],total_frozen_sources=len(f['sources']),initial_finding=pin(B/'source-findings-vco01.json'),preliminary=pin(B/'product-preliminary-source-vco01.json'),checks=['Complete seven-edit product inverse reconstructed independently from literal AST, no generator execution; both context functions equal actually controlled component source. All ten current product pins unchanged by additive freeze.','Read whole matrix/packing test and reference-bank/consumed-mode observer. Independent original V23 helper functions are used; exhaustive finite13-token/4-carry/9-initial matrix relation covers three prefixes, with four meaningful arithmetic mutations. Product block packing adds16 positions/512binary/160XZ cases and premature EDS/wrong-offset faults.','Context bank ownership follows exact original V23 valid-data lifecycle and assignment priority. Independent observer derives expected context from reference predecode, never candidate context function; old valid current/next banks and actually consumed modes are checked. Four bank mutations target capture/current-next/shift/promotion separately, require named context-bank failure.','Full18case direct/miter public schedule unchanged. Original12 product and12 miter faults, header ownership observer, occupied ring/descriptor checks retained. Real ready-valid block burst requires changed promotions and concurrent accept plus actual input/output stalls and final EDS, scalar bytes/metadata scoreboard; no forced internal state.','Reconstructed all eight complete source differences and both complete initial launcher support bridges; reviewed additive dependency-only freeze and launcher selection. Selected wrapper executable hashes, lexical Python anchors,1GiB entry/528MiB continuous+terminal resource checks, exact ProcessOwner post-complete/post-context signal guards and CPU6/2GiB preserved. No healthy timeout.','Observed saved standalone component5/5 XML only; full product42 selected predicates still unexecuted,2MAX4118 explicitly excluded. Full product acceptance requires actual meaningful controls; native mapping/timing remain separate.'],execution='No reviewed producer, simulator, test or mapped native execution by reviewer.')
p=B/'source-only-peer-vco02.json';assert not p.exists();p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(peer=str(p),pin=pin(p))))
