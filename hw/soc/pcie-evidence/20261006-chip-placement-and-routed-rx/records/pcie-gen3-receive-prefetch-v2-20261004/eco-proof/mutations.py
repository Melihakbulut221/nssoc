# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy,hashlib,json,pathlib,time
import compare as m
root=m.ROOT;gold,gate=m.read('gold'),m.read('gate')
base=m.compare(gold,gate);assert base['mismatches']==[]
first=next(k for k,c in gate['cells'].items() if c['type']=='$_DFF_PP0_')
maxbit=max(b for c in gate['cells'].values() for bits in c['connections'].values() for b in bits if isinstance(b,int))
rows=[]
for kind in ['invert_D','invert_clock','invert_reset','invert_output','missing_state','unknown_function','unknown_output','undriven_reset','duplicate_driver','changed_port_census']:
 bad={**gate,'cells':gate['cells'].copy(),'ports':copy.deepcopy(gate['ports'])}
 if kind in ('invert_D','invert_clock','invert_reset','invert_output'):
  if kind=='invert_output':
   p=bad['ports']['data_o'];bit=p['bits'][0];p['bits'][0]=maxbit+1
  else:
   p={'invert_D':'D','invert_clock':'C','invert_reset':'R'}[kind]
   c=copy.deepcopy(bad['cells'][first]);bit=c['connections'][p][0];c['connections'][p]=[maxbit+1];bad['cells'][first]=c
  bad['cells']['peer_fault_inverter']={'type':'$_NOT_','parameters':{},'port_directions':{'A':'input','Y':'output'},'connections':{'A':[bit],'Y':[maxbit+1]}}
 elif kind=='missing_state':del bad['cells'][first]
 elif kind=='unknown_function':
  bad['cells'][first]=copy.deepcopy(bad['cells'][first]);bad['cells'][first]['type']='PEER_BLACKBOX'
 elif kind=='unknown_output':bad['ports']['data_o']['bits'][0]='x'
 elif kind=='undriven_reset':
  c=copy.deepcopy(bad['cells'][first]);c['connections']['R']=[maxbit+2];bad['cells'][first]=c
 elif kind=='duplicate_driver':bad['cells']['peer_duplicate']={'type':'$_NOT_','parameters':{},'port_directions':{'A':'input','Y':'output'},'connections':{'A':[bad['ports']['clk_i']['bits'][0]],'Y':bad['cells'][first]['connections']['Q']}}
 else:bad['ports']['payload_i']['bits'].pop()
 try:
  result=m.compare(gold,bad)
 except (AssertionError,KeyError) as error:
  assert not kind.startswith('invert'),(kind,error)
  rows.append(dict(kind=kind,status='REJECTED_MALFORMED_OR_UNSUPPORTED_GRAPH',error=repr(error)))
 else:
  assert result['mismatches'],kind
  assert len(result['mismatches'])==1,(kind,result['mismatches'])
  rows.append(dict(kind=kind,status='REJECTED_ACTUAL_BOOLEAN_COMPLEMENT',mismatches=result['mismatches'],reason='Direct inversion of the selected Boolean boundary differs for every input/state valuation.'))
record={'status':'PASS_TEN_MEANINGFUL_EQUIVALENCE_KERNEL_CONTROLS','positive':base,'controls':rows,'scope':'Four real Boolean boundary-inversion faults and six fail-closed graph/coverage faults, including the actual failed-physical undriven-reset class on exact native-expanded candidate. No altered source netlist written.'}
(root/'mutation-controls.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
