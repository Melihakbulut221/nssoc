# SPDX-License-Identifier: Apache-2.0
"""Run the exact pinned Ruby RES2 class and its proposed switch correction."""
import pathlib,subprocess,json,zipfile,io,hashlib,re
import klayout.db as db
P=pathlib.Path
raw=P('diagnostic.zip').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='d6ff10e2ebc4613908dad51f338860592ef9ef4b8e88e48b729538d22a93e45a'
data=json.loads(zipfile.ZipFile(io.BytesIO(raw)).read('top-mismatch.json'))
source=data['deck_source_evidence']['custom_devices.lvs']['source']
assert hashlib.sha256(source.encode()).hexdigest()==data['deck_source_evidence']['custom_devices.lvs']['sha256']
match=re.search(r'(?ms)^class RES2 < RBA::DeviceClassResistor\n.*?^end$',source);assert match
original=match[0]
assert original.count('    super\n')==1
fixed=original.replace('    super\n','    super\n    self.supports_serial_combination = SERIES_RES\n    self.supports_parallel_combination = PARALLEL_RES\n')
P('out').mkdir();rows=[]
for variant,definition in [('original',original),('fixed',fixed)]:
 for serial in [False,True]:
  for parallel in [False,True]:
   tag=f'{variant}-{int(serial)}-{int(parallel)}'
   ruby="require 'json'\nSERIES_RES = "+str(serial).lower()+"\nPARALLEL_RES = "+str(parallel).lower()+"\n"+definition+"\nd = RES2.new\n"
   ruby += "def flag(d,n); d.send(d.respond_to?(n) ? n : n+'?'); end\n"
   ruby += "File.write('flags.json', JSON.generate({'serial'=>flag(d,'supports_serial_combination'),'parallel'=>flag(d,'supports_parallel_combination')}))\n"
   P('flags.rb').write_text(ruby)
   proc=subprocess.run(['klayout','-b','-zz','-r','flags.rb'],timeout=60,capture_output=True,text=True)
   if proc.returncode:
    failure={'variant':variant,'tag':tag,'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'production_accepted':False}
    P('out/native-control-error.json').write_text(json.dumps(failure,indent=2));print(json.dumps(failure));proc.check_returncode()
   flags=json.loads(P('flags.json').read_text())
   expected={'serial':serial,'parallel':parallel} if variant=='fixed' else {'serial':True,'parallel':True}
   assert flags==expected,(tag,flags,expected)
   for kind in ['serial','parallel']:
    text='* native resistor merge control\n.SUBCKT TOP a b\n'
    text+=('R1 a x 1000\nR2 x b 1000\n' if kind=='serial' else 'R1 a b 1000\nR2 a b 1000\n')+'.ENDS TOP\n'
    P('control.cir').write_text(text)
    nl=db.Netlist();nl.read('control.cir',db.NetlistSpiceReader());c=nl.circuit_by_name('TOP');devs=list(c.each_device());assert len(devs)==2
    for cls in nl.each_device_class():
     cls.supports_serial_combination=flags['serial'];cls.supports_parallel_combination=flags['parallel']
     cls.enable_parameter('W',True);cls.enable_parameter('L',True);cls.enable_parameter('R',False)
    nl.combine_devices();after=list(c.each_device());count=1 if flags[kind] else 2
    assert len(after)==count,(tag,kind,len(after),count)
    rows.append({'variant':variant,'requested_serial':serial,'requested_parallel':parallel,'actual_Ruby_class_flags':flags,'topology':kind,'device_count_before':2,'device_count_after':len(after),'expected_count':count})
r={'status':'PASS_ISOLATED_MERGE_SWITCH_CONTROLS','source_sha':__import__('os').environ.get('GITHUB_SHA'),'original_custom_devices_sha256':hashlib.sha256(source.encode()).hexdigest(),'original_RES2_source':original,'candidate_RES2_source':fixed,'cases':rows,'scope':'Exact Ruby class flag evaluation plus native KLayout two-resistor combine controls. Not macro LVS, topology qualification, DRC, or manufacturing acceptance. No SRAM GDS/CDL or comparison tolerances changed.','production_accepted':False,'upstream_reference':'https://github.com/IHP-GmbH/IHP-Open-PDK/pull/1121','upstream_head':'3df647ebe53439ae41d56a1e9c2b38003ba2124d'}
P('out/merge-switch-controls.json').write_text(json.dumps(r,indent=2));print(r['status'],len(rows))
