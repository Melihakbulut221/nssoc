"""Explicit zero-delay functional aliases for unsupported delayed timing pins.
This is a DERIVED simulation model, never foundry/native timing or SDF evidence.
Original IHP file remains byte-identical. All original license notices retained.
"""
import re,hashlib
SOURCE_SHA='28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4'
def adapt(source):
 assert hashlib.sha256(source.encode()).hexdigest()==SOURCE_SHA
 changed=[]
 def module(match):
  text=match.group(0);name=match.group(1)
  # CVC parses unsupported ifnone edge paths even with +nospecify.
  # Explicitly omit ALL specify text only in the derived functional mode.
  # Icarus reference and macro-off model retain original specify sections.
  text=re.sub(r'\bspecify\b.*?\bendspecify\b',lambda m:'\n`ifndef NSSOC_CVC_ZERO_DELAY\n'+m.group(0)+'\n`endif\n',text,flags=re.S)
  if 'delayed_'not in text:return text
  aliases={}
  for kind,args in re.findall(r'\$(setuphold|recrem)\s*\((.*?)\);',text,re.S):
   v=[x.strip()for x in args.split(',')]
   assert len(v)==9 and v[2:7]==['0','0','notifier','',''],(name,kind,v)
   for event,pin in zip(v[:2],v[7:]):
    e=re.fullmatch(r'(?:posedge|negedge)\s+(\w+)',event);assert e
    actual=e.group(1);assert pin=='delayed_'+actual
    assert pin not in aliases or aliases[pin]==actual
    aliases[pin]=actual
  assert aliases and set(re.findall(r'\bdelayed_\w+\b',text))==set(aliases)
  addition='\n// NSSOC derived functional-only zero-delay aliases, 2026-11-15.\n'
  addition+='// No SDF, nonzero timing limits, timing conditions or pin overrides.\n'
  addition+='`ifdef NSSOC_CVC_ZERO_DELAY\n'
  addition+=''.join('assign '+pin+' = '+actual+';\n'for pin,actual in sorted(aliases.items()))
  addition+='`endif\n'
  changed.append({'module':name,'aliases':aliases})
  return text[:-len('endmodule')]+addition+'endmodule'
 derived=re.sub(r'module\s+(\w+)\s*\([^;]*;.*?endmodule',module,source,flags=re.S)
 assert len(changed)==16 and derived!=source
 return derived,changed
