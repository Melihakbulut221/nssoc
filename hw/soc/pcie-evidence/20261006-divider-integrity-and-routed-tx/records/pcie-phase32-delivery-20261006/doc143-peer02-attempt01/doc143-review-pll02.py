# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Additive saved clean regression and document review; no native rerun."""
from pathlib import Path
import datetime,hashlib,json,tarfile,xml.etree.ElementTree as ET
R=Path.cwd();B=Path(__file__).resolve().parent;D=B/'v23-final-controls01'
def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
def load(p):return json.loads(Path(p).read_text())
def check(p,h):assert pin(p)=={k:h[k]for k in('bytes','sha256')},str(p)
prior=load(B/'doc143-review-pll01.json');doc=R/'docs/143-pcie-divider-and-routed-transmitter.md';s=doc.read_text()
image='![Actual Bias8 VCO, clock-base and latch-collector waveforms showing late amplitude collapse](img/pcie-bias8-latch-loss-20261006.png)\n\n'
para='''A subsequent clean execution of the final source files passes all **36
non-MAX4118 tests**, including the real block-burst test, with zero failures
and two MAX4118 predicates deselected. It finishes in 450.62 seconds. Its
full native test artifacts are retained separately; the earlier 47 execution
records remain unchanged. This closes the current non-MAX4118 regression
without changing the negative native setup result below.

'''
assert s.count(image)==s.count(para)==1
old=s.replace(image,'').replace(para,'').encode();assert dict(bytes=len(old),sha256=hashlib.sha256(old).hexdigest())==prior['document']
plot=R/'docs/img/pcie-bias8-latch-loss-20261006.png';assert pin(plot)==pin(R/'hw/soc/out/pcie-bias8-wave-root-20261006/bias8-latch-loss-over-time.png')
f=B/'pcie-integrity-v23-current-full-controls04-validation-20261006.json';v=load(f);a=Path(v['archive']['path']);check(a,v['archive']);members=v['members'];assert len(members)==316
seen=set()
with tarfile.open(a,'r:xz')as tar:
 for m in tar:
  assert m.isfile()and not m.issparse()and m.name not in seen and m.name in members;seen.add(m.name)
  with tar.extractfile(m)as stream:got=dict(bytes=m.size,sha256=hashlib.file_digest(stream,'sha256').hexdigest())
  assert got=={k:members[m.name][k]for k in got}
assert seen==set(members)
for h in members.values():check(h['restore_path'],h)
r=load(D/'result.json');check(D/'result.json',v['result']);assert r['status']=='PASS_CURRENT_V23_FULL_NON4118_REGRESSION'and r['returncode']==0 and r['passed']==36 and r['stop_reason']is None
ready=load(R/'hw/soc/out/pcie-integrity-v23-20261006/ready-finite.json');assert r['source_pins']==v['sources']==ready['source_allowlist']
for n,h in r['source_pins'].items():check(R/n,h)
for n,h in r['outputs'].items():check(n,h)
cases=list(ET.parse(D/'tests.xml').getroot().iter('testcase'));assert len(cases)==36 and all(not any(c.find(x)is not None for x in('failure','error','skipped'))for c in cases)
assert [c.attrib['name']for c in cases]==[x['name']for x in r['cases']]
assert '36 passed, 2 deselected in 450.62s' in (D/'tests.log').read_text()
for who in ['owner','child']:
 p=Path('/proc')/str(r[who]['pid'])/'stat';assert not p.exists()or p.read_text().rsplit(') ',1)[1].split()[19]!=r[who]['start_ticks']
helpers=[]
for name,h in members.items():
 if not name.startswith('tests/')or not name.endswith('/result.json'):continue
 p=Path(h['restore_path']);j=load(p)
 for n,q in j['inputs'].items():check(n,q)
 for n,q in j['outputs'].items():check(Path(n)if Path(n).is_absolute()else p.parent/n,q)
 if 'tests'in j:
  xml=list(ET.parse(p.parent/'results.xml').getroot().iter('testcase'));counts=dict(passed=sum(not any(c.find(t)is not None for t in('failure','error','skipped'))for c in xml),failed=sum(any(c.find(t)is not None for t in('failure','error'))for c in xml),skipped=sum(c.find('skipped')is not None for c in xml));assert counts==j['tests']and len(xml)==18
  if j['exact_test_selection']is None:assert j['status']=='PASS_PORT_ONLY_PCIE_GEN3_WIDE_CRC_QUARANTINE_RX'and counts==dict(passed=18,failed=0,skipped=0)
  else:assert j['status']=='FAIL'and counts==dict(passed=0,failed=1,skipped=17)
  helpers.append(dict(path=str(p),**pin(p),counts=counts))
 else:
  log=(p.parent/'simulation.log').read_text()
  if j['fault']is None:assert j['returncode']==0 and 'PASS_V23_FRAMER_BURST blocks=15 bytes=786 packets=25 promotions=14 changed=13 concurrent=13 inputstall=38 outputstall=6'in log
  else:assert j['fault']=='header_promote_stale'and j['returncode']!=0 and 'V23_FRAMER_PROMOTION_RELATION'in log and 'Time: 28000'in log
  helpers.append(dict(path=str(p),**pin(p),fault=j['fault'],returncode=j['returncode']))
assert len(helpers)==28
release=load(B/'v23-final-release01.json');assert release['status']=='PASS_IMMUTABLE_RELEASE_ROUNDTRIPS'and release['tag']=='evidence-20261006-pcie-closure'and len(release['assets'])==2
for asset in release['assets']:
 assert asset['authenticated_roundtrip']and asset['anonymous_roundtrip'];local=a if asset['name']==a.name else f;check(local,asset)
q=dict(status='PASS_INDEPENDENT_DOC143_ADDITIVE_AND_CURRENT_V23_36_CONTROLS_SAVED_REVIEW',utc=datetime.datetime.now(datetime.UTC).isoformat(),document=pin(doc),prior_document_peer=pin(B/'doc143-review-pll01.json'),plot=pin(plot),method=pin(Path(__file__)),validation=pin(f),archive=dict(path=str(a),members=316,**pin(a)),result=pin(D/'result.json'),pytest=pin(D/'tests.xml'),release=pin(B/'v23-final-release01.json'),helpers=helpers,findings=[],scope='Full316archive/originalpath readback; actual36pytest cases and28 saved helper receipts/rawXMLs recounted, exact final10source bytes match originalfinite ready. Complete prior document recovered by removing only added plot+clean regression paragraph. Earlier47executions/10failures remain unchanged; MAX4118 V23 and native timing/PHY acceptance remain excluded. No HDL, EDA, waveform replay or tests rerun.')
p=B/'doc143-review-pll02.json';assert not p.exists();p.write_text(json.dumps(q,indent=2)+'\n');print(q['status'],pin(p))
