import subprocess,json,zipfile,tarfile,hashlib,io
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
r=json.loads(subprocess.check_output(['gh','api',P+'actions/runs/43630345267']));assert r['status']=='completed' and r['head_sha']=='bdd7cc588490425ff98c4718ea8986ecc06a128a'
meta=json.loads(subprocess.check_output(['gh','api',P+'actions/artifacts/14128012721']));assert meta['workflow_run']['id']==43630345267 and meta['digest']=='sha256:d32dd9bb9e0cc1d25f34e29cfbec4bb71908bef7bcaaa577327719602dcd3570'
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14128012721/zip']);assert hashlib.sha256(b).hexdigest()=='d32dd9bb9e0cc1d25f34e29cfbec4bb71908bef7bcaaa577327719602dcd3570'
z=zipfile.ZipFile(io.BytesIO(b));t=tarfile.open(fileobj=io.BytesIO(z.read('build.tgz')),mode='r:gz');result={'source_run':43630345267,'source_head':r['head_sha'],'source_conclusion':r['conclusion'],'files':{},'tails':{}}
for member in t:
 if not member.isfile():continue
 raw=t.extractfile(member).read();result['files'][member.name]=hashlib.sha256(raw).hexdigest()
 if member.name.endswith('/soc_top.mapped.json'):
  m=json.loads(raw)['modules']['soc_top'];candidates={n:c for n,c in m['cells'].items() if c['type'].startswith('sg13g2_df') and ('soc_pcie_replay_tx.v:310.' in c.get('attributes',{}).get('src','') or 'soc_pcie_replay_tx.v:309.' in c.get('attributes',{}).get('src',''))};result['sequential_source_candidates']=candidates
  aliases={n:v for n,v in m['netnames'].items() if 'replay_eop' in n or n.endswith('.core_eop')};result['eop_aliases']=aliases
  bits={b for v in aliases.values()for b in v['bits']};result['alias_drivers']={n:c for n,c in m['cells'].items() if any(c['port_directions'][pin]=='output' and bits.intersection(bs) for pin,bs in c['connections'].items())}
 if member.name.endswith(('rtl-driver.log','synthesis-driver.log','/syn.log')):result['tails'][member.name]=raw.decode(errors='replace')[-5000:]
Path('out').mkdir();Path('out/mapping-diagnosis.json').write_text(json.dumps(result,indent=2))
