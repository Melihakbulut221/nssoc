# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Synthetic event regression only. No production oracle or acceptance edits."""
from pathlib import Path
from fractions import Fraction as Q
import ast,copy,hashlib,json
B=Path(__file__).resolve().parent;SOURCE=Path.cwd()/'scripts/characterize_pcie_pll_loop_v1.py'
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
tree=ast.parse(SOURCE.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='measure_chain')
node=next(n for n in ast.walk(fn)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='counts'for t in n.targets)and 'osc'in ast.unparse(n.value))
assert ast.unparse(node.value)=='[sum((a <= e < b for e in osc)) for a, b in zip(slow[:-1], slow[1:])]'
code=compile(ast.fix_missing_locations(ast.Expression(copy.deepcopy(node.value))),str(SOURCE),'eval')
def buckets(osc,slow):return eval(code,{'__builtins__':{'sum':sum,'zip':zip}},dict(osc=osc,slow=slow))
osc=[Q(k*1000)for k in range(220)];kvals=list(range(51))
# All51 output events are defined by distinct exact global input ordinals4*k.
# Smooth relative phase moves only14/1000 of an input period across the run.
negative=[osc[4*k]+Q(7)-Q(14*k,50)for k in kvals]
positive=[osc[4*k]-Q(7)+Q(14*k,50)for k in kvals]
def fixed_global_check(events,source=osc):
 # The synthetic fixture supplies the true fixed global anchor0 and a declared
 # 0.1UI bound. This is not a tolerance proposed for real measured captures.
 if len(events)!=51 or any(b<=a for a,b in zip(events[:-1],events[1:])):return False,'event_census_or_order'
 residual=[events[k]-source[4*k]for k in kvals]
 if any(abs(x)>Q(100)for x in residual):return False,'fixed_global_phase_bound'
 return True,'all51_exact_ordinal_pairs_bounded'
for seq in [negative,positive]:assert fixed_global_check(seq)[0]
a,b=buckets(osc,negative),buckets(osc,positive);assert set(a)=={3,4}and a.count(3)==1;assert set(b)=={4,5}and b.count(5)==1
bad=[]
faults={
 'missing_output':negative[:20]+negative[21:],
 'extra_output':negative[:20]+[(negative[19]+negative[20])/2]+negative[20:],
 'glitch_doublet':negative[:20]+[negative[20]-Q(1),negative[20]+Q(1)]+negative[21:],
 'ratio3':[osc[3*k]+Q(7)-Q(14*k,50)for k in kvals],
 'ratio5':[Q(5*k*1000)+Q(7)-Q(14*k,50)for k in kvals],
 'stall_with_later_catchup':[x+(Q(1000)if 20<=k<23 else 0)for k,x in enumerate(negative)],
}
for name,seq in faults.items():
 ok,why=fixed_global_check(seq);assert not ok,name
 bad.append(dict(name=name,rejected=True,diagnostic=why,output_events=len(seq),original_bucket_counts=buckets(osc,seq)))
# A nearest-edge estimator also changes its chosen ordinal at halfUI.
half_ui=[osc[4*k]+Q(493)+Q(14*k,50)for k in kvals]
nearest=[min(range(len(osc)),key=lambda j:abs(osc[j]-v))for v in half_ui]
adv=[b-a for a,b in zip(nearest[:-1],nearest[1:])];assert 5 in adv and set(adv)<={4,5};assert not fixed_global_check(half_ui)[0]
record=dict(status='PASS_SYNTHETIC_BUCKET_PHASE_SENSITIVITY_REGRESSION_NO_ORACLE_ADOPTION',findings=[],method=pin(Path(__file__)),production_source=pin(SOURCE),exact_production_count_expression=ast.unparse(node.value),production_count_AST_sha256=hashlib.sha256(ast.dump(node.value,include_attributes=False).encode()).hexdigest(),time_units='Arbitrary exact rational units; inputUI1000; no simulator or physical waveform implied.',perfect_div4_falling_phase=dict(events=51,exact_input_ordinals=[4*k for k in kvals],phase_range=[7,-7],bucket_counts=a,bad_indices=[i for i,v in enumerate(a)if v!=4],fixed_global_synthetic_bound_pass=True),perfect_div4_rising_phase=dict(events=51,phase_range=[-7,7],bucket_counts=b,bad_indices=[i for i,v in enumerate(b)if v!=4],fixed_global_synthetic_bound_pass=True),six_actual_event_mutations=bad,nearest_ordinal_halfUI_counterexample=dict(phase_range=[493,507],nearest_ordinals=nearest,advances=adv,scope='Nearest-edge selection has its own halfUI boundary. Do not substitute nearest counts for an independently anchored global correspondence.'),scope='Executed the exact inherited production AST expression on synthetic event fixtures. Both perfect divisions produce a3or5 half-open artifact solelyfrom smoothphase crossingzero. Six explicit event mutations reject under separately declared synthetic anchor/bound; this doesnot qualify any physical oracle. Real tolerance must be predeclared after numerical convergence and independently justified. All existing production code/criteria/results remain unchanged.')
(B/'result01.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
