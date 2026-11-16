import os,json,hashlib,subprocess
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
paths=subprocess.check_output(['git','ls-files','-z','hw/soc/rtl','hw/soc/flow','hw/soc/tools.soc.mk']).decode().split('\0')
paths=[p for p in paths if p and Path(p).is_file()]
assert 'hw/soc/rtl/pcie/soc_pcie_credit_tx.v'in paths
paths+=['scripts/prepare_predecode_mainchip.sh','scripts/check_predecode_mainchip_mapping.py','scripts/require_credit_crc_qualification.py','scripts/require_peer_ready_qualification.py','scripts/qualify_pcie_peer_ready_certificate.py',__file__]
before={p:sha(p)for p in paths}
subprocess.run(['bash','scripts/prepare_predecode_mainchip.sh'],check=True)
assert all(sha(p)==h for p,h in before.items())
p=Path('out/mapping.json');r=json.loads(p.read_text())
assert not r['accepted']and not r['mapped_boot_passed']and not r['final_timing_complete']
r['source_binding']=dict(kind='Tracked SoC RTL and flow plus explicit build/qualification scripts',before=before,all_files_unchanged=True,scope='Repository source identity; generated firmware and mapped netlist are separately hashed outputs. Not a claim of complete compiler dependency tracing.')
r['status']='MAPPED_PEER_READY_ACK_MAINCHIP_REQUIRES_NEW_BOOT_AND_PHYSICAL_VALIDATION'
p.write_text(json.dumps(r,indent=2))
