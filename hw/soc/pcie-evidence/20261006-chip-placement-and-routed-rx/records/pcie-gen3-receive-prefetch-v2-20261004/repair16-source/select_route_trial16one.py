# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json,hashlib,re
B=Path(__file__).resolve().parent;D=Path('/dev/shm/nssoc-rx-prefetch-v2-repair14a-drt-01');N=Path('/dev/shm/nssoc-rx-prefetch-v2-postroute-repair-16-one-repair-04')
def pin(p):
 with Path(p).open('rb')as f:return dict(bytes=Path(p).stat().st_size,sha256=hashlib.file_digest(f,'sha256').hexdigest())
a=(D/'routed.v').read_text();z=(N/'repaired.v').read_text();log=(N/'native.log').read_text()
def cell(text,k):
 m=re.search(r'\b(sg13g2_\w+)\s+'+re.escape(k)+r'\s*\((.*?)\);',text,re.S);assert m
 return {'type':m[1],'connections':dict(re.findall(r'\.(\w+)\((.*?)\)',m[2]))}
cs={k:{'baseline':cell(a,k),'candidate':cell(z,k)}for k in ['_25505_','_19647_','_19728_','place9595','_19796_','_24518_','_24520_','_24526_','_24548_','eco10_wire_312103','_24549_','_24550_','_24552_','_25594_','_13120_']}
for k in cs:assert cs[k]['baseline']['connections']==cs[k]['candidate']['connections']
assert [(k,v['baseline']['type'],v['candidate']['type'])for k,v in cs.items() if v['baseline']['type']!=v['candidate']['type']]==[('place9595','sg13g2_buf_2','sg13g2_buf_4'),('_19796_','sg13g2_nor2_1','sg13g2_nor2_2')]
iterations=[x for x in log.splitlines()if re.match(r'^\s*\d+\*?\s*\|',x)];assert len(iterations)==3
final=log.split('RX16ONE04_GRT_AFTER_BROAD_REPAIR_ESTIMATES_ONLY_slow_max\n')[1].split('RX16ONE04_GRT_AFTER_BROAD_REPAIR_ESTIMATES_ONLY_slow_min\n')[0]
setup=[x for x in final.split('Startpoint:')[1:]if 'recovery check'not in x];assert len(setup)==100 and all(x.lstrip().startswith('_25594_\n')for x in setup)
r={'status':'SELECTED_FOR_ONE_PROOF_GATED_ACTUAL_ROUTE_TRIAL_NOT_ACCEPTED','prior_screening_decision_retained':pin(B/'one04-rejection-review.json'),'candidate_result':pin(N/'result.json'),'baseline_netlist':pin(D/'routed.v'),'candidate_netlist':pin(N/'repaired.v'),'method':pin(__file__),'original_actual_critical_path_cells':cs,'actual_optimizer_iteration_rows':iterations,'baseline_actual_setup_ns':-.402478,'baseline_actual_hold_ns':.049182,'mixed_optimizer_reported_setup_ns':-.174,'mixed_endpoint_TNS_ns':-15.6,'original_endpoint_TNS_ns':-29.2,'unchanged_baseline_GRT_setup_ns':.030589,'candidate_GRT_setup_ns':-.040985,'candidate_GRT_hold_ns':.108700,'final_GRT_top100_launch':'_25594_','selection_reason':'Actual original worst-path weak NOR and preceding buffer materially strengthened; mixed-RC WNS/TNS improve. GRT is materially optimistic for baseline, so its adverse screening result does not prove routed regression. One constrained actual route/RC measurement justified after new canonical proof, ten actual faults and six native port cases. No margin sweep or timing-constraint change.','gates':['fresh native gate expansion with exact reused originalgold','1804-state/5443-function canonical proof','ten actual fault detections','six unchanged native port cases','independent route/RC source peer','zero router DRC and unchanged routed netlist','actual nominal RC all three cell corners; hold/setup/recovery/removal reported'],'scope':'Trial selection only. No equivalence/physical/production acceptance yet; previous rejection evidence remains immutable.'}
(B/'route-trial-selection16one.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
