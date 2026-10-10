#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Write a separately named source recipe; never run simulation or alter parents."""
import ast
import hashlib
import json
from pathlib import Path
B=Path(__file__).resolve().parent
R=Path.cwd()
old=R/'scripts/characterize_pcie_vco_v6_feedback_v1.py'
s=old.read_text(); tree=ast.parse(s)
segments={x.name:ast.get_source_segment(s,x) for x in tree.body if isinstance(x,(ast.FunctionDef,ast.ClassDef))}
changes={
'Meter': [('explicit13 contact','explicit31 contact'),('== 437,','== 455,')],
'deck': [('Actual437-device physical VCOv6 loaded /80 prerequisite','Actual455-device VCOv6 and divider wire RC loaded /80 prototype')],
'guard': [('nssoc-vco-v6-feedback-*','nssoc-vco-v6-divider-wire-*')],
'run_native': [
('                            owner.complete(proc)\n                            break','                            owner.complete(proc)\n                            owner.check()\n                            free, used = guard(out)\n                            free_min, own_peak = min(free_min, free), max(own_peak, used)\n                            break'),
('    fifo.unlink()\n    return result','    owner.check()\n    free, used = guard(out)\n    fifo.unlink()\n    return result')],
'run': [('Finite27C loaded /80; no PLL lock, full divider RC, substrate spreading, PVT, jitter, BER, or foundry qualification.','Finite27C loaded /80 with actual VCO and divider metal RC; explicit ideal body boundaries, no substrate spreading, device-wire coupling, RF/PVT, PLL lock, BER or foundry qualification.')],
}
parts=[];bridge={}
for name,edits in changes.items():
    orig=segments[name]; cur=orig
    for a,b in edits:
        assert cur.count(a)==1,(name,a)
        cur=cur.replace(a,b)
    inv=cur
    for a,b in reversed(edits):
        assert inv.count(b)==1
        inv=inv.replace(b,a)
    assert inv==orig
    parts.append(cur)
    bridge[name]={'old':orig,'new':cur,'operations':edits,'full_inverse':True}
head=(B/'characterizer-head.txt').read_text()
tail='''
# Unchanged functions retain exact code/defaults/closures in private globals.
_scope = dict(previous._scope, __file__=__file__, __name__=__name__, SOURCE=CHAIN,
              TOP=TOP, config=config, Meter=Meter, deck=deck, guard=guard,
              run_native=run_native, run=run)
_overrides = {"config", "Meter", "deck", "guard", "run_native", "run"}
for _name, _value in previous._scope.items():
    if isinstance(_value, types.FunctionType) and _value.__globals__ is previous._scope and _name not in _overrides:
        _scope[_name] = types.FunctionType(_value.__code__, _scope, _value.__name__, _value.__defaults__, _value.__closure__)
# Copied functions above use the inherited, independently frozen support names.
for _name in ("deck", "guard", "run_native", "run"):
    _value = globals()[_name]
    _scope[_name] = types.FunctionType(_value.__code__, _scope, _value.__name__, _value.__defaults__, _value.__closure__)
run, main = _scope["run"], _scope["main"]

if __name__ == "__main__":
    raise SystemExit(main())
'''
text=head+'\n\n'+'\n\n\n'.join(parts)+'\n'+tail
out=R/'scripts/characterize_pcie_vco_v6_divider_wire_v1.py'
compile(text,str(out),'exec');out.write_text(text)
pin=lambda p: {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(B/'characterizer-source-bridge.json').write_text(json.dumps({'status':'SOURCE_ONLY_EXPLICIT_FUNCTION_DELTAS','parent':{str(old):pin(old)},'new':{str(out):pin(out)},'functions':bridge,'new_head':pin(B/'characterizer-head.txt'),'execution':False},indent=2)+'\n')
print(pin(out))
