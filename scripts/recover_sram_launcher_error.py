import hashlib,zipfile,tarfile,io,json,pathlib
b=pathlib.Path('native.zip').read_bytes();assert hashlib.sha256(b).hexdigest()=='2eace46fa383aeec32bb3ef2ada5d8e7c509f87a530e199672fa18210d7b7ee3'
z=zipfile.ZipFile(io.BytesIO(b));names=[n for n in z.namelist() if n.endswith('.tgz')];assert len(names)==1
with tarfile.open(fileobj=io.BytesIO(z.read(names[0])),mode='r:gz') as t:
 raw=t.extractfile('native/run.log').read();assert len(raw)==111 and hashlib.sha256(raw).hexdigest()=='a6462a15b9f25d285837ad48c54d8a640b99bc1305c36114fdfad3ea8c27d842'
 text=raw.decode();assert all(not l.lstrip().lower().startswith(('.subckt','x','m','r','c')) for l in text.splitlines())
 pathlib.Path('out').mkdir();pathlib.Path('out/launcher-error.json').write_text(json.dumps({'run_id':43524969803,'job_id':132228353121,'launcher_error':text}));print(text)
