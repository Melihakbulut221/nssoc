#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compare exact proved LCRC mapped netlists under identical zero-wire STA."""
import hashlib,io,json,os,re,shutil,subprocess,tarfile,traceback,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-lcrc-word-onehot-timing'
RUN=39890538709
HEAD='691fb685c98654ea0d0662443347b3c2753ccd8e'
SUMMARY_SHA='e1b6d7aae68aa424dd54cc84aa9968dfac95634f345bc1215615abb644ba85e0'
ARCHIVE_SHA='9d151b475cfc3f0e033292901ef85c17eaa36b834917f15c775da4bd2d3f7cac'
PDK_COMMIT='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
LIBRARIES={
 'typ':('sg13g2_stdcell_typ_1p20V_25C.lib','9654b7cb685cf7d376b9842089ea2903540448e8'),
 'slow':('sg13g2_stdcell_slow_1p08V_125C.lib','6dd075da1073a86a98d9804019842be3d2f13a9f'),
 'fast':('sg13g2_stdcell_fast_1p32V_m40C.lib','fd479d3fd11358bbacee450dc7352b46de8588cb')}
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def api(path):
    return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path],text=True))
def asset(aid):
    return subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/releases/assets/'+str(aid),'-H','Accept: application/octet-stream'])
def q(s):
    s=str(s);assert not any(c in s for c in '{}\n\r');return '{'+s+'}'

def normalize_structural(module,path):
    """Only spelling changes: emit scalar wires and original physical cells."""
    assert module['ports'] and module['cells']
    bits={b for p in module['ports'].values()for b in p['bits']if isinstance(b,int)}
    bits|={b for cell in module['cells'].values()for v in cell['connections'].values()for b in v if isinstance(b,int)}
    def expr(bit):return 'n'+str(bit)if isinstance(bit,int)else "1'b"+bit
    lines=['module soc_pcie_lcrc_tx ('+', '.join(module['ports'])+');']
    for name,p in module['ports'].items():
        assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name)
        assert not p.get('upto',0)and not p.get('offset',0)and p['direction']in ['input','output']
        width=len(p['bits']);lines.append(p['direction']+(' ['+str(width-1)+':0]'if width>1 else '')+' '+name+';')
    lines += ['wire n'+str(b)+';'for b in sorted(bits)]
    for name,p in module['ports'].items():
        for i,b in enumerate(p['bits']):
            port=name+('['+str(i)+']'if len(p['bits'])>1 else '')
            lhs,rhs=(expr(b),port)if p['direction']=='input'else(port,expr(b))
            lines.append('assign '+lhs+' = '+rhs+';')
    aliases={name:'physical_cell_'+str(i)for i,name in enumerate(module['cells'])}
    for name,cell in module['cells'].items():
        assert cell['type'].startswith('sg13g2_')and not cell['parameters']
        assert not re.search(r'\s',name)
        connections=[]
        for pin,v in cell['connections'].items():
            assert len(v)==1 and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',pin)
            connections.append('.'+pin+'('+expr(v[0])+')')
        lines.append(cell['type']+' '+aliases[name]+' ('+', '.join(connections)+');')
    lines.append('endmodule')
    path.write_text('\n'.join(lines)+'\n')
    return aliases

