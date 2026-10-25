# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import copy,json
import prepare01 as m
B=Path(__file__).resolve().parent;T=B/'control-fixture01';T.mkdir();source=T/'source.bin';source.write_bytes(bytes(range(251))*7)
manifest=m.split(source,T/'parts',113,'tiny.bin');checks=[]
assert m.verify(manifest,T/'parts')['bytes']==1757;checks.append('positive_uneven_final_piece')
def reject(name,doc):
 try:m.verify(doc,T/'parts')
 except AssertionError:checks.append(name)
 else:raise AssertionError(name+' survived')
q=copy.deepcopy(manifest);q['parts'][1]['offset']+=1;reject('wrong_offset',q)
q=copy.deepcopy(manifest);q['parts'][1],q['parts'][2]=q['parts'][2],q['parts'][1];reject('reordered_piece',q)
p=T/'parts'/manifest['parts'][0]['name'];original=p.read_bytes();p.write_bytes(bytes([original[0]^1])+original[1:]);reject('actual_one_byte_corruption',manifest);p.write_bytes(original)
q=copy.deepcopy(manifest);q['parts']=q['parts'][:-1];reject('missing_tail',q)
assert m.verify(manifest,T/'parts')['sha256']==m.pin(source)['sha256']
(B/'controls01.json').write_text(json.dumps(dict(status='PASS_MULTIPART_BYTE_IDENTITY_CONTROLS',controls=checks,method=m.pin(__file__),splitter=m.pin(m.__file__)),indent=2)+'\n');print(checks)
