# SPDX-License-Identifier: Apache-2.0
"""Read immutable top ports/counts without detailed cross-reference pair iteration."""
import pathlib,json,hashlib,zipfile,tarfile,io,collections,re,importlib.metadata
import klayout.db as db
P=pathlib.Path
assert importlib.metadata.version('klayout')=='0.30.13'
blob=P('native.zip').read_bytes();assert hashlib.sha256(blob).hexdigest()=='9bac7b5cb401e8b8fc28442197e3dba1cf3c2ce30cba523eae779d315c0c7848'
z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['bounded-native.tgz']
with tarfile.open(fileobj=io.BytesIO(z.read('bounded-native.tgz')),mode='r:gz') as t:
 raw=t.extractfile('native/lvs.lvsdb').read()
 decks=[m for m in t.getmembers() if m.isfile() and m.name.endswith('/sg13g2.lvs')];assert len(decks)==1
 deck=t.extractfile(decks[0]).read().decode()
 dl=deck.splitlines();selected=set()
 for i,line in enumerate(dl):
  if any(token in line for token in ['top_lvl_pins','make_top_level_pins','flag_missing_ports']):selected.update(range(max(0,i-5),min(len(dl),i+9)))
 deck_context=[{'line':i+1,'text':dl[i]} for i in sorted(selected)]
assert hashlib.sha256(raw).hexdigest()=='94f00e5d650caeab65c39659de9dea7b1cb3cf0f5be87ba8c1c95eccd51dcd36'
P('/tmp/matrix.lvsdb').write_bytes(raw)
messages=collections.Counter(re.findall(r'Maximum (?:complexity|depth) exhausted[^"\r\n]*',raw.decode()))
lvs=db.LayoutVsSchematic();lvs.read('/tmp/matrix.lvsdb')
top='RM_IHPSG13_2P_256x16_c2_bm_bist'
def value(v):return v() if callable(v) else v
rows={}
for side,nl in [('layout',lvs.netlist()),('reference',lvs.reference)]:
 hits=[c for c in nl.each_circuit() if c.name.casefold()==top.casefold()];assert len(hits)==1
 c=hits[0]
 pins=[{'name':value(p.name),'id':value(p.id)} for p in c.each_pin()]
 devices=collections.Counter(d.device_class().name for d in c.each_device())
 children=collections.Counter(s.circuit_ref().name for s in c.each_subcircuit())
 rows[side]={'name':c.name,'pins':pins,'direct_devices':dict(devices),'children':dict(children),'net_count':sum(1 for _ in c.each_net()),'named_nets':sorted(value(n.name) for n in c.each_net() if value(n.name))}
r={'status':'TOP_INVENTORY_ONLY','accepted':False,'source_run':43591517998,'database_sha256':'94f00e5d650caeab65c39659de9dea7b1cb3cf0f5be87ba8c1c95eccd51dcd36','top':rows,'deck_port_context':deck_context,'search_limit_messages':dict(messages),'scope':'Saved netlist top pin names, direct device class counts and child type counts only. No detailed xref pair traversal, no graph changes, no acceptance.'}
P('out').mkdir();P('out/top-inventory.json').write_text(json.dumps(r,indent=2))
