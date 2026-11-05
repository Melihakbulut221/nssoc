# SPDX-License-Identifier: Apache-2.0
"""Fresh nominal RC and original-clock three-corner STA on a routed main-chip database.

Measurement only. The verified post-route input package (run 39635867954)
supplies the PDK, configuration, SDC and macro views unchanged. Only the
routed database, its DEF export and its Verilog export replace the package's
pre-route candidate. RC extraction and STA run through the repository's own
AuditedRCX and AuditedRoutedSTA steps (ReplayOnehotRoutedExtraction flow) in
LibreLane 3.0.5. This is not the qualified post-route wrapper and accepts
nothing; it reports what the frozen timing gates would see on this route.
"""
import collections,hashlib,json,math,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CORNERS=['nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C']
GATED=['timing__setup__ws','timing__hold__ws','timing__setup_vio__count','timing__hold_vio__count',
 'design__max_cap_violation__count','design__max_slew_violation__count','design__max_fanout_violation__count']
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb')as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def worst_paths(report,limit=4000):
    rows=[];cur={}
    for line in report.open(errors='replace'):
        s=line.strip()
        if s.startswith('Startpoint:'):cur=dict(start=s.split()[1])
        elif s.startswith('Endpoint:')and cur:cur['end']=s.split()[1]
        elif s.startswith('Path Group:')and cur:cur['group']=s.split()[2]
        elif s.endswith('slack (VIOLATED)')or s.endswith('slack (MET)'):
            if cur:
                try:cur['slack']=float(s.split()[0])
                except ValueError:pass
                rows.append(cur);cur={}
                if len(rows)>=limit:break
    return rows
def module(name,depth=2):
    parts=re.split(r'[./]',name.replace('\\',''))
    return '.'.join(parts[:depth])if len(parts)>1 else '<top-port>'
def restore(package):
    contract=json.loads((package/'input-contract.json').read_text())
    assert contract['clocks_ns']==[20,4,8,8]and contract['derating_percent']==5
    assert contract['original_pdk_revision']=='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
    assert contract['original_root']==str(ROOT),(contract['original_root'],str(ROOT))
    restored=0
    for name,row in contract['input_files'].items():
        rel=Path(name);assert not rel.is_absolute()and '..'not in rel.parts
        src=package/'files'/rel;dst=ROOT/rel;assert sha(src)==row['sha256']
        if dst.exists():assert sha(dst)==row['sha256'],('existing input differs',name)
        else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);restored+=1
    return contract,restored
def main(package,odb,deffile,netlist,app,out):
    package,out=Path(package),Path(out);out.mkdir(parents=True,exist_ok=True)
    r=dict(status='RUNNING',accepted=False,scope=__doc__.strip().split('\n\n')[1].replace('\n',' '))
    save=lambda:(out/'result.json').write_text(json.dumps(r,indent=1,sort_keys=True)+'\n');save()
    contract=json.loads((package/'input-contract.json').read_text())
    assert contract['clocks_ns']==[20,4,8,8]and contract['derating_percent']==5
    assert contract['original_pdk_revision']=='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
    assert contract['original_root']==str(ROOT),(contract['original_root'],str(ROOT))
    restored=0
    for name,row in contract['input_files'].items():
        rel=Path(name);assert not rel.is_absolute()and '..'not in rel.parts
        src=package/'files'/rel;dst=ROOT/rel;assert sha(src)==row['sha256']
        if dst.exists():assert sha(dst)==row['sha256'],('existing input differs',name)
        else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);restored+=1
    r['restored_input_files']=restored;r['input_files']=len(contract['input_files'])
    raw=package/'trial-config.json';state=json.loads((package/'candidate-state.json').read_text())
    assert sha(raw)==contract['configuration_sha256']
    assert sha(state['sdc'])=='19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597'
    replaced=dict(odb=state['odb'],nl=state['nl'],def_=state['def'])
    state.update(odb=str(odb),nl=str(netlist),spef=None,pnl=None,sdf=None,metrics={});state['def']=str(deffile)
    r['inputs']=dict(odb=sha(odb),def_=sha(deffile),netlist=sha(netlist),sdc=sha(state['sdc']),config=sha(raw),replaced_package_paths=replaced)
    trial=out/'trial-config.json';trial.write_bytes(raw.read_bytes())
    initial=out/'initial-state.json';initial.write_text(json.dumps(state,indent=2)+'\n')
    flow=ROOT/'hw/soc/pnr/replay_onehot_routed_extraction_flow.py'
    run=out/'run';run.mkdir()
    cmd=[str(app),'python',str(flow),'--flow','ReplayOnehotRoutedExtraction','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),
         '--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(run),'--with-initial-state',str(initial),str(trial)]
    env={k:v for k,v in os.environ.items()if k not in('GH_TOKEN','GITHUB_TOKEN')}
    r.update(status='RUNNING_RCX_STA',command=cmd);save()
    with(out/'native.log').open('w')as log:code=subprocess.call(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    r['returncode']=code;save()
    if code:print((out/'native.log').read_text(errors='replace')[-16000:],flush=True)
    assert code==0,'native RCX/STA failed'
    step=lambda p:[x for x in run.glob(p)]
    rc,=step('*-nssoc-onehotroutercx');sta,=step('*-nssoc-onehotroutedsta')
    r['spef_integrity']=json.loads((rc/'native-spef-integrity.json').read_text())
    r['sta_script_proof']=json.loads((sta/'native-sta-script-proof.json').read_text())
    measured=json.loads((sta/'state_out.json').read_text());m={}
    for c in CORNERS:
        f=sta/c;met={k.split('__corner:')[0]:v for k,v in measured['metrics'].items()if k.endswith('__corner:'+c)}
        gate={k:met.get(k)for k in GATED}
        ok=all(v is not None and math.isfinite(v)for v in gate.values())and gate['timing__setup__ws']>=0 and gate['timing__hold__ws']>=0 and all(gate[k]==0 for k in GATED[2:])
        props=(f/'sta.log').read_text(errors='replace')
        entry=dict(metrics=met,gate=gate,gate_met=ok,unpropagated_empty=not(f/'unpropagated.rpt').read_text().strip(),
                   clocks_propagated_marker='NSSOC_ROUTED_ORIGINAL_CLOCKS_PROPAGATED'in props)
        for kind in('max','min'):
            rows=worst_paths(f/(kind+'.rpt'))
            bad=[x for x in rows if x.get('slack',0)<0]
            by=collections.Counter((x.get('group'),module(x.get('end','')))for x in bad)
            entry[kind+'_violating_paths_in_report']=len(bad)
            entry[kind+'_worst']=sorted(rows,key=lambda x:x.get('slack',1e9))[:25]
            entry[kind+'_by_group_and_endpoint_module']=[dict(group=g,module=mod,paths=n,worst=min(x['slack']for x in bad if x.get('group')==g and module(x.get('end',''))==mod))for(g,mod),n in by.most_common(40)]
        m[c]=entry
    r.update(measurements=m,status='MEASURED_ALL_GATES_MET'if all(v['gate_met']for v in m.values())else'MEASURED_GATES_OPEN');save()
    for c in CORNERS:print(c,json.dumps(m[c]['gate']))
if __name__=='__main__':main(*sys.argv[1:7])
