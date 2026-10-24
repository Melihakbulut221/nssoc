# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import hashlib,json,difflib
B=Path(__file__).resolve().parent
p=B/'launch_probe01.py';before=p.read_text()
old='''        with m.life.ProcessOwner(B/'controller-owned.json') as owner:
            owner.check()
            native=m.run(OUT,.6,'')
            owner.check()
            m._scope['guard'](OUT)
        owner.check()'''
new='''        native=run_with_boundary_signals()
        m._scope['guard'](OUT)'''
addition='''def run_with_boundary_signals():
    # Outside the native owner there are no owned children. Fail immediately
    # so cancellation cannot remain trapped in an inactive outer owner's flag.
    # The inner ProcessOwner temporarily installs its graceful native handler
    # and restores this one, covering both entry and exit handoff boundaries.
    def stop(signum, frame):
        raise RuntimeError("Controller received " + signal.Signals(signum).name)
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    try:
        for sig in previous:signal.signal(sig,stop)
        return m.run(OUT,.6,'')
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)


'''
ops=[('import os\n','import os\nimport signal\n',1),('source-freeze.json','source-freeze02.json',3),('source-only-peer-rx.json','source-only-peer02-rx.json',2),(old,new,1),('def controller():',addition+'def controller():',1)]
s=before
for a,b,n in ops:
 assert s.count(a)==n,(a,s.count(a));s=s.replace(a,b)
inv=s
for a,b,n in reversed(ops):assert inv.count(b)==n;inv=inv.replace(b,a)
assert inv==before
out=B/'launch_probe02.py';out.write_text(s)
pin=lambda p:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(B/'launcher02-source-bridge.json').write_text(json.dumps({'status':'ADDITIVE_HANDOFF_FIX_SOURCE','parent':{str(p):pin(p)},'new':{str(out):pin(out)},'operations':ops,'whole_byte_inverse':True,'diff':''.join(difflib.unified_diff(before.splitlines(True),s.splitlines(True)))},indent=2)+'\n')
print(pin(out))
