"""Actual source-graph expansion only; no new wire model or analog simulation."""
from pathlib import Path
import ast,hashlib,json,sys,os,resource
R=Path.cwd();B=Path(__file__).resolve().parent
assert os.sched_getaffinity(0)=={10}
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,)*2)
sys.path.insert(0,str(R/'scripts'))
import characterize_pcie_vco_v6_divider_bias8_v1_wire_v1 as parent

def pin(p):return dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
ns=dict(parent.__dict__)
for key,name in [('REFERENCE','clock_div4_hbt_v10.spice'),('REFERENCE_PARENT','clock_div4_hbt_v9.spice'),('REFERENCE_CAP24','clock_div4_hbt_v8.spice'),('REFERENCE_DIV2','clock_div2_hbt.spice')]:
 p=R/'hw/soc/analog/pcie'/name;ns[key]=p;ns[key+'_SHA']=pin(p)['sha256']
fragment=B/'reference_rows-fragment.py';tree=ast.parse(fragment.read_text());assert len(tree.body)==1 and isinstance(tree.body[0],ast.FunctionDef)
exec(compile(tree,str(fragment),'exec'),ns)
_,nominal,texts=parent.previous.config()
a,_=parent.reference_rows(nominal,texts);b,source=ns['reference_rows'](nominal,texts)
aa={r['path']:r for r in a};bb={r['path']:r for r in b};assert len(aa)==len(bb)==73 and set(aa)==set(bb)
changed=[p for p in aa if aa[p]!=bb[p]];assert changed==['xchain.xdiv.xsecond.xbias'],changed
assert bb[changed[0]]==dict(aa[changed[0]],params=dict(aa[changed[0]]['params'],l='11.5u'))
assert aa['xchain.xdiv.xfirst.xcore.xbias']==bb['xchain.xdiv.xfirst.xcore.xbias']
r=dict(status='PASS_SOURCE_GRAPH_ONLY_EXACT_ONE_SECOND_STAGE_REFERENCE_DELTA',inputs={str(p):pin(p)for p in [fragment,Path(parent.__file__),*(ns[k]for k in ['REFERENCE','REFERENCE_PARENT','REFERENCE_CAP24','REFERENCE_DIV2'])]},changed=changed,before=aa[changed[0]],after=bb[changed[0]],source_devices=73,unchanged_records=72,first_stage_reference=bb['xchain.xdiv.xfirst.xcore.xbias'],scope='Pure frozen source expansion only; no native wire model generation, simulation, physical acceptance or control replay.')
p=B/'source-reference-draft-control01.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],pin(p))
