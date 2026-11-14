import hashlib,zipfile,tarfile,io,pathlib,subprocess
P=pathlib.Path
blob=P('native.zip').read_bytes();assert hashlib.sha256(blob).hexdigest()=='31142082483dce4751f3abfe3af48cc1e76a48b4ce6f61ce9afbb6f29f5f3ced'
z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['bounded-native.tgz']
with tarfile.open(fileobj=io.BytesIO(z.read('bounded-native.tgz')),mode='r:gz') as t:raw=t.extractfile('native/lvs.lvsdb').read()
assert hashlib.sha256(raw).hexdigest()=='341e7da0e6d9552c99f31d058d0250846321051badf48c099add4e60edebc2aa'
P('/tmp/full-macro.lvsdb').write_bytes(raw)
assert subprocess.check_output(['klayout','-b','-v'],text=True).strip()=='KLayout 0.30.13'
subprocess.run(['klayout','-b','-zz','-r','scripts/diagnose_dp_bounded_mismatch.rb'],check=True,timeout=300)
