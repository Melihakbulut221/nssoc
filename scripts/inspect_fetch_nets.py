import json,hashlib,pathlib,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
p=pathlib.Path('hw/soc/out/corrpre-pcie-mbist-native-boot/synthesis/soc_top.mapped.json')
assert hashlib.sha256(p.read_bytes()).hexdigest()=='13f96b84486caff79ce53b1e183d98443875208b26d962dfe9d95e62878d40d5'
m=json.loads(p.read_text())['modules']['soc_top']
nets={k:v for k,v in m['netnames'].items() if any(w in k.lower() for w in ('instr','fetch','prefetch','mi_','bus_data','row_'))}
assert nets
out=pathlib.Path('fetch-net-inventory');out.mkdir()
(out/'result.json').write_text(json.dumps(dict(source_head=os.environ['GITHUB_SHA'],mapped_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),netnames=nets,ports=m['ports'],accepted=False),indent=2))
for k,v in nets.items():print(k,len(v['bits']))
