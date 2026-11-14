import hashlib,zipfile,tarfile,io,pathlib,json,re,collections
P=pathlib.Path
blob=P('native.zip').read_bytes();assert hashlib.sha256(blob).hexdigest()=='95e9cf179b818929781a79cca4e5a089e2e04d51a724a0b01752ead2c057fc05'
z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['bounded-native.tgz']
with tarfile.open(fileobj=io.BytesIO(z.read('bounded-native.tgz')),mode='r:gz') as t:raw=t.extractfile('native/lvs.lvsdb').read()
assert hashlib.sha256(raw).hexdigest()=='839fc525689e193b0dd1146188c274bb2dfcc58f470fe345a17e9044e0de14c5'
text=raw.decode('utf-8')
messages=collections.Counter(re.findall(r'Maximum (?:complexity|depth) exhausted[^"\r\n]*',text))
r={'status':'RAW_SERIALIZED_DIAGNOSTIC_ONLY','accepted':False,'source_run':43589897545,'database_sha256':hashlib.sha256(raw).hexdigest(),'search_limit_messages':[{'message':k,'count':v} for k,v in messages.items()],'message_count':sum(messages.values()),'scope':'Only exact embedded search-limit strings counted from immutable native serialization in cloud. No KLayout object loading, geometry edits, netlist reinterpretation or LVS acceptance. Zero messages does not prove no limit exhaustion.'}
P('out').mkdir();P('out/search-limit-messages.json').write_text(json.dumps(r,indent=2))
