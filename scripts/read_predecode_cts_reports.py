import pathlib,subprocess,json,zipfile,hashlib
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s],timeout=60))
def source(aid,digest,name):
 meta=api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==43622573415 and meta['workflow_run']['head_sha']=='a3a79275ea42940b3c319c7c15cab2ae75f15109' and meta['digest']=='sha256:'+digest and not meta['expired']
 path=pathlib.Path(name)
 with path.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True)
 with path.open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==digest
 return zipfile.ZipFile(path)
r=api('actions/runs/43622573415');assert r['status']=='completed' and r['conclusion']=='success'
native=source(14124619734,'244a660873d74ae73e2913c1cd96546817d6a3e0474045a662ea566246adaac5','native.zip')
safe=source(14125635095,'27634a4fc273d1dfa52c6bb72cbfde2b50e8f7c3bf15fb5ff73cf31dbad72ace','safe.zip')
report=json.loads(safe.read('result.json'));assert report['sources_unchanged'] and not report['accepted']
out=pathlib.Path('out');out.mkdir();selected={};all_names=native.namelist();assert len(set(all_names))==len(all_names)
for name in all_names:
 path=pathlib.PurePosixPath(name)
 if not name.startswith('run/27-openroad-cts/') or path.suffix not in ('.rpt','.log','.json'):continue
 assert not path.is_absolute() and '..' not in path.parts
 raw=native.read(name);assert hashlib.sha256(raw).hexdigest()==report['outputs'][name]
 raw.decode('utf-8');dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 selected[name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
assert selected and any(n.endswith('.rpt')for n in selected)
(out/'index.json').write_text(json.dumps({'source_run':43622573415,'cts_odb_sha256':report['cts_odb_sha256'],'files':selected,'archive_members':all_names,'accepted':False,'scope':'Exact CTS text reports only; no new native run or acceptance'},indent=2))