def verify_structural(module,parsed,aliases):
    assert set(aliases)==set(module['cells']) and len(set(aliases.values()))==len(aliases)
    assert set(aliases.values())==set(parsed['cells'])
    def translate(bit):
        if isinstance(bit,str):return bit
        values=parsed['netnames']['n'+str(bit)]['bits'];assert len(values)==1
        return values[0]
    for name,cell in module['cells'].items():
        c=parsed['cells'][aliases[name]]
        assert cell['type']==c['type']and cell['parameters']==c['parameters']
        assert cell['port_directions']==c['port_directions']
        assert {p:[translate(b)for b in v]for p,v in cell['connections'].items()}==c['connections']
    assert set(module['ports'])==set(parsed['ports'])
    for name,p in module['ports'].items():
        pp=parsed['ports'][name]
        assert p['direction']==pp['direction']and [translate(b)for b in p['bits']]==pp['bits']
    return {'same_physical_cells':len(module['cells']),'same_cell_types_parameters_and_every_pin':True,'same_all_ports':True}

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    r={'status':'RUNNING','source_head':os.environ['GITHUB_SHA'],'candidate_adopted':False,'full_phy_accepted':False,'final_timing_complete':False,
       'scope':'Same exact previously proved IHP mapped default-capacity LCRC netlists, three native library corners, register-to-register setup/hold and word-address launch cones. Ideal clocks and zero interconnect RC. Fixed diagnostic slew/load, not physical/signoff timing or a whole-chip port environment.',
       'diagnostic_conditions':{'period_ns':4,'clock_uncertainty_ns':0.25,'clock_and_input_transition_ns':0.05,'output_load_pf':0.01,'late_derate':1.05,'early_derate':0.95,'wire_rc':0,'io_delays':'unconstrained; only register-to-register reports','sdf':False}}
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        run=api('actions/runs/'+str(RUN))
        assert run['status']=='completed'and run['conclusion']=='success'and run['head_sha']==HEAD and run['run_attempt']==1
        raw=asset(667748324);assert digest(raw)==SUMMARY_SHA
        source=json.loads(raw);(OUT/'source-summary.json').write_bytes(raw)
        assert source['sources_unchanged']and source['sequential']['passed']and source['capacity']==8
        assert source['candidate_sha256']=='30934f20cf650ddebfa2e88512c668dbf63ad67a3daf4f6b37e88a97d5742157'
        archive=asset(667748563);assert digest(archive)==ARCHIVE_SHA
        r['source']={'run':RUN,'head':HEAD,'summary_sha256':SUMMARY_SHA,'archive_sha256':ARCHIVE_SHA,'mapped':source['native_mapping']};save()
        tf=tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz')
        protected={}
        for label in ['baseline','candidate']:
            for ext in ['v','json']:
                suffix=label+'-rtl/mapped.'+ext
                members=[m for m in tf.getmembers()if m.name==suffix or m.name.endswith('/'+suffix)]
                assert len(members)==1 and members[0].isfile()
                b=tf.extractfile(members[0]).read()
                key='netlist_sha256'if ext=='v'else'json_sha256'
                assert digest(b)==source['native_mapping'][label][key]
                p=OUT/(label+'.'+ext);p.write_bytes(b);protected[str(p)]=sha(p)
        sta=Path(shutil.which('sta')).resolve();assert sta.is_file()
        r['tool']={'path':str(sta),'sha256':sha(sta),'version':subprocess.check_output([str(sta),'-version'],stderr=subprocess.STDOUT,text=True),
                   'source_commit':os.environ['OPENSTA_SOURCE_COMMIT'],'cudd_commit':os.environ['CUDD_SOURCE_COMMIT']}
        protected[str(sta)]=sha(sta);protected[str(Path(__file__))]=sha(__file__)
        # Retain the built tool and corresponding pinned source/build patches
        # so a later report-only fix need not rebuild the same native runtime.
        runtime=OUT/'runtime';runtime.mkdir()
        shutil.copyfile(sta,runtime/'sta')
        for tool in ['opensta','cudd']:
            source_dir=Path(os.environ['RUNNER_TEMP'])/tool
            subprocess.run(['git','-C',str(source_dir),'archive','--format=tar.gz','--output='+str(runtime/(tool+'-source.tar.gz')),'HEAD'],check=True)
            (runtime/(tool+'-generated-build.patch')).write_bytes(subprocess.check_output(['git','-C',str(source_dir),'diff','--binary']))
        shutil.copyfile(ROOT/'.github/workflows/lcrc-word-onehot-timing-cloud.yml',runtime/'build-workflow.yml')
        (runtime/'dynamic-libraries.txt').write_bytes(subprocess.check_output(['ldd',str(sta)]))
        (runtime/'README.txt').write_text('Built for Ubuntu24.04. Original source archives include all upstream licenses. Apply generated-build patches when reproducing the exact build; pinned build commands are in build-workflow.yml. This tool is not a qualified signoff runtime.\n')
        r['retained_runtime']={'binary_sha256':sha(runtime/'sta'),'scope':'Pinned native STA executable plus corresponding source archives, generated build patches and exact build workflow; Ubuntu24.04 dynamic system libraries are listed separately.'};save()

        libs={}
        for corner,(name,blob)in LIBRARIES.items():
            url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+PDK_COMMIT+'/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/'+name
            b=urllib.request.urlopen(url,timeout=60).read()
            assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob
            p=OUT/name;p.write_bytes(b);libs[corner]=p;protected[str(p)]=sha(p)
        r['libraries']={k:{'path':str(v),'sha256':sha(v),'git_blob':LIBRARIES[k][1]}for k,v in libs.items()}
        yosys=Path(shutil.which('yosys')).resolve();protected[str(yosys)]=sha(yosys)
        r['normalization']={};r['cell_name_aliases']={}
        r['measurements']={};r['launch_registers']={}
        for label in ['baseline','candidate']:
            module=json.loads((OUT/(label+'.json')).read_text())['modules']['soc_pcie_lcrc_tx']
            normalized=OUT/(label+'-scalar.v');aliases=normalize_structural(module,normalized)
            r['cell_name_aliases'][label]=aliases
            parsed=OUT/(label+'-scalar.json')
            ys=OUT/(label+'-readback.ys')
            ys.write_text('read_liberty -lib '+str(libs['typ'])+'\nread_verilog '+str(normalized)+'\nhierarchy -check -top soc_pcie_lcrc_tx\nwrite_json '+str(parsed)+'\n')
            with(OUT/(label+'-readback.log')).open('w')as log:
                code=subprocess.call([str(yosys),'-s',str(ys)],stdout=log,stderr=subprocess.STDOUT)
            assert code==0,'Native structural readback failed'
            native_module=json.loads(parsed.read_text())['modules']['soc_pcie_lcrc_tx']
            r['normalization'][label]=verify_structural(module,native_module,aliases)
            protected[str(normalized)]=sha(normalized)
            # Fault control: the comparison must detect a real pin inversion.
            import copy
            wrong=copy.deepcopy(native_module)
            n=next(n for n,x in wrong['cells'].items()if 'D'in x['connections'])
            wrong['cells'][n]['connections']['D']=['1']
            try:verify_structural(module,wrong,aliases)
            except AssertionError:r['normalization'][label]['wrong_data_pin_rejected']=True
            else:raise AssertionError('Structural readback control accepted')
            regs=['index']+(['word_read_onehot']if label=='candidate'else[])
            launch={}
            for net in regs:
                bits=module['netnames'][net]['bits'];pins=[]
                for n,c in module['cells'].items():
                    if c['type'].startswith('sg13g2_df') and any(b in bits for b in c['connections'].get('Q',[])):pins.append(aliases[n]+'/Q')
                assert pins,('Missing exact mapped launch registers',label,net)
                launch[net]=pins
            r['launch_registers'][label]=launch
            r['measurements'][label]={};save()
            for corner,lib in libs.items():
                d=OUT/(label+'-'+corner);d.mkdir()
                lines=['read_liberty '+q(lib),'read_verilog '+q(normalized),'link_design soc_pcie_lcrc_tx',
                       'create_clock -name clk -period 4 [get_ports clk_i]',
                       'set_clock_uncertainty 0.25 [get_clocks clk]',
                       'set_clock_transition 0.05 [get_clocks clk]',
                       'set_input_transition 0.05 [all_inputs]',
                       'set_load 0.01 [all_outputs]',
                       'set_timing_derate -late 1.05','set_timing_derate -early 0.95',
                       'check_setup -verbose',
                       'puts "BEGIN_ALL_MAX"',
                       'report_checks -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay max -group_path_count 10 -format full_clock_expanded -digits 9',
                       'puts "END_ALL_MAX"','puts "BEGIN_ALL_MIN"',
                       'report_checks -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay min -group_path_count 10 -format full_clock_expanded -digits 9',
                       'puts "END_ALL_MIN"']
                for net,pins in launch.items():
                    # Tcl list elements are individually braced: native $ names
                    # are literal, never expanded or simplified by an alias.
                    collection='[get_pins [list '+' '.join(q(p)for p in pins)+']]'
                    lines += ['puts "BEGIN_'+net+'_MAX"',
                              'report_checks -from '+collection+' -to [all_registers -data_pins] -path_delay max -group_path_count 10 -format full_clock_expanded -digits 9',
                              'puts "END_'+net+'_MAX"']
                lines+=['exit']
                (d/'analysis.tcl').write_text('\n'.join(lines)+'\n')
                with(d/'native.log').open('w')as log:code=subprocess.call([str(sta),'-exit',str(d/'analysis.tcl')],stdout=log,stderr=subprocess.STDOUT)
                text=(d/'native.log').read_text()
                assert code==0 and not re.search(r'(^|\n)Error[: ]|invalid command name|wrong # args',text),text[-12000:]
                results={}
                for tag in ['ALL_MAX','ALL_MIN']+[n+'_MAX'for n in launch]:
                    a='BEGIN_'+tag;b='END_'+tag
                    assert text.count(a)==1 and text.count(b)==1
                    body=text.split(a,1)[1].split(b,1)[0]
                    vals=[float(v)for v in re.findall(r'([-+]?[0-9]+(?:\.[0-9]+)?)\s+slack\s+\((?:MET|VIOLATED)\)',body)]
                    assert vals and len(vals)<=10,('No exact native timing values',tag,body)
                    results[tag]={'minimum_reported_slack_ns':min(vals),'reported_paths':len(vals),'report_sha256':digest(body.encode())}
                    (d/(tag+'.rpt')).write_text(body)
                r['measurements'][label][corner]=results;save()
        r['differences']={corner:{tag:r['measurements']['candidate'][corner][tag]['minimum_reported_slack_ns']-r['measurements']['baseline'][corner][tag]['minimum_reported_slack_ns']for tag in ['ALL_MAX','ALL_MIN','index_MAX']}for corner in libs}
        assert all(sha(p)==v for p,v in protected.items())
        r.update(status='COMPLETE_THREE_CORNER_ZERO_WIRE_COMPARISON_NOT_PHYSICAL_ACCEPTANCE',sources_unchanged=True,protected_inputs=protected)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
