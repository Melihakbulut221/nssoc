import hashlib,zipfile,tarfile,io,pathlib,subprocess,json,sys
P=pathlib.Path
blob=P('native.zip').read_bytes();assert hashlib.sha256(blob).hexdigest()=='31142082483dce4751f3abfe3af48cc1e76a48b4ce6f61ce9afbb6f29f5f3ced'
z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['bounded-native.tgz']
with tarfile.open(fileobj=io.BytesIO(z.read('bounded-native.tgz')),mode='r:gz') as t:raw=t.extractfile('native/lvs.lvsdb').read()
assert hashlib.sha256(raw).hexdigest()=='341e7da0e6d9552c99f31d058d0250846321051badf48c099add4e60edebc2aa'
P('/tmp/full-macro.lvsdb').write_bytes(raw)
assert subprocess.check_output(['klayout','-b','-v'],text=True).strip()=='KLayout 0.30.13'
proc=subprocess.run(['klayout','-b','-zz','-r','scripts/diagnose_dp_bounded_mismatch.rb'],timeout=300)
P('out').mkdir(exist_ok=True)
P('out/reader-status.json').write_text(json.dumps({'native_returncode':proc.returncode,'reader_completed_successfully':proc.returncode==0,'report_exists':P('out/top-mismatch.json').is_file(),'accepted':False,'scope':'Preserve diagnostic report even if native reader aborts at finalization. Never convert native failure into success or LVS acceptance.'},indent=2))
sys.exit(0 if proc.returncode==0 else 1)

