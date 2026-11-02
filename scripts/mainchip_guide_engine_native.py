"""Full actual-chip equality, native write/reload, DRT and antenna with new ELF."""
import gc,json,os,sys
from pathlib import Path
sys.path.insert(0,"/work/tail-source/scripts")
import odb
import mainchip_bulk_postdrt_antenna_native as native
from mainchip_guide_engine_acquisition import fp,need
n,p=native.n,native.p
ROOT=Path("/work/guide-reference");WORK=Path("/work/out/work/bulk-postdrt-antenna");DATA=Path("/work/out/bulk-postdrt-antenna")
SOURCE="work/bulk-postdrt-antenna/narrow47-restored.odb"
SNAPSHOT="bulk-postdrt-antenna/narrow47-restored-observed.json"
DEF="work/bulk-postdrt-antenna/narrow47-restored-observed.def"
def read(path):return json.loads(path.read_bytes())
def save(name,value):native.save(DATA/name,value)
def snap(path,stem,proof):
 reference=read(ROOT/SNAPSHOT);protected=reference["protected"]
 need(len(reference["instances"])==154480 and len(reference["nets"])==143820 and len(protected)==1691,"actual full reference census")
 del reference;gc.collect()
 value=native.snapshot(path,WORK/(stem+".def"),protected)
 need(len(value["instances"])==154480 and len(value["nets"])==143820 and len(value["protected"])==1691,"actual full new-engine census")
 save(stem+".json",value);del value;gc.collect()
 observed=fp(DATA/(stem+".json"));exported=fp(WORK/(stem+".def"))
 need(observed==proof[SNAPSHOT],"entire native snapshot equals original engine")
 need(exported==proof[DEF],"entire DEF equals original engine")
 return dict(snapshot=observed,DEF=exported,instances=154480,nets=143820,protected_clock_records=1691)
def roundtrip(proof):
 before=snap(ROOT/SOURCE,"guide-engine-before",proof)
 db,block=n.load(ROOT/SOURCE)
 try:
  need(not list(block.getChildren()),"no hidden child blocks")
  odb.write_db(db,str(WORK/"narrow47-restored.odb"))
 finally:odb.dbDatabase.destroy(db)
 after=snap(WORK/"narrow47-restored.odb","guide-engine-after",proof)
 need(before==after,"whole-chip load/write/reload equality")
 text=native.check_tcl(WORK/"narrow47-restored.odb","final",WORK)
 need(text.encode()==(ROOT/"work/bulk-postdrt-antenna/final-check.tcl").read_bytes(),"unchanged full checker Tcl")
 (WORK/"final-check.tcl").write_text(text)
 save("guide-engine-roundtrip.json",dict(status="PASS_ACTUAL_CHIP_NEW_ENGINE_ROUNDTRIP",before=before,after=after,
  candidate=fp(ROOT/SOURCE),rewritten=fp(WORK/"narrow47-restored.odb"),current_route_calls=0,**p.FLAGS))
def measure(proof):
 antenna,drc=native.collect_checks("final",WORK,DATA)
 previous=read(ROOT/"bulk-postdrt-antenna/narrow47-result.json")
 observed=snap(WORK/"final-measured.odb","guide-engine-measured",proof)
 save("guide-engine-measurement.json",dict(antenna=antenna,drc=drc,reference_antenna=previous["antenna"],reference_drc=previous["drc"],**p.FLAGS))
 need(antenna==previous["antenna"],"complete antenna results equal original engine")
 need(drc==previous["drc"],"complete DRT measurement equals original engine")
 for name in("final-antenna-nets.json","final-antenna-summary.json","final-antenna-violations.json"):
  need(read(DATA/name)==read(ROOT/"bulk-postdrt-antenna"/name),"entire antenna report "+name)
 need(antenna["design_is_routed"]==1,"unchanged routed marker, not signoff")
 save("guide-engine-result.json",dict(status="PASS_ACTUAL_CHIP_ENGINE_ROUNDTRIP_AND_FULL_CHECKS",
  snapshot=observed,roundtrip=read(DATA/"guide-engine-roundtrip.json"),antenna=antenna,drc=drc,
  native_chip_roundtrip_qualified=True,native_routing_qualified=False,routing_memory_reduction_measured=False,
  current_route_calls=0,current_repair_calls=0,routing_complete=False,**p.FLAGS))
def main():
 need(not any(k in os.environ for k in("GH_TOKEN","GITHUB_TOKEN")),"credential-free native")
 p.source_guard()
 proof=read(Path("/work/guide-reference-pins.json"))
 for name,pin in proof.items():need(fp(ROOT/name)==pin,"reference input "+name)
 phase=os.environ["NSSOC_GUIDE_ENGINE_PHASE"]
 need(phase in("roundtrip","measure"),"declared phase")
 {"roundtrip":roundtrip,"measure":measure}[phase](proof)
 for name,pin in proof.items():need(fp(ROOT/name)==pin,"reference unchanged "+name)
if __name__=="__main__":main()
