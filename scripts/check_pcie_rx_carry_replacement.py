#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove the exact stateless RX carry-select replacement compositionally.

Bind the actual 12-bit operands and destination, project the remaining module
back to the exact reference, and prove every binary operand pair in native SAT.
Source-change guards and two declared carry faults must be rejected. This does
not certify the protocol, physical timing, four-state simulation or serial PHY.
"""
from pathlib import Path
import argparse
import json,hashlib,subprocess,resource
parser=argparse.ArgumentParser(description=__doc__)
for name in ('reference','candidate','yosys','out'):
    parser.add_argument('--'+name,type=Path,required=True)
args=parser.parse_args()
S=args.reference.resolve();C=args.candidate.resolve();Y=args.yosys.resolve();D=args.out.resolve();D.mkdir(parents=True,exist_ok=False)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
reference=S.read_text();candidate=C.read_text();start='    // Parallel nibble sums with late carry selection after the queue mux.\n';end='    wire select_dllp=';base='    wire [11:0] credit_base=data_limit_o[(head_slot/SLOTS_PER_CLASS)*12 +: 12];\n';units='    wire [11:0] credit_units=units[head_slot];\n';expression='data_limit_o[(head_slot/SLOTS_PER_CLASS)*12 +: 12]+units[head_slot]'
def project(text):
 assert text.count(start)==text.count(end)==1
 a=text.index(start);b=text.index(end,a);block=text[a:b];assert block.count(base)==block.count(units)==1
 assert block.count('wire [11:0] credit_return_sum=')==1
 outer=text[:a]+text[b:];assert outer.count('credit_return_sum')==1
 assert 'data_limit_o[(head_slot/SLOTS_PER_CLASS)*12 +: 12]<=\n                        credit_return_sum;'in outer
 restored=outer.replace('credit_return_sum',expression);assert restored==reference
 return block,restored
block,restored=project(candidate);(D/'projected-reference.v').write_text(restored);(D/'actual-combinational-block.vh').write_text(block)
guards=[]
for name,bad in [('unrelated_state_change',candidate.replace('released_o<=1;','released_o<=0;')),('changed_operand',candidate.replace(units,units.replace('units[head_slot]','units[head_slot]+12\'d1')))]:
 assert bad!=candidate
 try:project(bad)
 except AssertionError:guards.append(dict(name=name,rejected_before_solver=True))
 else:raise AssertionError('Source projection accepted unrelated behavior change')
pins={str(p):sha(p)for p in [Path(__file__),S,C,Y,D/'projected-reference.v',D/'actual-combinational-block.vh']};rows=[]
def limits():resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
body=block.replace(base,'').replace(units,'')
for name,old,new in [('baseline',None,None),('lost_high_carry','credit_carry=credit_low[4] ? credit_mid1[4] : credit_mid0[4];','credit_carry=credit_mid0[4];'),('lost_middle_carry','credit_low[4] ? credit_mid1[3:0] : credit_mid0[3:0]','credit_mid0[3:0]')]:
 mutated=body
 if old:assert mutated.count(old)==1;mutated=mutated.replace(old,new)
 source=D/(name+'.v');source.write_text('`default_nettype none\nmodule check(input wire [11:0] credit_base,credit_units,output wire bad);\n'+mutated+'\nwire [11:0] expected=credit_base+credit_units;\nassign bad=credit_return_sum!=expected;\nendmodule\n`default_nettype wire\n');recipe=D/(name+'.ys');recipe.write_text(f'read_verilog -formal -sv {source}\nhierarchy -check -top check\nproc\nopt\ncheck -assert\nselect -assert-none t:$dff* t:$adff* t:$dlatch*\nsat -verify -prove bad 0 -show-inputs -show-outputs\n');log=D/(name+'.log');pins.update({str(p):sha(p)for p in [source,recipe]})
 with log.open('x')as f:p=subprocess.run([Y,'-s',recipe],stdout=f,stderr=subprocess.STDOUT,preexec_fn=limits)
 text=log.read_text();assert 'implicitly declared'not in text and'syntax error'not in text.lower();passed=p.returncode==0 and'SUCCESS!'in text;counterexample=p.returncode!=0 and'proof did fail'in text;assert passed if name=='baseline'else counterexample
 rows.append(dict(name=name,passed=passed,counterexample=counterexample,returncode=p.returncode,log_sha256=sha(log)))
assert all(sha(p)==h for p,h in pins.items());result=dict(status='PASS_EXACT_SOURCE_IDENTITY_AND_EXHAUSTIVE_12BIT_REPLACEMENT',inputs=pins,inputs_unchanged=True,cases=rows,source_guards=guards,operand_bits=24,covered_binary_operand_combinations=2**24,assumptions=[],projection_identical=True,additional_sequential_state=False,scope='Compositional equivalence of this exact stateless RTL replacement: all12bitoperandpairs prove newwire equals original12bitaddition, bothoperandbindings and sole12bitdestinationverified; removingonlythecombblock/restoringexpression yieldsfullfrozenmodule byteforbyte including everyport,stateupdate,reset andparameter. Thus the replacement is equivalent wherever original RTL has defined binary behavior, independently of queue size. No claim native fullmodule largestcase equiv_induct passed (it exhausted memory); no serialPHY/protocolqualification or timingclaim. Earlier add-proof12 wrong_mid used undeclaredmid_zero; these new two mutations are declared actualcarrypaths and check-assert/default_nettype-none reject unresolvedsignals.');(D/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
