import pathlib,json,math
import klayout.db as db
P=pathlib.Path;root=P('normalization-controls');root.mkdir();rows=[]
for label,gate,bulk,length,expected in [('parallel','g','b','0.13u',1),('different_gate','g2','b','0.13u',2),('different_bulk','g','b2','0.13u',2),('different_length','g','b','0.2u',2)]:
 p=root/(label+'.cir');p.write_text('* independent MOS merge control\n.subckt TOP d g s b g2 b2\nM1 d g s b NMOS W=1u L=0.13u\nM2 d '+gate+' s '+bulk+' NMOS W=2u L='+length+'\n.ends TOP\n')
 nl=db.Netlist();nl.read(str(p),db.NetlistSpiceReader());c=nl.circuit_by_name('TOP');before=list(c.each_device());assert len(before)==2;total=sum(d.parameter('W') for d in before)
 nl.combine_devices();after=list(c.each_device());assert len(after)==expected
 assert math.isclose(sum(d.parameter('W') for d in after),total,rel_tol=1e-12)
 rows.append({'control':label,'device_count_before':2,'device_count_after':len(after),'width_sum_preserved':True})
P('out').mkdir(exist_ok=True);P('out/normalization-controls.json').write_text(json.dumps({'status':'PASS_MOS_MERGE_CONTROLS_ONLY','cases':rows,'manufacturing_approval':False},indent=2));print(rows)
