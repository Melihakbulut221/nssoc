"""Add one exact named-mutant diagnostic; product remains byte-identical."""
from pathlib import Path
import ast,hashlib,json,difflib
R=Path.cwd();B=Path(__file__).resolve().parent
def pin(p):
 p=Path(p)
 with p.open('rb') as s:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(s,'sha256').hexdigest())
validation=B/'controls01-final-validation.json';v=json.loads(validation.read_text())
assert v['status']=='RETAINED_V24_41_PASS_1_HOST_DIAGNOSTIC_FAILURE'
assert pin(v['archive']['path'])=={k:v['archive'][k] for k in('bytes','sha256')}
p=R/'sw/tests/test_pcie_gen3_integrity_v24_miter.py';old=p.read_text()
fragment='''        )
    )
    assert (out / "sim/sim.vvp").is_file()
'''
replacement='''        )
    ) or (
        # This named mutation now first trips the independent consumed-mode
        # observer. Accept only its precise native fatal, never any error.
        fault == "header_carried_always_bad"
        and result.returncode != 0
        and re.search(
            r"FATAL: [^\\n]+:\\d+: V24_CONTEXT_CONSUMED_MODE word=1\\n"
            r"\\s+Time: \\d+  Scope: soc_pcie_gen3_continuous_rx_integrity_v24\\n",
            log,
        ) is not None
    )
    assert (out / "sim/sim.vvp").is_file()
'''
assert old.count(fragment)==1
new=old.replace(fragment,replacement);assert new.replace(replacement,fragment)==old
snapshot=B/'source-before-diagnostic03';snapshot.mkdir()
freeze=B/'source-freeze02.json';f=json.loads(freeze.read_text())
for n,h in f['sources'].items():assert pin(R/n)==h,n
for n,h in f['product_sources'].items():
 q=snapshot/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((R/n).read_bytes());assert pin(q)==h
p.write_text(new);ast.parse(new)
f['product_sources'][str(p.relative_to(R))]=pin(p)
f['sources'][str(p.relative_to(R))]=pin(p)
if str(p) in f['sources']:f['sources'][str(p)]=pin(p)
f['previous_freeze']=dict(path=str(freeze),**pin(freeze))
f['status']='FROZEN_V24_NAMED_MUTANT_DIAGNOSTIC_CORRECTION_REQUIRES_ADDITIVE_PEER'
f['scope']='All product RTL and all stimuli unchanged. One exact native fatal accepted only for header_carried_always_bad. Historical41PASS1FAIL retained; targeted two predicates required. No native mapping before merged evidence peer.'
fresh=B/'source-freeze03.json';fresh.write_text(json.dumps(f,indent=2)+'\n')
s=(B/'launch_controls02.py').read_text()
for a,b in [('source-freeze02.json','source-freeze03.json'),(pin(freeze)['sha256'],pin(fresh)['sha256']),('source-only-peer-vco02.json','source-only-peer-vco03.json'),('nssoc-integrity-v24-full-controls01','nssoc-integrity-v24-diagnostic-controls03'),("'status01.json'","'status03.json'"),("'controls01.xml'","'controls03.xml'"),("'owner01.json'","'owner03.json'"),("'controls01.log'","'controls03.log'")]:s=s.replace(a,b)
line=next(x for x in s.splitlines() if x.startswith('command='))
s=s.replace(line,"command=[sys.executable,'-m','pytest','-q','-p','no:cacheprovider',str(R/'sw/tests/test_pcie_gen3_integrity_v24_miter.py')+'::test_actual_miter_fault_is_observed[header_carried_always_bad]',str(R/'sw/tests/test_pcie_gen3_integrity_v24_prefix.py')+'::test_exact_generated_inverse_and_wrapper_bridge','--basetemp='+str(D),'--junitxml='+str(B/'controls03.xml')]")
s=s.replace('V24 full42 selected controls with unchanged18 public profiles and originalV23 cycle schedule;2MAX4118 tests explicitly excluded.','V24 targeted named-mutant native diagnostic and exact source inverse;41PASS1FAIL full history preserved.')
launch=B/'launch_controls03.py';launch.write_text(s);ast.parse(s)
d=(B/'detach_controls02.py').read_text()
for a,b in [('launch_controls02.py','launch_controls03.py'),(repr(pin(B/'launch_controls02.py')),repr(pin(launch))),('source-freeze02.json','source-freeze03.json'),(repr(pin(freeze)),repr(pin(fresh))),('source-only-peer-vco02.json','source-only-peer-vco03.json'),('nssoc-integrity-v24-full-controls01','nssoc-integrity-v24-diagnostic-controls03'),("'status01.json'","'status03.json'"),("'detached-once01.json'","'detached-once03.json'"),("'launch01.log'","'launch03.log'"),("'detached-receipt01.json'","'detached-receipt03.json'")]:d=d.replace(a,b)
detach=B/'detach_controls03.py';detach.write_text(d);ast.parse(d)
rows=[]
for oldp,newp in [(snapshot/str(p.relative_to(R)),p),(B/'launch_controls02.py',launch),(B/'detach_controls02.py',detach)]:
 rows.append(dict(parent=dict(path=str(oldp),**pin(oldp)),candidate=dict(path=str(newp),**pin(newp)),whole_diff=''.join(difflib.unified_diff(oldp.read_text().splitlines(True),newp.read_text().splitlines(True)))))
rec=dict(status='ADDITIVE_NAMED_DIAGNOSTIC_ONLY_NO_PRODUCT_OR_STIMULUS_CHANGE',freeze=dict(path=str(fresh),**pin(fresh)),history_validation=dict(path=str(validation),**pin(validation)),source_snapshot=str(snapshot),support={str(x):pin(x) for x in(launch,detach)},whole_bridges=rows,actual_mutant_log=pin('/dev/shm/nssoc-integrity-v24-full-controls01/test_actual_miter_fault_is_obs11/capture/simulation.log'),targeted_count=2)
(B/'diagnostic-correction03.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({k:rec[k] for k in('status','freeze','support')}))
