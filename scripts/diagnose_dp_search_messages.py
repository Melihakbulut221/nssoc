import hashlib,zipfile,tarfile,io,pathlib,json,re,collections
P=pathlib.Path
blob=P('native.zip').read_bytes();assert hashlib.sha256(blob).hexdigest()=='31142082483dce4751f3abfe3af48cc1e76a48b4ce6f61ce9afbb6f29f5f3ced'
z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['bounded-native.tgz']
with tarfile.open(fileobj=io.BytesIO(z.read('bounded-native.tgz')),mode='r:gz') as t:raw=t.extractfile('native/lvs.lvsdb').read()
assert hashlib.sha256(raw).hexdigest()=='341e7da0e6d9552c99f31d058d0250846321051badf48c099add4e60edebc2aa'
text=raw.decode('utf-8')
messages=collections.Counter(re.findall(r'Maximum (?:complexity|depth) exhausted[^"\r\n]*',text))
r={'status':'RAW_SERIALIZED_DIAGNOSTIC_ONLY','accepted':False,'source_run':43587554414,'database_sha256':hashlib.sha256(raw).hexdigest(),'search_limit_messages':[{'message':k,'count':v} for k,v in messages.items()],'message_count':sum(messages.values()),'scope':'Only exact embedded search-limit strings counted from immutable native serialization in cloud. No KLayout object loading, geometry edits, netlist reinterpretation or LVS acceptance. Zero messages does not prove no limit exhaustion.'}
P('out').mkdir();P('out/search-limit-messages.json').write_text(json.dumps(r,indent=2))
