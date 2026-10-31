#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Explicit instance-specific tail drain shunts; no transistor or acceptance changes."""
TOP="nssoc_cdr_pd500_resistor_v59"
TARGETS={3:(28,"$131"),4:(28,"$131"),5:(28,"$131"),6:(28,"$131"),
         32:(124,"$680"),33:(124,"$680"),34:(124,"$680"),35:(124,"$680")}
LOCAL_RAIL=(750,0,910,36000)
M1_BOX=(670,0,990,36000)
M2_BOX=(330,200,1330,35800)
M2_WIDTHS=(1000,600,300)
CUT_SIZE=190
CUT_PITCH=500
CUT_CENTERS=tuple((830,y)for y in range(500,35501,CUT_PITCH))
CLEARANCE={8:220,10:240,19:220}
LAYERS=((8,0),(10,0),(19,0))
FLAGS=dict(physical_acceptance=False,electrical_acceptance=False,full_phy_accepted=False,
 timing_accepted=False,qualified_pex=False,new_simulation=False)
def require(value,message):
    if not value:raise AssertionError(message)
def open_spans(lo,hi,blocked,minimum=1000):
    """Complement conservative obstacle projections; no native geometry is inferred."""
    require(all(type(v)is int and v%5==0 for v in(lo,hi,minimum))and lo<hi and minimum>=1000,"ordered grid-aligned segment bounds")
    clipped=[]
    for row in blocked:
        require(len(row)==2 and all(type(v)is int and v%5==0 for v in row)and row[0]<=row[1],"ordered grid-aligned blocker")
        a,b=max(lo,row[0]),min(hi,row[1])
        if a<b:clipped.append((a,b))
    merged=[]
    for a,b in sorted(clipped):
        if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
        else:merged.append((a,b))
    result=[];start=lo
    for a,b in merged:
        if a-start>=minimum:result.append((start,a))
        start=max(start,b)
    if hi-start>=minimum:result.append((start,hi))
    return result

def local_plan():
    require(len(TARGETS)==8 and len(CUT_CENTERS)==71,"eight drains and71 possible cuts per drain")
    require(all(v%5==0 for box in(LOCAL_RAIL,M1_BOX,M2_BOX)for v in box),"5nm metal grid")
    require(all(type(w)is int and w%10==0 and 290<=w<=1000 for w in M2_WIDTHS),"bounded drain-centered M2 widths")
    cuts=[(x-95,y-95,x+95,y+95)for x,y in CUT_CENTERS]
    require(all(all(v%5==0 for v in box)and box[2]-box[0]==box[3]-box[1]==190 for box in cuts),"exact V1 cut")
    require(all(M1_BOX[0]+10<=a and M1_BOX[1]+10<=b and c<=M1_BOX[2]-10 and d<=M1_BOX[3]-10 for a,b,c,d in cuts),"M1 enclosure")
    require(all(M2_BOX[0]+50<=a and M2_BOX[1]+50<=b and c<=M2_BOX[2]-50 and d<=M2_BOX[3]-50 for a,b,c,d in cuts),"M2 conservative enclosure")
    return dict(rail=list(LOCAL_RAIL),metal1=list(M1_BOX),metal2=list(M2_BOX),via1=[list(x)for x in cuts],
      possible_cuts=71,minimum_new_cuts=32,metal2_width_candidates_dbu=list(M2_WIDTHS),
      metal2_min_segment_length_dbu=1000,minimum_new_cuts_per_segment=2,
      selection="maximum bridged drain length, then widest M2, then cut count",
      via_filter="Use fully enclosed cut positions in conservatively spaced M2 segments; skip near existing Via1; discard segments with fewer than two new cuts; preserve every decision.",
      clearance_dbu={str(k):v for k,v in CLEARANCE.items()},all_original_geometry_retained=True,**FLAGS)
def validate_target(device,anchor,native_model,native_cluster,native_name):
    require(type(device)is int and device in TARGETS,"exact target native device")
    require(native_model=="sg13_lv_nmos","actual target MOS model")
    require((native_cluster,native_name)==TARGETS[device],"actual native target net identity")
    require(anchor["label"]=="T%03d_D"%device and anchor["metal"]==8,"actual drain M1 anchor")
    require(anchor["native_cluster"]==native_cluster,"anchor/native owner agreement")
    require(anchor["detail"]["terminal"]=="D","actual drain terminal")
    point=anchor["point_dbu"]
    require(len(point)==2 and all(type(v)is int for v in point),"integer native drain point")
    return True
def input_names(config,full):
    require(config["schema"]=="cdr-current-eight-drain-straps-inputs-v1","current input schema")
    members=config["members"]
    require(type(members)is dict and len(members)==42,"all original36 and6 current physical inputs")
    require(set(members)<=set(full),"all members in complete actual original archive")
    for name,pin in members.items():
        require(isinstance(name,str)and not name.startswith("/")and ".."not in name.split("/")and "\\"not in name,"relative input path")
        require(set(pin)=={"bytes","sha256"}and type(pin["bytes"])is int and pin["bytes"]>0,"input pin")
        require(full[name]==pin["sha256"],"exact current archive fingerprint")
    require(config["producer_run"]==41017290646 and config["original_full_members"]==2797,"actual loaded producer")
    require(config["current_geometry"]["gds_sha256"]=="34f06505f3ff2fdb06257d6202931aa12d2d0176d482a2a7916561eeb9646034","current two-M1 GDS")
    require(config["current_geometry"]["lvs_sha256"]=="db740e4439e43e67bb9ddce5e69d784e1adb1b18b07cac893fe0db3128a1ec43","current full LVS")
    require(config["plan"]==local_plan(),"exact new shunt plan")
    return sorted(members)
