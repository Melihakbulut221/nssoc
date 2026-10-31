#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pinned native view adapter; disabled until a separately reviewed activation.

No routing, repair, resizing, clock edits or estimated parasitics are present.
Independent fresh OpenROAD processes reload full and timing Verilog.
"""
import json,os,re,subprocess
from pathlib import Path
import mainchip_routed_view_admission as a

OUT=Path("/work/routed-views")
SOURCE=Path("/work/routed-view-inputs/final-measured.odb")
ENGINE=Path("/work/engine/openroad")
MODES=("candidate","full","timing")
# Verified against OpenROAD dcf36133 / OpenSTA 857316ff sources archived by this proposal.
CAPTURE=r"""
proc rv_hex {value} {return [binary encode hex [encoding convertto utf-8 $value]]}
proc rv_row {stream args} {puts $stream [join $args "\t"]}
set block [ord::get_db_block]
if {$block eq "NULL" || [$block getName] ne "soc_top"} {error "exact soc_top block required"}
if {[llength [$block getChildren]] != 0} {error "hierarchical children are not admitted"}
rv_row $rv BEGIN [rv_hex [$block getName]] [$block getDbUnitsPerMicron]
foreach net [$block getNets] {
  rv_row $rv N [rv_hex [$net getName]] [$net getSigType] [expr {[$net getWire] ne "NULL"}]
}
set sta_instances [dict create]
foreach si [sta::network_leaf_instances] {
  set di [sta::sta_to_db_inst $si]
  if {$di eq "NULL"} {error "STA instance has no exact DB instance"}
  set key [$di getName]
  if {[dict exists $sta_instances $key]} {error "duplicate linked STA instance"}
  dict set sta_instances $key $si
}
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  set iname [$inst getName]
  if {![dict exists $sta_instances $iname]} {error "DB instance omitted from STA"}
  set si [dict get $sta_instances $iname]
  rv_row $rv I [rv_hex $iname] [rv_hex [[$master getLib] getName]] [rv_hex [$master getName]] [$master getType]
  foreach it [$inst getITerms] {
    set mt [$it getMTerm]
    set pname [$mt getName]
    set net [$it getNet]
    set nname ""
    if {$net ne "NULL"} {set nname [$net getName]}
    set sig [$mt getSigType]
    rv_row $rv T [rv_hex $iname] [rv_hex $pname] [rv_hex $nname] $sig [$mt getIoType]
    if {$sig ni {POWER GROUND}} {
      set sp [$si find_pin $pname]
      if {$sp eq "NULL"} {error "linked signal terminal missing"}
      set lp [$sp liberty_port]
      if {$lp eq "NULL"} {error "signal terminal has no Liberty port"}
      set lc [$si liberty_cell]
      if {$lc eq "NULL"} {error "signal terminal has no Liberty cell"}
      if {[$lc find_liberty_port $pname] ne $lp || [$sp port_name] ne $pname} {error "exact Liberty port identity mismatch"}
      set corner [sta::cmd_corner]
      rv_row $rv C [rv_hex $iname] [rv_hex $pname] [rv_hex $nname] [rv_hex [sta::get_full_name $sp]] [$sp is_driver] [rv_hex [$lc name]] [rv_hex [$sp port_name]] [$lp capacitance $corner min] [$lp capacitance $corner max]
    }
  }
}
foreach port [$block getBTerms] {
  set pname [$port getName]
  set net [$port getNet]
  set nname ""
  if {$net ne "NULL"} {set nname [$net getName]}
  set sig [$port getSigType]
  rv_row $rv P [rv_hex $pname] [rv_hex $nname] $sig [$port getIoType]
  if {$sig ni {POWER GROUND}} {
    set sp [sta::find_pin $pname]
    if {$sp eq "NULL" || ![$sp is_top_level_port]} {error "exact linked top port missing"}
    rv_row $rv B [rv_hex $pname] [rv_hex $nname] [rv_hex [sta::get_full_name $sp]] [$sp is_driver]
  }
}
rv_row $rv END [llength [$block getInsts]] [llength [$block getNets]] [llength [$block getBTerms]]
close $rv
"""

def q(path):
    text=str(path)
    a.require(re.fullmatch(r"/work/[A-Za-z0-9_./-]+",text)is not None and ".."not in Path(text).parts,"owned Tcl path")
    return "{"+text+"}"

def validate_request(r):
    a.exact(set(r),{"envelope","source","lefs","liberties"},"request fields")
    a.validate_envelope(r["envelope"])
    def descriptor(d):
        a.exact(set(d),{"path","pin"},"input descriptor")
        q(d["path"]);a.require(str(d["path"]).startswith("/work/routed-view-inputs/"),"input root")
        a.filepin(d["pin"])
    descriptor(r["source"]);a.exact(r["source"]["path"],str(SOURCE),"exact admitted source path")
    a.exact(r["source"]["pin"],r["envelope"]["candidate"],"source envelope pin")
    a.exact(set(r["liberties"]),set(a.CORNERS),"original three PVT libraries")
    a.require(type(r["lefs"])is list and r["lefs"],"real LEF inputs")
    rows=[r["source"],*r["lefs"]]
    for corner in a.CORNERS:
        a.require(type(r["liberties"][corner])is list and r["liberties"][corner],"real Liberty inputs")
        rows.extend(r["liberties"][corner])
    seen={}
    for d in rows:
        descriptor(d)
        if d["path"]in seen:a.exact(seen[d["path"]],d["pin"],"same file cannot have conflicting pins")
        seen[d["path"]]=d["pin"]
    a.require(len({d["path"]for d in r["lefs"]})==len(r["lefs"]),"no duplicate LEF reads")
    for corner in a.CORNERS:a.require(len({d["path"]for d in r["liberties"][corner]})==len(r["liberties"][corner]),"no duplicate Liberty reads")
    return seen

def render(r,mode,corner):
    validate_request(r);a.require(mode in MODES and corner in a.CORNERS,"native phase")
    lines=["# Exact read-only native view export/reload. No design repair.","set_thread_count 1"]
    lines.extend("read_liberty "+q(d["path"])for d in r["liberties"][corner])
    if mode=="candidate":
        lines.append("read_db "+q(SOURCE))
        if corner==a.CORNERS[0]:
            lines.extend(["write_def "+q(OUT/"completed.def"),
              "write_verilog -include_pwr_gnd "+q(OUT/"full.v"),
              "write_verilog "+q(OUT/"timing.v")])
    else:
        lines.extend("read_lef "+q(d["path"])for d in r["lefs"])
        lines.extend(["read_verilog "+q(OUT/(mode+".v")),"link_design soc_top"])
    lines.append("set rv [open "+q(OUT/(mode+"-"+corner+".records"))+" {WRONLY CREAT EXCL}]")
    return "\n".join(lines)+"\n"+CAPTURE+"\nexit\n"

def parse_records(raw):
    a.require(type(raw)is bytes,"native inventory bytes")
    v=dict(block=None,dbu=None,instances={},nets={},ports={});loads=dict(pins=[],ports=[]);begun=ended=False
    def unhex(s):
        a.require(len(s)%2==0 and re.fullmatch("[0-9a-f]*",s)is not None,"native hex framing")
        return bytes.fromhex(s).decode("utf-8")
    def bit(s):a.require(s in("0","1"),"native bool");return s=="1"
    def integer(s):a.require(re.fullmatch(r"0|[1-9]\d*",s)is not None,"native integer");return int(s)
    for line in raw.decode("ascii").splitlines():
        row=line.split("\t");kind=row[0]
        a.require(not ended,"data after inventory END")
        if kind=="BEGIN":
            a.require(not begun and len(row)==3,"unique native BEGIN");begun=True
            v["block"]=unhex(row[1]);v["dbu"]=integer(row[2]);continue
        a.require(begun,"native BEGIN required")
        if kind=="N":
            a.require(len(row)==4,"net record");n=unhex(row[1]);a.require(n not in v["nets"],"duplicate native net")
            v["nets"][n]=dict(sigtype=row[2],wire=bit(row[3]))
        elif kind=="I":
            a.require(len(row)==5,"instance record");n=unhex(row[1]);a.require(n not in v["instances"],"duplicate native instance")
            v["instances"][n]=dict(master=[unhex(row[2]),unhex(row[3])],master_type=row[4],pins={})
        elif kind=="T":
            a.require(len(row)==6,"pin record");i,p,n=map(unhex,row[1:4])
            a.require(i in v["instances"]and p not in v["instances"][i]["pins"],"unique owned native pin")
            v["instances"][i]["pins"][p]=dict(net=n or None,sigtype=row[4],io=row[5])
        elif kind=="P":
            a.require(len(row)==5,"port record");p,n=map(unhex,row[1:3]);a.require(p not in v["ports"],"duplicate native port")
            v["ports"][p]=dict(net=n or None,sigtype=row[3],io=row[4])
        elif kind=="C":
            a.require(len(row)==10,"native Liberty record");i,p,n,path,lc,lp=[unhex(row[k])for k in(1,2,3,4,6,7)]
            loads["pins"].append(dict(instance=i,pin=p,net=n or None,path=path,driver=bit(row[5]),liberty_cell=lc,liberty_pin=lp,min=float(row[8]),max=float(row[9])))
        elif kind=="B":
            a.require(len(row)==5,"native STA port");p,n,path=map(unhex,row[1:4])
            loads["ports"].append(dict(port=p,net=n or None,path=path,driver=bit(row[4])))
        elif kind=="END":
            a.require(len(row)==4,"native END")
            a.exact(list(map(integer,row[1:])),[len(v["instances"]),len(v["nets"]),len(v["ports"])],"native actual enumeration")
            ended=True
        else:raise ValueError("unknown native record")
    a.require(begun and ended,"complete native inventory")
    a.validate_inventory(v)
    loads["pins"].sort(key=lambda r:(r["instance"],r["pin"]))
    loads["ports"].sort(key=lambda r:r["port"])
    return v,loads

def collect(original,added,records):
    a.require(len(original["instances"])==154480 and len(original["nets"])==143820,"enumerated admitted final physical census")
    a.exact(set(records),{(m,c)for m in MODES for c in a.CORNERS},"all nine independent native captures")
    views={};models={m:{}for m in MODES}
    for (mode,corner),raw in records.items():
        inventory,loads=parse_records(raw);models[mode][corner]=loads
        if mode in views:a.exact(inventory,views[mode],"same physical inventory across PVT input models")
        else:views[mode]=inventory
    a.exact(views["candidate"],original,"native capture equals admitted final snapshot")
    proof=a.compare_views(original,views["full"],views["timing"],added)
    for mode in MODES:a.validate_loads(views[mode],models[mode],added)
    for mode in("full","timing"):a.exact(models[mode],models["candidate"],"reloaded actual signal Liberty loads and STA paths")
    return dict(topology=proof,loads=models["candidate"],inventory=original,record_pins={m+"/"+c:a.pin_bytes(raw)for(m,c),raw in records.items()},**a.FLAGS)

def execute(request,original,added,runner):
    a.authorize_native() # currently always refuses BEFORE mkdir, reads, or runner
    inputs=validate_request(request)
    a.require(a.pin(ENGINE)["sha256"]==a.ENGINE_SHA,"exact qualified engine ELF")
    def check_inputs():
        for path,expected in inputs.items():a.exact(a.pin(Path(path)),expected,"unchanged actual model/candidate bytes")
    check_inputs();OUT.mkdir(exist_ok=False)
    records={};commands=[]
    try:
        for mode in MODES:
            for corner in a.CORNERS:
                check_inputs();script=OUT/(mode+"-"+corner+".tcl")
                script.write_text(render(request,mode,corner))
                argv=[str(ENGINE),"-no_init","-exit",str(script)]
                # Caller supplies the existing exit-checked cloud supervisor.
                record=runner(argv,1200,OUT/(mode+"-"+corner+".stdout"),OUT/(mode+"-"+corner+".stderr"))
                a.exact(record["argv"],argv,"actual native command")
                a.require(type(record["returncode"])is int and record["returncode"]==0,"native process succeeded")
                commands.append(record);check_inputs()
                records[(mode,corner)]=(OUT/(mode+"-"+corner+".records")).read_bytes()
        proof=collect(original,added,records)
        proof["outputs"]={n:a.pin(OUT/n)for n in("completed.def","full.v","timing.v")}
        proof["commands"]=commands
        proof["native_executed"]=True # only after all nine actual runner commands succeed
        (OUT/"result.json").write_bytes(a.encode(proof));return proof
    finally:
        check_inputs()
        # Full command/output preservation belongs to the future cloud supervisor.
        (OUT/"available-output-pins.json").write_bytes(a.encode({p.name:a.pin(p)for p in OUT.iterdir()if p.is_file()}))

def main():
    a.authorize_native()
if __name__=="__main__":main()
