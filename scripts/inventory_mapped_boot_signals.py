import json,pathlib,hashlib,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
p=pathlib.Path('hw/soc/out/corrpre-pcie-mbist-native-boot/synthesis/soc_top.mapped.json')
sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha=='13f96b84486caff79ce53b1e183d98443875208b26d962dfe9d95e62878d40d5'
m=json.loads(p.read_text())['modules']['soc_top'];names={n:{'width':len(v['bits']),'bits':v['bits']}for n,v in m['netnames'].items()if n.startswith('u_ibex.')and any(k in n.lower()for k in ['csr','regfile','rf_','branch','exs_','mepc','mtvec','retire','instr_valid'])}
assert names
out=pathlib.Path('observer-inventory');out.mkdir()
(out/'result.json').write_text(json.dumps(dict(source_head=os.environ['GITHUB_SHA'],mapped_sha256=sha,source_binding=json.loads(pathlib.Path('out/source-binding.json').read_text()),signals=names,scope='Exact mapped named-net inventory only; not boot execution or acceptance.'),indent=2))
print('NAMED_CORE_SIGNALS',len(names))
