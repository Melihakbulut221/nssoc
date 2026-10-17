from pathlib import Path
import hashlib,json,ast,difflib
R=Path.cwd();B=Path(__file__).resolve().parent;O=B.parents[1]/'pcie-divider-v9-bias-v1-20261006/native-peer-pll'
def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
rows=[]
for name in ['read_raw_databases.py','run_database_reader.py','review_saved_native.py']:
 old=(O/name).read_text();s=old
 edits=[('v9-bias-v1','v10-tail-v1'),('v9_bias_v1','v10_tail_v1'),('V9_BIAS_V1','V10_TAIL_V1'),('BIAS8_V1','TAIL115_V1'),('Bias8V1','Tail115V1')]
 if name=='review_saved_native.py':
  edits += [
   ('==327','==340'),('full_member_readback=327','full_member_readback=340'),('with327 archive','with340 archive'),
   ('PASS_ACTUAL_BIAS8_TWO_RPPD_DELTA_CAP24_POWER_AND_EIGHT_GEOMETRY_CONTROLS','PASS_ACTUAL_TAIL115_ONE_RPPD_DELTA_BIAS8_CAP24_AND_TEN_GEOMETRY_CONTROLS'),
   ("len(geometry['controls'])==8","len(geometry['controls'])==10"),
   ("'restore_shorter_actual_pulldown']","'restore_shorter_actual_pulldown','remove_actual_reference_resistor_body','restore_old_reference_length']"),
   ("assert geometry['changed_pulldown_length_um']=={'DIV__XDN':[7,8],'DIV__XDP':[7,8]} and geometry['unchanged_intrinsics']==89", "assert geometry['changed_reference_length_um']=={'DIV__XSECOND__XBIAS':[12.7,11.5]} and geometry['unchanged_intrinsics']==90\nassert geometry['retained_bias8_pulldown_names']==['DIV__XDN','DIV__XDP']\nfor name,length in [('DIV__XSECOND__XBIAS',11.5),('DIV__XFIRST__XCORE__XBIAS',12.7)]:\n row=next(x for x in layout['instances']if x['name']==name)\n assert row['kind']=='resistor'and row['width_um']==1 and row['length_um']==length"),
   ('two pull-down rppd L7to8um deltas with both24um MIMs retained and89unchanged intrinsic geometries','one SECOND reference rppd L12.7to11.5um delta with FIRST L12.7, both pull-down L8 and both24um MIMs retained and90unchanged intrinsic geometries'),
   ('and8actualgeometryfaults','and10actualgeometryfaults'),
  ]
 applied=[]
 for a,b in edits:
  if a in s:applied.append(dict(before=a,after=b,count=s.count(a)));s=s.replace(a,b)
 p=B/name;assert not p.exists();p.write_text(s);ast.parse(s)
 reverse=s
 for e in reversed(applied):reverse=reverse.replace(e['after'],e['before'])
 assert reverse==old
 rows.append(dict(path=str(p),pin=pin(p),parent=str(O/name),parent_pin=pin(O/name),replacements=applied,full_diff=''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True)))))
(B/'source-bridge.json').write_text(json.dumps(rows,indent=2)+'\n');print('All three independent saved reader full inverses verified; actual same native API settings, no extraction.')
