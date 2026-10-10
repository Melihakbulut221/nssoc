from pathlib import Path
import datetime, hashlib, json, shutil, difflib
R=Path.cwd();B=Path(__file__).resolve().parent

def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
products=[R/'scripts/generate_pcie_integrity_command_v25.py',R/'hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v25.v',R/'hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v25.v',R/'scripts/check_pcie_gen3_continuous_rx_integrity_v25.py',R/'hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v25',R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v25.py',R/'sw/tests/test_pcie_gen3_continuous_rx_integrity_v25.py',R/'sw/tests/test_pcie_gen3_integrity_v25_command.py',R/'sw/tests/test_pcie_gen3_integrity_v25_architecture.py',R/'sw/tests/test_pcie_gen3_integrity_v25_block_burst.py']
# Inherited runtime closure, plus the exact actually loaded V23 reference/helper
# bodies. No active checkpoints or mutable live capture paths enter this cut.
old=json.loads((R/'hw/soc/out/pcie-integrity-v24-20261006/source-freeze02.json').read_text())
paths=[]
for name in old['sources']:
 p=Path(name)
 if '.local/' in name or '/tools/cocotb-venv/' in name or '/.venv/' in name:paths.append(p)
extra=['scripts/characterize_pcie_clock_trim_stream_v2.py','scripts/check_pcie_integrity.py','scripts/check_pcie_integrity_native.py','scripts/cocotb_results.py','scripts/generate_pcie_integrity_ingress_v11.py','scripts/generate_pcie_crc_candidates_v3.py','sw/tests/test_pcie_gen3_integrity_v3_crc.py','sw/tests/test_pcie_gen3_integrity_v23_miter.py','sw/tests/test_pcie_gen3_integrity_v23_block_burst.py','sw/tests/test_pcie_gen3_continuous_rx_integrity_v23.py','hw/soc/rtl/pcie/soc_pcie_gen3_framer_rx_integrity_v23.v','hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v23.v','hw/soc/rtl/pcie/soc_pcie_gen3_ingress_integrity_v11.v','hw/soc/rtl/pcie/soc_pcie_gen3_data_descrambler.v','hw/soc/rtl/pcie/soc_pcie_gen3_ingress.v','scripts/check_pcie_gen3_continuous_rx_integrity_v23.py','hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v23','hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py']
paths += products+[R/p for p in extra]
paths += [B/n for n in ['architecture-contract02.json','integration-audit02.json','architecture-source-peer-vco01.json','source-bridge-initial01.json','source-bridge-draft02.json','companion-bridge-initial01.json','preliminary-writer-peer-vco01.json','preliminary-command-component-peer-vco02.json','collection01.log']]
paths += [p for p in (B/'draft-before-unknown-control02').rglob('*') if p.is_file()]
paths += [p for p in (B/'static-test-construction01').rglob('*') if p.is_file()]
paths += [B/'unknown-control-supplement02.json',B/'source-derivation01.json',Path(__file__)]
D=B/'source-snapshot01';D.mkdir()
for p in products:
 q=D/p.relative_to(R);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
selected={name:dict(path=str(Path(shutil.which(name)).absolute()),**pin(shutil.which(name)))for name in ('iverilog','vvp')}
record=dict(status='FROZEN_V25_REGISTERED_COMMAND_SOURCE_PENDING_INDEPENDENT_PEER',utc=datetime.datetime.now(datetime.UTC).isoformat(),product_sources={str(p.relative_to(R)):pin(p)for p in products},sources={str(p):pin(p)for p in dict.fromkeys(paths)},selected_tools=selected,functional_predicates=42,excluded_MAX4118_predicates=1,profile='CPU6, inherited pytest/native 2GiB AS, 1GiB entry/528MiB continuous+terminal shared floor, no healthy elapsed timeout.',scope='V23-derived one-stage parser-to-ring command. Explicit nominal +1 relation; independent 19-case public byte/metadata scoreboard and real minimum16/normal64 block transactions. No general cycle equivalence, no physical/adoption claim.',runtime_scope='Exact selected Icarus wrappers/underlying tools and runtime payload plus lexical pytest/cocotb interpreters and configuration; no claim of a fully hermetic operating system.')
(B/'source-freeze01.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(freeze=pin(B/'source-freeze01.json'),products=len(products),inputs=len(record['sources']))))
