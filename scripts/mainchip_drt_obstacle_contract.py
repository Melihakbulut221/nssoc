#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Exact DBU and endpoint-obstacle contracts; a preroute observation is not a cause."""
import hashlib,json,re
from fractions import Fraction
import mainchip_drt_report_analysis as text
q=text.q
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False,
  routing_executed=False,physical_cause_proven=False,iteration10_mutable_routes_present=False)
INPUT_ODB=dict(bytes=212855093,sha256="15dff6b392f043891aff5508709ded3de825d6abc55cc7f7bf24bc7532134fbc")
def rectangle(value):
    q.require(type(value)in(list,tuple)and len(value)==4 and all(type(x)is int for x in value),"integer rectangle")
    q.require(value[0]<=value[2]and value[1]<=value[3],"ordered rectangle")
    return list(value)
def dbu_box(row,dbu):
    q.require(type(dbu)is int and dbu>0,"positive integral DBU")
    m=re.fullmatch(r"\tbbox = \((-?\d+\.\d+), (-?\d+\.\d+)\) - \((-?\d+\.\d+), (-?\d+\.\d+)\) on Layer ([A-Za-z][A-Za-z0-9_]*)",row["bbox_text"])
    q.require(m is not None and m[5]==row["layer"],"unchanged marker grammar/layer")
    values=[Fraction(m[i])*dbu for i in range(1,5)]
    q.require(all(x.denominator==1 for x in values),"marker lies exactly on native DBU grid")
    return rectangle([x.numerator for x in values])
def relation(a,b):
    a=rectangle(a);b=rectangle(b)
    x=min(a[2],b[2])-max(a[0],b[0]);y=min(a[3],b[3])-max(a[1],b[1])
    return dict(closed_intersection=x>=0 and y>=0,positive_area_intersection=x>0 and y>0,x_overlap_dbu=x,y_overlap_dbu=y)
def scope(raw,plan,mutation,analysis,dbu,expected_total,expected_selected):
    owners=text.ownership(plan,mutation);rows=text.parse_report(raw)
    q.require(analysis["status"]=="COMPLETE_TEXTUAL_DRT_MANIFEST_CLASSIFICATION","qualified textual analysis")
    q.require(all(analysis[k]is False for k in text.FLAGS),"textual analysis acceptance scope")
    q.require(analysis["iteration10"]==text.classify(rows,owners),"entire textual record/ownership equality")
    q.require(len(rows)==expected_total,"complete report census")
    selected=[];other=[]
    for row in rows:
        if row["kind"]=="Short"and row["layer"]=="Metal2":
            q.require(len(row["nets"])==2 and row["nets"][0]!=row["nets"][1],"two distinct Short endpoints")
            selected.append(dict(row,box=dbu_box(row,dbu)))
        else:other.append(row)
    q.require(len(selected)==expected_selected,"complete selected Metal2 Short census")
    return dict(markers=selected,other_markers=other,endpoint_names=sorted({n for r in selected for n in r["nets"]}),
      report_records=len(rows),selected_records=len(selected),other_records=len(other),dbu=dbu),owners
def witness(marker,shape,allow_cross_layer_pin=False):
    q.require(shape["owner"]in marker["nets"],"only exact marker endpoint")
    r=relation(marker["box"],shape["box"])
    if not r["closed_intersection"]:return None
    same=shape["layer"]==marker["layer"]
    if not same and not allow_cross_layer_pin:return None
    return dict(shape,relation=r,layer_relation="same_layer"if same else"xy_projection_only_different_layer",
      observation="candidate_endpoint_obstacle_evidence_not_root_cause")
def census(net_names,instance_names,added,attachments):
    q.require(len(net_names)==143820 and len(set(net_names))==143820,"complete native net census")
    q.require(len(instance_names)==154480 and len(set(instance_names))==154480,"complete actual diode candidate instance census")
    q.require(all(type(n)is str and n for n in net_names+instance_names),"native names")
    q.require(set(n for n in instance_names if n.startswith("NSSOC_BULK_NEW_"))==set(added)==set(attachments)
      and len(added)==1351 and len(set(added))==1351,"complete added diode census")
    q.require(set(attachments.values())<=set(net_names),"all added diode endpoints exist")
    return dict(net_count=len(net_names),instance_count=len(instance_names),added_count=len(added))
def source_pin(value):
    raw=q.encode(value)
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def source_gate(root=None):
    from pathlib import Path
    import mainchip_stale_wire_routing as inherited
    root=Path(root)if root is not None else Path(__file__).resolve().parents[1]
    prior=inherited.source_gate()
    m=q.decode((root/"scripts/mainchip-drt-obstacle-readback-source.json").read_bytes())
    q.require(m["schema"]=="mainchip-drt-obstacle-readback-source-v1"and m["native_routing_authorized"]is False,"read-only source scope")
    q.require(type(m["native_readonly_authorized"])is bool,"explicit native authority")
    q.require(m["inherited_files"]==prior["files"]and inherited.MANIFEST in m["files"],"complete unchanged inherited source closure")
    for n,p in m["files"].items():
        q.valid_name(n);q.filepin(p);q.require((root/n).is_file()and not(root/n).is_symlink()and q.pin(root/n)==p,"protected source "+n)
    return m
def native_authorization(root=None):
    import os
    m=source_gate(root)
    q.require(os.environ.get("GITHUB_ACTIONS")=="true","hosted native execution only")
    q.require(m["native_readonly_authorized"]is True and m["native_routing_authorized"]is False,"native read-only activation is disabled")
    return m
def context(env,checkout):
    q.require(env.get("GITHUB_ACTIONS")=="true"and env.get("GITHUB_REPOSITORY")=="Melihakbulut221/nssoc","actual hosted repository")
    q.require(env.get("GITHUB_EVENT_NAME")=="workflow_dispatch"and env.get("GITHUB_REF")=="refs/heads/codex/mainchip-drt-obstacle-readback","actual manual branch")
    q.require(re.fullmatch("[a-f0-9]{40}",env.get("GITHUB_SHA",""))is not None and checkout==env["GITHUB_SHA"],"exact checkout")
    q.require(env.get("GITHUB_RUN_ATTEMPT")=="1"and re.fullmatch("[1-9][0-9]*",env.get("GITHUB_RUN_ID",""))is not None,"original run")
    return dict(source=checkout,run=int(env["GITHUB_RUN_ID"]),attempt=1)
if __name__=="__main__":
    import os,subprocess
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    ctx=context(os.environ,subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip())
    source_gate(root);print(json.dumps(dict(status="PASS_OBSTACLE_SOURCE_BINDING_ONLY",**ctx,**FLAGS)))
