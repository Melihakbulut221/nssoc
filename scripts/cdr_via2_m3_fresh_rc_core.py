#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Current-source RC numerical core; standalone native entry is disabled.

This library acquires nothing and grants no execution authority. A separately
reviewed host must authenticate inputs and supervise every native child process.
"""
import ast,copy,difflib,hashlib,importlib,inspect,io,json,math,re,shlex,shutil,sys,time,tokenize
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import cdr_via2_m3_fresh_rc_namespaces as binding_namespace

TOP='nssoc_cdr_pd500_resistor_v59'
MODEL='nssoc_cdr_pd500_resistor_v59_compact'
CENSUS=dict(npn13G2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)
CATALOG='scripts/cdr-via2-m3-fresh-rc-core-catalog.json'
CONFIG='scripts/cdr-via2-m3-fresh-rc-core-inputs.json'
RAW_PARSER='scripts/frozen_cdr_rc/audit_pilot.py'

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def encode(value):return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()

def regular(root,relative):
    root=Path(root).resolve();path=root/relative
    require(path.is_file()and not path.is_symlink(),'missing or linked source '+relative)
    require(root in path.resolve().parents,'source escaped root')
    require(not any(p.is_symlink()for p in path.parents if p!=root),'linked source ancestry')
    return path

def catalog(root):return json.loads(regular(root,CATALOG).read_text())

def source(root,key):
    item=catalog(root)['sources'][key];path=regular(root,item['path']);data=path.read_bytes()
    require(len(data)==item['bytes']and hashlib.sha256(data).hexdigest()==item['sha256'],'frozen source bytes '+key)
    return path,data.decode('utf-8'),item

def checked_nodes(root,key,names):
    path,text,item=source(root,key);tree=ast.parse(text);lines=text.splitlines();nodes=[]
    require(len(names)==len(set(names))and set(names)<=set(item['definitions']),'unapproved definition selection')
    for name in names:
        found=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name==name]
        require(len(found)==1,'missing or duplicated definition')
        node=found[0];pin=item['definitions'][name];raw=('\n'.join(lines[node.lineno-1:node.end_lineno]).rstrip()+'\n').encode()
        require(len(raw)==pin['bytes']and hashlib.sha256(raw).hexdigest()==pin['sha256'],'frozen definition bytes')
        require(hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()==pin['ast_sha256'],'frozen definition AST')
        require(not node.decorator_list,'definition decorators refused')
        if isinstance(node,ast.FunctionDef):
            require(not node.args.defaults and not any(node.args.kw_defaults)and node.returns is None,'definition-time evaluation refused')
            require(all(a.annotation is None for a in [*node.args.posonlyargs,*node.args.args,*node.args.kwonlyargs]),'argument annotation refused')
        nodes.append(copy.deepcopy(node))
    return path,nodes

def functions(root,key,names,scope):
    path,nodes=checked_nodes(root,key,names);ns=dict(scope)
    require(not set(names)&set(ns),'definition/global collision')
    ns['__file__']=str(path);ns['__name__']='nssoc_current_rc_frozen_'+key
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(path),'exec'),ns)
    return SimpleNamespace(**{n:ns[n]for n in names},__file__=str(path))

def block_nodes(root,name):
    pin=catalog(root)['blocks'][name];_,text,_=source(root,pin['source']);tree=ast.parse(text)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main')
    tr=next(n for n in main.body if isinstance(n,ast.Try));a,b=pin['span']
    nodes=[n for n in tr.body if a<=n.lineno and n.end_lineno<=b]
    require(nodes and min(n.lineno for n in nodes)==a and max(n.end_lineno for n in nodes)==b,'numeric block boundaries')
    require(all(a<=n.lineno and n.end_lineno<=b for n in tr.body if n.lineno<=b and n.end_lineno>=a),'partial statement selection')
    raw=('\n'.join(text.splitlines()[a-1:b])+'\n').encode()
    require(len(nodes)==pin['statements']and len(raw)==pin['bytes']and hashlib.sha256(raw).hexdigest()==pin['sha256'],'numeric block source bytes')
    require(hashlib.sha256(ast.dump(ast.Module(body=nodes,type_ignores=[]),include_attributes=False).encode()).hexdigest()==pin['ast_sha256'],'numeric block AST')
    return pin,copy.deepcopy(nodes)

def run_block(root,name,scope,values):
    pin,nodes=block_nodes(root,name)
    require(set(values)==set(pin['args']),'exact numerical block argument names')
    require(not set(pin['args'])&set(scope),'numeric argument/global collision')
    fn=ast.parse('def numerical_stage('+','.join(pin['args'])+'):\n    pass\n').body[0]
    fn.body=nodes+[ast.Return(value=ast.Dict(keys=[ast.Constant(x)for x in pin['returns']],values=[ast.Name(id=x,ctx=ast.Load())for x in pin['returns']]))]
    ns=dict(scope);exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'<frozen-current-'+name+'>','exec'),ns)
    return ns['numerical_stage'](**values)

def literal(root,key,name):
    _,text,_=source(root,key);found=[n for n in ast.parse(text).body if isinstance(n,ast.Assign)and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)and n.targets[0].id==name]
    require(len(found)==1,'literal source constant')
    return ast.literal_eval(found[0].value)

def dependencies(root):
    for key,module_name in [('parser','build_pcie_local_vco_hybrid_v6'),('models','build_cdr500_cleaned_native_models')]:
        path,_,_=source(root,key);module=importlib.import_module(module_name)
        require(Path(module.__file__).resolve()==path.resolve(),'converter module origin')
    return sys.modules['build_cdr500_cleaned_native_models'],sys.modules['build_pcie_local_vco_hybrid_v6']

def common(root):
    models,parser=dependencies(root)
    return dict(ast=ast,copy=copy,difflib=difflib,hashlib=hashlib,inspect=inspect,io=io,json=json,math=math,re=re,shlex=shlex,shutil=shutil,sys=sys,time=time,tokenize=tokenize,Counter=Counter,defaultdict=defaultdict,Decimal=Decimal,Path=Path,patch=patch,sha=sha,models=models,parser=parser)

def target_namespace(root,scope):
    return functions(root,'targets',['validate_bound_targets','binding_target_controls'],dict(scope,TARGETS=(184,185,222,223)))

def binding_functions(root,out):
    scope=dict(common(root),ROOT=Path(root),OUT=Path(out),TOP=TOP,MODEL=MODEL,CENSUS=CENSUS)
    return functions(root,'binding',['native_contact_oracle','native_export','geometry_readback_matches','geometry_readback_controls','build','verify','controls'],scope)

def binding_native_export(root,out):
    return binding_functions(root,out).native_export()

def binding_validate(root,out,technology_root=None):
    scope=common(root);f=binding_functions(root,out)
    scope.update({n:getattr(f,n)for n in ('geometry_readback_controls','build','verify','controls')})
    scope['admission']=target_namespace(root,common(root));r={}
    try:
        result=run_block(root,'binding_validate',scope,dict(ROOT=Path(root if technology_root is None else technology_root),OUT=Path(out),r=r))
        (Path(out)/'pd500-compact.spice').write_text(result['text'])
        (Path(out)/'binding.json').write_bytes(encode(result['binding']))
        return result
    finally:(Path(out)/'binding-core-observations.json').write_bytes(encode(r))

def derive_wire_methods(root,wire_parent):
    scope=common(root);scope['NONBRIDGE_SELECTOR']=literal(root,'v4','NONBRIDGE_SELECTOR')
    methods=json.loads(regular(root,'docs/evidence/cdr-v4-rc-inputs-20261017.json').read_text())['report']['original_extraction_methods']
    result=run_block(root,'wire_derive',scope,dict(OUT=Path(wire_parent),methods=methods))
    return result['edits']

def raw_parser(root):
    scope=common(root)
    h=functions(root,'spice_lines',['require','spice_lines'],{})
    return functions(root,'raw_parser',['require','number','parse_spice'],dict(scope,h=h))

def current_binding(root,packet,context,descriptor_pin):
    # Packet-reader performs a fresh byte read on every intrinsic or composition use.
    cb=binding_namespace.CurrentBinding(packet,context,descriptor_pin)
    cfg=json.loads(regular(root,'scripts/cdr-via2-m3-fresh-rc-namespace-inputs.json').read_text())
    intrinsic=binding_namespace.intrinsic_namespace(Path(root),cfg,cb)
    return cb,intrinsic

def generated_functions(text,names,scope,filename):
    tree=ast.parse(text);nodes=[]
    require(len(names)==len(set(names)),'unique generated definition list')
    for name in names:
        found=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name]
        require(len(found)==1,'generated definition missing or duplicated')
        require(not found[0].decorator_list and not found[0].args.defaults and not any(found[0].args.kw_defaults),'generated definition-time evaluation')
        nodes.append(copy.deepcopy(found[0]))
    ns=dict(scope);require(not set(names)&set(ns),'generated definition/global collision')
    ns.update(__file__=str(filename),__name__='nssoc_current_rc_generated')
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(filename),'exec'),ns)
    return SimpleNamespace(**{n:ns[n]for n in names},__file__=str(filename))

def audit_namespace(root,wire,method_pin,intrinsic=None):
    import networkx as nx
    wire=Path(wire);target=wire/'audit-rc48.py'
    require(sha(target)==method_pin,'generated auditor identity')
    scope=dict(common(root),nx=nx,B=wire,PRIOR=regular(root,RAW_PARSER),rawparser=raw_parser(root))
    if intrinsic is not None:scope['validate_mim']=intrinsic.validate_mim
    module=generated_functions(target.read_text(),['pin','require','read','close','edge','audit'],scope,target)
    module.rawparser=scope['rawparser'];module.PRIOR=scope['PRIOR']
    return module

def wire_corruptions(root,wire,module,method_pin):
    import networkx as nx
    wire=Path(wire);path=wire/'mutations48.py';require(sha(path)==method_pin,'wire mutations identity')
    tree=ast.parse(path.read_text());start=next(i for i,n in enumerate(tree.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='a'for t in n.targets))
    selected=tree.body[start:]
    require(not any(isinstance(n,(ast.Import,ast.ImportFrom))and (isinstance(n,ast.Import)or n.module!='collections')for node in selected for n in ast.walk(node)),'mutation import surface')
    scope=dict(common(root),nx=nx,B=wire,P=wire/'rc03',m=module,__file__=str(path),__name__='nssoc_current_wire_mutations')
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected,type_ignores=[])),str(path),'exec'),scope)
    require(len(scope['r']['cases'])==13,'all frozen wire controls')
    return scope['r']

def wire_audit(root,wire,method_pins):
    wire=Path(wire);module=audit_namespace(root,wire,method_pins['audit-rc48.py']['adapted_sha256'])
    result=module.audit(wire/'rc03',json.loads((wire/'anchors08.json').read_text()))
    (wire/'audit.json').write_bytes(encode(result))
    require(result['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY','full raw wire audit')
    controls=wire_corruptions(root,wire,module,method_pins['mutations48.py']['adapted_sha256'])
    return dict(audit=result,controls=controls)

def capture_generate(root,variant_out):
    scope=dict(common(root),ROOT=Path(root),OUT=Path(variant_out),TOP=TOP)
    return functions(root,'capture',['generate'],scope).generate()

def prepare_capture_runtime(root,variant_out,qualified):
    return run_block(root,'capture_runtime',common(root),dict(OUT=Path(variant_out),qualified=qualified))

def derive_capture_methods(root,variant_out,variant):
    require(variant in ('precise','precise_reversed'),'native order variant')
    r={};out=Path(variant_out)
    def save():(out/'method-derivation.json').write_bytes(encode(r))
    try:return run_block(root,'capture_method',common(root),dict(ROOT=Path(root),OUT=out,VARIANT=variant,precise='1a44bd5c70af3800213419c2e3b2213285523a74fcc4b92bc9cf7314d93a592c',r=r,save=save))
    finally:save()

def capture_finish(root,variant_out,capture,binding):
    scope=common(root);scope['check_capture']=functions(root,'capture',['check_capture'],scope).check_capture
    return run_block(root,'capture_finish',scope,dict(OUT=Path(variant_out),capture=capture,binding=binding,r={}))['r']

def mim_audit(root,variant_out,capture_result,packet,context,descriptor_pin):
    out=Path(variant_out);scope=common(root);cb,intrinsic=current_binding(root,packet,context,descriptor_pin)
    scope['audit_cdr_v59_mim_intrinsic']=SimpleNamespace(__file__=str(source(root,'intrinsic')[0]))
    bound=cb.stage_report('binding');data=packet();check=binding_namespace.CurrentBinding(lambda:data,context,descriptor_pin);check.stage_report('binding')
    descriptor=binding_namespace.decode(data['descriptor'])
    require(capture_result['model_binding_source']['summary_sha256']==descriptor['summary_sha256']and capture_result['model_binding_source']['run']==descriptor['run'],'capture uses exact current binding')
    require(capture_result['native_order_variant']==out.name and out.name in ('precise','precise_reversed'),'exact native capture variant')
    r=dict(capture_counts=capture_result['intrinsic_capture_binding'],intrinsic_binding_source=dict(run=descriptor['run'],summary_sha256=descriptor['summary_sha256']));derived=run_block(root,'audit_derive',scope,dict(CAP=out,r=r));wire=derived['B']
    module=audit_namespace(root,wire,r['adaptations']['new_auditor_sha256'],intrinsic)
    r['audit']=module.audit(wire/'rc03',json.loads((wire/'anchors08.json').read_text()))
    (wire/'mim-audit.json').write_bytes(encode(r['audit']))
    require(r['audit']['status']=='PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY','strict MIM wire audit')
    require(r['audit']['actual_exported_resistors']==capture_result['intrinsic_capture_binding']['R']and r['audit']['actual_exported_capacitors']==capture_result['intrinsic_capture_binding']['C']and r['audit']['native_mim_intrinsic']['devices']==7,'complete measured raw R/C and seven MIM agreement')
    r['wire_controls']=wire_corruptions(root,wire,module,r['adaptations']['unchanged_wire_mutations_sha256'])
    try:return run_block(root,'audit_intrinsic_controls',scope,dict(B=wire,P=wire/'rc03',module=module,r=r))['r']
    finally:(out/'intrinsic-audit-controls.json').write_bytes(encode(r))

def composition_namespace(root,text,nr,nc):
    scope=common(root);d=functions(root,'derivation',['derive','controls'],dict(scope,SOURCE_SHA='c87d213c8676f58d989fc85c91b0408d5c1581cd69f14f96d96ed2e986d299a8',MODEL='nssoc_cdr_pd500_resistor_mim_wire_v59'))
    expected,_=d.derive(source(root,'composition')[1],nr,nc)
    require(text==expected,'exact measured-count composition derivation')
    return generated_functions(text,['assemble','verify','faults'],dict(scope,MODEL='nssoc_cdr_pd500_resistor_mim_wire_v59'),'<current-measured-composition>')

def compose_functions(root,mim_out,packet,context,descriptor_pin):
    scope=common(root);cb,_=current_binding(root,packet,context,descriptor_pin)
    def binding_pin():
        data=packet();check=binding_namespace.CurrentBinding(lambda:data,context,descriptor_pin)
        report=check.stage_report('binding');descriptor=binding_namespace.decode(data['descriptor'])
        require(descriptor['report']==report,'binding packet report mismatch')
        return descriptor
    scope.update(ROOT=Path(root),OUT=Path(mim_out),MODEL='nssoc_cdr_pd500_resistor_mim_wire_v59',admission=SimpleNamespace(binding_pin=binding_pin))
    d=functions(root,'derivation',['derive','controls'],dict(common(root),SOURCE_SHA='c87d213c8676f58d989fc85c91b0408d5c1581cd69f14f96d96ed2e986d299a8',MODEL='nssoc_cdr_pd500_resistor_mim_wire_v59'))
    scope['derive_composition']=d.derive
    scope['composition_namespace']=lambda text,nr,nc:composition_namespace(root,text,nr,nc)
    path,nodes=checked_nodes(root,'precision',['compose']);node=nodes[0]
    markers=[i for i,n in enumerate(node.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='spec'for t in n.targets)]
    require(len(markers)==1,'one old generated-module loading boundary');i=markers[0]
    original=node.body[i:i+3]
    expected=ast.parse("spec=importlib.util.spec_from_file_location('fresh_pd500_composition',method);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)").body
    require(ast.dump(ast.Module(body=original,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=expected,type_ignores=[]),include_attributes=False),'exact historical import boundary')
    node.body[i:i+3]=ast.parse('m=composition_namespace(text,nr,nc)').body
    scope.update(__file__=str(path),__name__='nssoc_current_composition')
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(path),'exec'),scope)
    return scope['compose']

def compare_and_compose(root,mim_out,packet,context,descriptor_pin,variants):
    require(set(variants)=={'precise','precise_reversed'},'both native order variants required')
    for variant,row in variants.items():
        require(row['capture']['native_order_variant']==variant,'current native variant identity')
        require(len(row['audit']['wire_controls']['cases'])==13 and len(row['audit']['intrinsic_controls'])==9 and all(c['rejected']for c in row['audit']['intrinsic_controls']),'all thirteen wire and nine intrinsic controls in each order')
    scope=common(root);cap_order=functions(root,'cap_order',['rows','capkey','reorder','controls'],scope)
    records=functions(root,'precision',['records'],scope).records
    result=dict(variants=variants)
    scope.update(cap_order=cap_order,records=records)
    run_block(root,'order_compare',scope,dict(OUT=Path(mim_out),result=result))
    compose=compose_functions(root,mim_out,packet,context,descriptor_pin)
    result['composition']=compose(variants['precise']['capture'],variants['precise']['audit'])
    require(len(result['composition']['controls'])==21,'all composition controls')
    return result

def authorize_native():
    raise ValueError('Standalone native acquisition, RC extraction and electrical execution remain unconditionally disabled; a separately reviewed host is required')

if __name__=='__main__':authorize_native()
