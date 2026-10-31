#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Source-only current-binding namespace; never authorizes native acquisition or RC."""
import ast,copy,hashlib,json,re,types
from collections import Counter
from decimal import Decimal
from pathlib import Path

FROZEN_SOURCE="ebe4ebb3ca2aef7b23cfc68f4b17588c03cd84fb"
FROZEN_PATH="scripts/audit_cdr_v59_mim_intrinsic.py"
FROZEN_PIN={"bytes":3550,"sha256":"5e1f61f64c702b1636aca245a2772f5f8150fb5edd5a42020352ab059f439865"}
FROZEN_DEFINITIONS={"require":{"bytes":65,"sha256":"b509d6553af67925b691064575cc6a44ff58a39778fa364f77eabee150bc6c55"},"validate_mim":{"bytes":3106,"sha256":"074126d022ad6a03b9b5aa8b7356313c11d1570e111e4521715a552a75248de7"}}
NATIVE_FLAGS=("native_acquisition_authorized","native_execution_authorized","rc_extraction_authorized","electrical_simulation_authorized")
BINDING_PASS="PASS_PD500_NATIVE_MODEL_BINDING_14_FAULTS_AND_NATIVE_CONTACT_ORACLE_REQUIRES_WIRE_COMPOSITION_AND_WAVES"
CENSUS=dict(npn13G2=124,sg13_lv_nmos=50,rppd=98,cap_cmim=7,ptap1=221)

def require(ok,message):
    if not ok:raise ValueError(message)

def encode(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()

def decode(raw):
    require(type(raw)is bytes,"exact JSON bytes required")
    def pairs(rows):
        result={}
        for key,value in rows:
            require(key not in result,"duplicate JSON key");result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda token:(_ for _ in()).throw(ValueError("nonfinite JSON")))

def pin(raw):
    require(type(raw)is bytes,"exact bytes required")
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def validate_pin(value):
    require(set(value)=={"bytes","sha256"}and type(value["bytes"])is int and value["bytes"]>0,"nonempty exact byte pin")
    require(type(value["sha256"])is str and re.fullmatch("[0-9a-f]{64}",value["sha256"]),"SHA256 pin")
    return value

def validate_config(config):
    require(config["schema"]=="cdr-via2-m3-fresh-rc-namespace-source-v1","exact namespace schema")
    require(config["frozen_source"]==FROZEN_SOURCE and config["frozen_path"]==FROZEN_PATH,"exact immutable numerical source")
    require(config["candidate_view_producer"]is None,"actual view binding deliberately absent")
    require(all(config[name]is False for name in NATIVE_FLAGS),"all native authority remains disabled")
    require(config["full_phy_accepted"]is config["electrical_accepted"]is config["timing_accepted"]is False,"no acceptance")
    require(set(config["definitions"])=={"require","validate_mim"},"only two frozen intrinsic definitions")
    require(config["source_pin"]==FROZEN_PIN and config["definitions"]==FROZEN_DEFINITIONS,"immutable numerical file and definition pins")
    validate_pin(config["source_pin"])
    for item in config["definitions"].values():validate_pin(item)
    return config

def regular(root,name):
    require(type(name)is str and name and not Path(name).is_absolute()and ".."not in Path(name).parts and "\\"not in name,"relative source path")
    path=root/name
    for parent in (path,*path.parents):
        require(not parent.is_symlink(),"source ancestry symlink")
        if parent==root:break
    require(path.is_file(),"missing regular frozen source")
    return path

def select_definitions(text,pins,scope,filename):
    """Compile only hash-bound definitions; never execute imports, assignments, or main."""
    lines=text.splitlines(keepends=True);tree=ast.parse(text,filename=filename);selected=[]
    for name,expected in pins.items():
        validate_pin(expected)
        found=[node for node in tree.body if isinstance(node,ast.FunctionDef)and node.name==name]
        require(len(found)==1,"missing or duplicate frozen definition: "+name);node=found[0]
        require(not node.decorator_list and not node.args.defaults and not any(node.args.kw_defaults),"definition-time execution refused")
        args=[*node.args.posonlyargs,*node.args.args,*node.args.kwonlyargs]
        if node.args.vararg is not None:args.append(node.args.vararg)
        if node.args.kwarg is not None:args.append(node.args.kwarg)
        require(node.returns is None and all(arg.annotation is None for arg in args),"definition annotation refused")
        require(not any(isinstance(child,(ast.Import,ast.ImportFrom))for child in ast.walk(node)),"selected intrinsic definition may not import historical admission")
        raw=("".join(lines[node.lineno-1:node.end_lineno]).rstrip()+"\n").encode()
        require(pin(raw)==expected,"frozen definition bytes changed: "+name);selected.append(node)
    require(not(set(pins)&set(scope)),"caller namespace would overwrite a definition")
    namespace=dict(scope)
    exec(compile(ast.Module(body=selected,type_ignores=[]),filename,"exec"),namespace)
    require(all(callable(namespace[name])for name in pins),"frozen definitions missing after compile")
    return namespace

