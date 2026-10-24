"""Independent bounded mapping-source review; no production imports/native."""
from pathlib import Path
import ast,hashlib,itertools,json
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb')as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
f=json.loads((B/'source-freeze01.json').read_text());c=json.loads((B/'controls-freeze01.json').read_text())
for pins in [f['inputs'],c['inputs']]:
 for p,v in pins.items():assert pin(p)==v,p
sources=[B/'run_mapping01.py',R/'scripts/check_npu_physical_eco_mapping.py',R/'sw/tests/test_npu_physical_eco_mapping.py']
for p in sources:ast.parse(p.read_text())
text=(B/'run_mapping01.py').read_text();assert "for name in ('original','candidate','factored')"in text
assert "q.mapping_recipe((bundle/'recipe/original-map.ys').read_text(),sources[name],out,bundle,snapshot,syn)"in text
assert "if name in ('original','candidate'):assert net['sha256']==frozen['expected_mapping'][name]"in text
assert "assert shutil.disk_usage(O).free>=1024**3;complete=True"in text
assert 'owned_popen('in text and 'stop_failed_group(p)'in text and 'healthy_elapsed_timeout=None'in text
assert f['expected_mapping']==dict(original='13dd615dabe769c4c2809dfb1e4b2e182f55c265256aea0f279e4d31c8005e48',candidate='ef20a6b368ad425af23ad72279e0d9bb31f2a06e92e42f405a20c6c3c71ac64f')
# Direct, independent algebra enumeration; not running the production checker.
for a,b,c0,d in itertools.product((0,1),repeat=4):assert not((a or b)and not(a and c0 and d))==((c0 and d)if a else not b)
# Exact pre-map gate-only bridge inspected from constant literals via AST.
t=ast.parse((R/'scripts/prepare_npu_reconvergence_eco.py').read_text());lits={n.targets[0].id:ast.literal_eval(n.value)for n in t.body if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Name)and isinstance(n.value,ast.Constant)}
a=Path(f['netlists']['candidate']).read_text();b=Path(f['netlists']['factored']).read_text();assert a.count(lits['OLD'])==a.count(lits['PREDECESSOR'])==1 and a.replace(lits['OLD'],lits['NEW'])==b
assert '17 passed'in(B/'controls01.log').read_text()
assert '8 passed'in(R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/repair05-source/lifecycle-controls02.log').read_text()
assert pin(R/'hw/soc/out/pcie-gen3-transmit-v4-repair-20261005/owned_lifecycle05.py')['sha256']=='39dedf775c53370fe7696fab46b198bf3d727c3dbf52dbd4148c3d70134ff526'
q=dict(status='PASS_SOURCE_ONLY_MATCHED_NPU_SRAM_ECO_MAPPING',source_freeze=pin(B/'source-freeze01.json'),controls_freeze=pin(B/'controls-freeze01.json'),findings=[],method=pin(Path(__file__)),method_pins={str(p):pin(p)for p in sources},input_pins_rehashed=len(f['inputs']),additional_control_pins_rehashed=len(c['inputs']),saved_graph_test_passes=17,saved_owned_lifecycle_test_passes=8,independent_binary_assignments=16,scope='Full runner/checker/test read with frozen mapping_recipe/mapping_contract/restore and onegate ECO source. Sequential original/candidate/factored same native recipe, required two exact old mapped hashes,32physicalSRAM identities and retained nonmemory pin equations, sharednamed-bit bijection and all unrelatedcells/ports preserved; exact INV/AND/MUX pin equations/newnetloads checked.16distinct graph mutations+renumberedpositive saved17PASS, no tests rerun. Owned WNOWAIT helper identical previously tested8controls; nativeCPU0/3GiB, SSD entry/continuous/terminalfloors and nohealthytimeout. Fresh output means no adoption/boot/route bypass; all native results remain pending. Additive controlfreeze is independently bound here; final launch must bind both freezes and this receipt. No producer/EDA/network run.')
(B/'source-only-peer-pll.json').write_text(json.dumps(q,indent=2)+'\n');print(q['status'],pin(B/'source-only-peer-pll.json'))
