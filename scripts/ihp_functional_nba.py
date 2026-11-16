"""Experimental zero-time NBA output scheduling for DERIVED functional cells.
Not native foundry behavior, SDF, physical delay or production acceptance.
Original pin truth tables/UDPs retained; original library remains untouched.
"""
import re
from ihp_zero_delay_aliases import SOURCE_SHA,adapt as alias_adapt
def adapt(source):
 derived,changes=alias_adapt(source);scheduled={}
 def module(match):
  name=match.group(1);body=match.group(0)
  if not re.search(r'\bihp_dff\w*\s*\(',body):return body
  outputs=[x.strip()for line in re.findall(r'\boutput\s+([^;]+);',body)for x in line.split(',')]
  assert outputs and all(re.fullmatch(r'\w+',x)for x in outputs),name
  def declaration(m):
   return '`ifdef NSSOC_CVC_ZERO_DELAY\noutput reg '+m.group(1)+';\n`else\n'+m.group(0)+'\n`endif'
  body=re.sub(r'\boutput\s+([^;]+);',declaration,body)
  for out in outputs:
   pattern=r'\b(buf|not)\s*\(\s*'+re.escape(out)+r'\s*,([^;]+)\);'
   matches=list(re.finditer(pattern,body));assert len(matches)==1,(name,out)
   m=matches[0];temporary='nssoc_functional_nba_'+out
   replacement=('`ifdef NSSOC_CVC_ZERO_DELAY\nwire '+temporary+';\n'+m.group(1)+' ('+temporary+','+m.group(2)+');\n'
      +'// Defer only the derived sequential output to the NBA region.\n'
      +'always @('+temporary+') '+out+' <= '+temporary+';\n'
      +'`else\n'+m.group(0)+'\n`endif')
   body=body[:m.start()]+replacement+body[m.end():]
  scheduled[name]=outputs;return body
 derived=re.sub(r'module\s+(\w+)\s*\([^;]*;.*?endmodule',module,derived,flags=re.S)
 assert len(scheduled)>=4 and set(scheduled)<=set(c['module']for c in changes)
 for c in changes:c['functional_nba_outputs']=scheduled.get(c['module'],[])
 return derived,changes
