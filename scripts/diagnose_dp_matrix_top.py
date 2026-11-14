# SPDX-License-Identifier: Apache-2.0
"""Read immutable top ports/counts without detailed cross-reference pair iteration."""
import pathlib,json,hashlib,zipfile,tarfile,io,collections,re,importlib.metadata
import klayout.db as db
P=pathlib.Path
assert importlib.metadata.version('klayout')=='0.30.13'
blob=P('native.zip').read_bytes();assert hashlib.sha256(blob).hexdigest()=='d9f0cd937bc43ab7550c22d672835d2092556f2f64aac10f0584d0ca945186bc'
z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['bounded-native.tgz']
with tarfile.open(fileobj=io.BytesIO(z.read('bounded-native.tgz')),mode='r:gz') as t:
 raw=t.extractfile('native/lvs.lvsdb').read()
 decks=[m for m in t.getmembers() if m.isfile() and m.name.endswith('/sg13g2.lvs')];assert len(decks)==1
 deck=t.extractfile(decks[0]).read().decode()
 dl=deck.splitlines();selected=set()
 for i,line in enumerate(dl):
  if any(token in line for token in ['top_lvl_pins','make_top_level_pins','flag_missing_ports']):selected.update(range(max(0,i-5),min(len(dl),i+9)))
 deck_context=[{'line':i+1,'text':dl[i]} for i in sorted(selected)]
assert hashlib.sha256(raw).hexdigest()=='40bf9721db12569e03a51b411a211b8fb8c51fccad02f554578c127a0a8e346c'
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
 degrees=collections.Counter();empty_names=[]
 for n in c.each_net():
  degree=(value(n.terminal_count),value(n.subcircuit_pin_count),value(n.pin_count))
  degrees[str(degree)]+=1
  if sum(degree)==0:empty_names.append(value(n.name))
 rows[side]={'name':c.name,'pins':pins,'direct_devices':dict(devices),'children':dict(children),'net_count':sum(1 for _ in c.each_net()),'net_degree_counts':dict(degrees),'empty_net_names':empty_names,'named_nets':sorted(value(n.name) for n in c.each_net() if value(n.name))}
r={'status':'TOP_INVENTORY_ONLY','accepted':False,'source_run':43592362942,'database_sha256':'40bf9721db12569e03a51b411a211b8fb8c51fccad02f554578c127a0a8e346c','top':rows,'deck_port_context':deck_context,'search_limit_messages':dict(messages),'scope':'Saved netlist top pin names, direct device class counts and child type counts only. No detailed xref pair traversal, no graph changes, no acceptance.'}
P('out').mkdir();P('out/top-inventory.json').write_text(json.dumps(r,indent=2))
