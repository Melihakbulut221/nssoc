from pathlib import Path
import ast,hashlib,json,difflib,datetime
R=Path.cwd();B=Path(__file__).resolve().parent
pin=lambda p:dict(bytes=Path(p).stat().st_size,sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest())
paths=['scripts/generate_pcie_integrity_prefix_v24.py','hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v24.v','hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v24.v','hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v24','scripts/check_pcie_gen3_continuous_rx_integrity_v24.py','hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v24.py','sw/tests/test_pcie_gen3_continuous_rx_integrity_v24.py','sw/tests/test_pcie_gen3_integrity_v24_miter.py','sw/tests/test_pcie_gen3_integrity_v24_block_burst.py','sw/tests/test_pcie_gen3_integrity_v24_prefix.py']
products={p:pin(R/p)for p in paths}
sources=json.loads((B/'component-source-freeze02.json').read_text())['sources']
sources.update({str(R/p):v for p,v in products.items()})
for p in ['architecture-source-peer-rx01.json','component-source-peer-vco02.json','component-status01.json','component-controls01.xml','component-controls01.log','context_observer01.vh','source-inverse01.log']:
 sources[str(B/p)]=pin(B/p)
for n in ['test_pcie_gen3_integrity_v23_miter.py','test_pcie_gen3_integrity_v23_block_burst.py','test_pcie_gen3_continuous_rx_integrity_v23.py']:
 sources[str(R/'sw/tests'/n)]=pin(R/'sw/tests'/n)
freeze=dict(status='FROZEN_V24_PREFIX_CONTEXT_PRODUCT_PENDING_ACTUAL_FULL_CONTROLS',utc=datetime.datetime.now(datetime.UTC).isoformat(),product_sources=products,sources=sources,selected_tools=json.loads((B/'component-source-freeze02.json').read_text())['selected_tools'],functional_predicates=42,excluded_MAX4118_predicates=2,profile=dict(MAX_ENCODED_BYTES=150,RING_DWORDS=64,CPU=6,AS_bytes=2*1024**3,healthy_timeout=None),scope='Exact V23 public-cycle behavior retained. Completed component5 controls are prerequisite only; full18case direct/miter, originalfaults, actualcontext bank burst andEDS/XZ packing must complete. No mapping or timing acceptance.')
f=B/'source-freeze01.json';assert not f.exists();f.write_text(json.dumps(freeze,indent=2)+'\n')
old=(B/'launch_component02.py').read_text();s=old
s=s.replace('component-source-freeze02.json','source-freeze01.json').replace('5bac8dc9531a542919b05ebd76cd397a33a64a31d69c03e9754d92626f6f84c9',pin(f)['sha256']).replace('component-source-peer-vco02.json','source-only-peer-vco01.json').replace('PASS_SOURCE_ONLY_V24_MATRIX_COMPONENT_CONTROLS','PASS_SOURCE_ONLY_V24_PREFIX_CONTEXT_IMPLEMENTATION')
s=s.replace('nssoc-integrity-v24-matrix-controls01','nssoc-integrity-v24-full-controls01').replace('component-status01.json','status01.json').replace('component-owner01.json','owner01.json').replace('component-controls01','controls01')
s=s.replace("str(B/'test_matrix_relation01.py')", ",".join("str(R/'"+p+"')"for p in paths if p.startswith('sw/tests/'))+",'-k','not 4118'")
s=s.replace("Standalone V24 finite matrix relation and four actual mutants only; product RTL remains V23. No native mapping or public-cycle acceptance from this component proof. Existing PLL untouched.","V24 full42 selected controls with unchanged18 public profiles and originalV23 cycle schedule;2MAX4118 tests explicitly excluded. Native mapping remains separately gated. Existing PLL untouched.")
launcher=B/'launch_controls01.py';assert not launcher.exists();launcher.write_text(s);ast.parse(s)
old_detach=(B/'detach_component02.py').read_text();d=old_detach
# Exact tuple substitutions avoid changing unrelated numeric hashes/output namespaces.
d=d.replace('launch_component02.py','launch_controls01.py').replace(repr(pin(B/'launch_component02.py')),repr(pin(launcher)))
d=d.replace('component-source-freeze02.json','source-freeze01.json').replace(repr(pin(B/'component-source-freeze02.json')),repr(pin(f)))
d=d.replace('component-source-peer-vco02.json','source-only-peer-vco01.json').replace('PASS_SOURCE_ONLY_V24_MATRIX_COMPONENT_CONTROLS','PASS_SOURCE_ONLY_V24_PREFIX_CONTEXT_IMPLEMENTATION')
d=d.replace('nssoc-integrity-v24-matrix-controls01','nssoc-integrity-v24-full-controls01').replace('component-status01.json','status01.json').replace('component-detached-once01.json','detached-once01.json').replace('component-detached-receipt01.json','detached-receipt01.json').replace('component-launch01.log','launch01.log')
p=B/'detach_controls01.py';assert not p.exists();p.write_text(d);ast.parse(d)
bridges=dict(product_full_inverse='Generator contains seven explicit unique edits; inverse restores entire pinned197239B V23 framer.',support={name:dict(parent=str(parent),parent_pin=pin(parent),candidate_pin=pin(B/name),full_diff=''.join(difflib.unified_diff(parent.read_text().splitlines(True),(B/name).read_text().splitlines(True))))for name,parent in [('launch_controls01.py',B/'launch_component02.py'),('detach_controls01.py',B/'detach_component02.py')]},source_differences={name:''.join(difflib.unified_diff((R/name.replace('_v24','_v23')).read_text().splitlines(True),(R/name).read_text().splitlines(True)))for name in paths if (R/name.replace('_v24','_v23')).exists()},scope='Preserves completed component files; no HDL test or producer launch by this preparer.')
(B/'source-bridges01.json').write_text(json.dumps(bridges,indent=2)+'\n')
print('freeze',pin(f));print('launcher',pin(launcher));print('detacher',pin(p));print('products',len(products),'sources',len(sources))
