import os,subprocess,json,hashlib
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
paths=subprocess.check_output(['git','ls-files','-z','hw/soc/rtl','hw/soc/flow','hw/soc/tb','scripts/prepare_core_only_mainchip.sh','scripts/check_core_only_mainchip_mapping.py','scripts/build_core_only_mainchip.py']).decode().split('\0')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
before={p:sha(p)for p in paths if p and Path(p).is_file()}
subprocess.run(['bash','scripts/prepare_core_only_mainchip.sh'],check=True)
assert all(sha(p)==h for p,h in before.items())
p=Path('out/mapping.json');r=json.loads(p.read_text());r['source_binding']=dict(before=before,all_files_unchanged=True);p.write_text(json.dumps(r,indent=2))