class CurrentBinding:
    """Recheck exact current descriptor/summary bytes on every read; no native authority."""
    def __init__(self,reader,context,descriptor_pin):
        require(callable(reader),"explicit current binding reader")
        require(set(context)=={"source","run_id","attempt"}and type(context["source"])is str and re.fullmatch("[0-9a-f]{40}",context["source"]),"explicit current source")
        require(type(context["run_id"])is int and context["run_id"]>0 and type(context["attempt"])is int and context["attempt"]==1,"explicit current run/attempt")
        self._reader=reader;self._context=copy.deepcopy(context);self._descriptor_pin=copy.deepcopy(validate_pin(descriptor_pin))
    def stage_report(self,stage):
        require(stage=="binding","only current binding stage allowed")
        packet=self._reader()
        require(type(packet)is dict and set(packet)=={"descriptor","summary"},"complete current binding packet")
        descriptor_raw=packet["descriptor"];summary_raw=packet["summary"]
        require(pin(descriptor_raw)==self._descriptor_pin,"current descriptor byte identity changed")
        descriptor=decode(descriptor_raw);report=decode(summary_raw)
        require(set(descriptor)=={"run","source_head","summary_sha256","report"},"exact current stage descriptor")
        require(descriptor["run"]==self._context["run_id"]and type(descriptor["run"])is int and descriptor["source_head"]==self._context["source"],"stale binding source/run")
        require(descriptor["summary_sha256"]==pin(summary_raw)["sha256"]and descriptor["report"]==report,"actual current summary bytes and descriptor disagree")
        require(report["source_head"]==self._context["source"]and report["status"]==BINDING_PASS and report["sources_unchanged"]is True,"current binding result incomplete")
        require(all(report[key]is False for key in ("native_simulation_passed","qualified_pex","wire_rc_included","full_phy_accepted","closed_loop")),"binding scope broadened")
        binding=report["binding"]
        require(binding["census"]==CENSUS and len(binding["devices"])==500,"complete current 500-device binding")
        devices=binding["devices"];ids=[row["native_id"]for row in devices]
        require(all(type(value)is int for value in ids)and set(ids)==set(range(1,501))and len(set(ids))==500,"complete unique current native IDs")
        require(Counter(row["model"]for row in devices)==CENSUS,"current model census")
        require(len(binding["native_ports"])==len(set(binding["native_ports"]))==25,"complete current public ports")
        require(len(report["controls"])==14 and all(row["rejected"]is True for row in report["controls"]),"complete current binding fault controls")
        require(report["target_length_controls"]["actual_fresh_binding"]is True and len(report["target_length_controls"]["rejected"])==6,"current target length controls")
        require(len(report["native_contact_comparisons"])==221 and len(report["contact_model_controls"]["rejected_geometry"])==len(report["contact_model_controls"]["rejected_compact_models"])==3,"current contact oracle scope")
        return copy.deepcopy(report)
    def identity(self):
        return dict(scope="CURRENT_BINDING_BYTES_ONLY_NOT_NATIVE_ADMISSION",context=copy.deepcopy(self._context),descriptor_pin=copy.deepcopy(self._descriptor_pin),native_authority=False)

def intrinsic_namespace(root,config,current_binding):
    validate_config(config);require(type(current_binding)is CurrentBinding,"explicit isolated current binding provider required")
    raw=regular(root,FROZEN_PATH).read_bytes()
    require(pin(raw)==config["source_pin"],"complete frozen source bytes changed")
    scope=dict(Counter=Counter,Decimal=Decimal,admission=current_binding)
    namespace=select_definitions(raw.decode("utf-8"),config["definitions"],scope,str(root/FROZEN_PATH))
    return types.SimpleNamespace(require=namespace["require"],validate_mim=namespace["validate_mim"],binding=current_binding,source_identity=dict(source=FROZEN_SOURCE,path=FROZEN_PATH,pin=pin(raw)),native_authority=False)

def authorize_native(config=None):
    raise ValueError("Native acquisition, view and RC execution are unconditionally disabled in this source-only namespace")

def main():
    authorize_native()

if __name__=="__main__":main()
