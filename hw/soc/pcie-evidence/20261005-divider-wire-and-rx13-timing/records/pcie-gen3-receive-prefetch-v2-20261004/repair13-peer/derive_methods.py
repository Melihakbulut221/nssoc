# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate future saved-output peer/sealer/controller; no native dispatch."""
from pathlib import Path
import ast,json,hashlib,difflib,datetime
O=Path(__file__).resolve().parent;B=O.parent;C=B/'repair13-continuation01';R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
pairs=[]
for old,new in [(B/'repair12-peer/review.py',O/'review.py'),(B/'repair12-peer/seal.py',O/'seal.py'),(B/'repair12-continuation01/run.py',C/'run.py')]:
 original=old.read_text();text=original.replace('repair12','repair13').replace('repair-12','repair-13').replace('RX12','RX13').replace('rx12_','rx13_')
 if new.name in ['review.py','seal.py']:
  text=text.replace('repair11-peer02','repair12-peer').replace('vs11_ns','vs12_ns').replace('vs_published11_ns','vs_published12_ns').replace('pcie-rx-repair11-finite','pcie-rx-repair12-finite').replace("'prior-published/repair11/'","'prior-published/repair12/'").replace('Earlier routed11 inputs','Earlier routed12 inputs')
 if new.name=='run.py':
  text=text.replace('WAITING_EXISTING_EXACT_RX13_DRT02','WAITING_EXISTING_EXACT_RX13_DRT01')
  anchor="    require(sorted(os.sched_getaffinity(0)) == [8], 'Controller CPU8')\n"
  assert text.count(anchor)==1;text=text.replace(anchor,anchor+"    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == manifest['boot_id'], 'Same recorded boot identity')\n")
  anchor="                    stage['returncode'] = owner.complete(process)\n";assert text.count(anchor)==1
  text=text.replace(anchor,anchor+"                    owner.check()\n                    require(shutil.disk_usage('/dev/shm').free >= FLOOR,\n                            '528MiB terminal scratch floor')\n")
  anchor="    return 0\n";assert text.count(anchor)==1
  text=text.replace(anchor,"    # A stop delivered during final complete/save/context teardown must propagate.\n    try:\n        owner.check()\n    except BaseException as error:\n        record.update(status='FAILED_RETAINED_NO_DEPENDENT_BYPASS', error=repr(error))\n        save()\n        raise\n"+anchor)
 assert not new.exists();ast.parse(text);new.write_text(text)
 a=original.splitlines(True);z=text.splitlines(True);ops=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,a,z,autojunk=False).get_opcodes():ops.append(dict(tag=tag,before=''.join(a[i:j]),after=''.join(z[k:l])))
 assert ''.join(x['before'] for x in ops)==original and ''.join(x['after'] for x in ops)==text
 pairs.append(dict(before=dict(path=str(old),**pin(old)),after=dict(path=str(new),**pin(new)),opcodes=ops))
(O/'source-bridge.json').write_text(json.dumps(pairs[:2],indent=2)+'\n')
(C/'source-bridge.json').write_text(json.dumps(pairs[2],indent=2)+'\n')
(O/'source-freeze.json').write_text(json.dumps({str(p):pin(p) for p in [O/'review.py',O/'seal.py',O/'source-bridge.json',Path(__file__)]},indent=2)+'\n')
print(json.dumps({x['after']['path']:{k:x['after'][k] for k in ['bytes','sha256']} for x in pairs}))
