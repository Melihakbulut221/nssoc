import importlib.util,pathlib,json,shutil,hashlib
p=pathlib.Path('hw/soc/flow/sim_logic_boot_gl.py')
s=importlib.util.spec_from_file_location('boot',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
lib=pathlib.Path('hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v')
assert m.digest(lib)=='28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4'
out=pathlib.Path('out');out.mkdir();report={'scope':'Unchanged native cell compatibility diagnosis only; no chip or timing acceptance','source_sha256':m.digest(p),'models_unchanged':False,'simulators':{}}
for sim in ['iverilog','verilator']:
 work=pathlib.Path('probe-'+sim)
 result=m.check_native_cell(sim,shutil.which(sim),lib,work)
 report['simulators'][sim]=result
 for log in work.glob('*.log'):shutil.copyfile(log,out/(sim+'-'+log.name))
report['models_unchanged']=m.digest(lib)=='28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4'
(out/'result.json').write_text(json.dumps(report,indent=2))
assert report['models_unchanged']
print(json.dumps(report,indent=2))
# Probe outcome retained, workflow success only means diagnostics collected.
