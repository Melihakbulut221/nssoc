import os,json,hashlib,re,io
from cloud_core_only_postgrt import ROOT,completed,archive,sha
OUT=ROOT/'hw/soc/out/core-only-slew-parasitic-comparison'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 sources=[]
 for label,rid,head,name,aid,digest in [
  ('baseline',44459123476,'fd1630e82067aef73a85976449fb1cdec3030fbc','core-only-setup-neighbor-extraction-44459123476',14499837022,'a6ec8a0379054fabe7db001e5d1e3e9cdb0fd83d0f51c09f9baf123d655c79dc'),
  ('slew',44468611583,'4736499767af0cb0853f6e5dd792593f362615a1','core-only-slew-neighbor-extraction-44468611583',14503269406,'b41baf9c021dd370de9538a652764e02ef1a1c36d84994c836aa7a3280d487a0')]:
  run=completed(rid,head);assert run['run_attempt']==1
  z,m=archive(run,name);assert m['id']==aid and m['digest']=='sha256:'+digest
  r=json.loads(z.read('result.json'));assert r['source_head']==head and r['sources_unchanged']
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
  for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  selected=[]
  for n in r['outputs']:
   if '/2-nssoc-coreonlyextractedsta/'in n and (n.endswith('.rpt')or n.endswith('.json')):
    p=OUT/label/n;assert p.resolve().is_relative_to(OUT.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n));selected.append(n)
  assert sum(n.endswith('/checks.rpt')for n in selected)==3
  (OUT/label/'source-result.json').write_bytes(z.read('result.json'))
  targets={'nssoc_sta_n_55232','nssoc_sta_n_54157','nssoc_sta_n_58480','net3463','nssoc_sta_n_55230','nssoc_sta_n_55231','nssoc_sta_n_54156','net4881','net3900','nssoc_sta_n_58474','nssoc_sta_n_58475','nssoc_sta_n_58477','nssoc_sta_n_58479'}
  raw=z.read('extraction/1-nssoc-coreonlyroutercx/nom/soc_top.nom.spef');text=raw.decode();names={};blocks={};current=None;unit_lines=[]
  for line in io.StringIO(text):
   line=line.rstrip('\n');mname=re.fullmatch(r'(\*\d+)\s+(\S+)',line)
   if mname:names[mname[1]]=mname[2]
   if re.match(r'\*[CR]_UNIT\s',line):unit_lines.append(line)
   if line.startswith('*D_NET '):
    fields=line.split();name=names.get(fields[1],fields[1]);current=name if name in targets else None
    if current:assert current not in blocks;blocks[current]=[]
   if current:blocks[current].append(line)
   if line=='*END':current=None
  assert set(blocks)==targets,(targets-set(blocks));assert len(unit_lines)==2
  resolved={name:[re.sub(r'\*\d+',lambda m:names.get(m[0],m[0]),line)for line in lines]for name,lines in blocks.items()}
  (OUT/label/'target-spef.json').write_text(json.dumps(dict(spef_sha256=hashlib.sha256(raw).hexdigest(),units=unit_lines,blocks=resolved,scope='Exact resolved-name SPEF blocks; resistance sums are not effective resistance; coupling remains explicit.'),indent=2)+'\n')
  sources.append(dict(label=label,run=rid,head=head,artifact=m,verified_outputs=len(r['outputs'])))
 result=dict(source_head=os.environ['GITHUB_SHA'],sources=sources,accepted=False,scope='Exact source-verified reports for electrical regression analysis; no new simulation or signoff.')
 result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()}
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
