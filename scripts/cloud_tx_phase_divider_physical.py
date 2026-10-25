#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cloud-only real quadrature-output prerequisite; never claims clock-tree closure."""
import ast,copy,hashlib,json,os,subprocess,sys,tarfile,traceback
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
from cloud_tx_exact_external_ports import compare as compare_ports
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-tx-phase-divider-physical'
TOP='nssoc_tx_phase_divider55_v1'

def clock_contract():
    source=ROOT/'scripts/run_cloud_tx_mux4.py'
    nodes=[n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='tree_plan']
    assert len(nodes)==1
    ns={'START':2e-9,'UI':125e-12};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),ns)
    plan=ns['tree_plan'](32);clocks=plan['clocks'];assert len(clocks)==31
    groups={}
    for c in clocks:
        half_ui=round(c['period']/125e-12);phase_ui=round((c['origin']-2e-9)/125e-12)
        assert abs(c['period']-half_ui*125e-12)<1e-22
        groups.setdefault(half_ui,[]).append(dict(name=c['name'],origin_ui=phase_ui,frequency_hz=1/(2*c['period'])))
    assert {k:len(v)for k,v in groups.items()}=={1:1,2:2,4:4,8:8,16:16}
    for k,rows in groups.items():
        actual=sorted(r['origin_ui']for r in rows)
        expected=[0]if k==1 else list(range(-(k.bit_length()-1),k-(k.bit_length()-1)))
        assert actual==expected
    return dict(source_sha256=sha(source),ui_s=125e-12,serial_rate=8e9,clock_pairs=31,half_period_units=groups,
      requirement='Physical divide-and-phase distribution plus selector-level drive; one shared divided signal is insufficient.',
      existing_reference_leaves=11,ideal_modulators_to_replace=62,schematic25ohm_accesses_to_replace=62,
      original_source_bit_and_sampling_gates_unchanged=True)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
    OUT.mkdir(parents=True,exist_ok=False)
    r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,full_phy_accepted=False,full_clock_tree_implemented=False,qualified_pex=False,phase_electrically_verified=False,steps={})
    def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    save()
    try:
        methods=json.loads((ROOT/'scripts/tx-phase-divider-physical-methods.json').read_text())
        assert all(sha(ROOT/p)==v for p,v in methods.items())
        r['clock_contract']=clock_contract();save()
        spec=json.loads((ROOT/'docs/evidence/pcie-tx-layout-cloud-input-20261013.json').read_text())
        packed=OUT/'fixture.tar.gz';fetch(spec['receipt']['url'],spec['receipt']['sha256'],packed)
        assert packed.stat().st_size==spec['receipt']['bytes']
        with tarfile.open(packed)as tar:tar.extractall(ROOT,filter='data')
        packed.unlink();manifest=json.loads((ROOT/'manifest.json').read_text())
        assert all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)==spec['runtime_sha256']=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from check_ihp_drc import record_result
        from prepare_ihp_drc import validate_lock,verify
        pins={ROOT/p:h for p,h in methods.items()};pins[app]=sha(app)
        for typ in ('drc','lvs'):
            lockpath=ROOT/f'hw/soc/pnr/ihp-{typ}.lock.json';lock=json.loads(lockpath.read_text());validate_lock(lock)
            assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6';pins[lockpath]=sha(lockpath)
            for row in lock['files']:
                p=ROOT/f'hw/soc/tools/ihp-{typ}-5e6d592'/row['path'];verify(p.read_bytes(),row);pins[p]=row['sha256']
        def execute(command,directory,label):
            log=directory/(label+'.log')
            with log.open('w')as f:code=subprocess.call(list(map(str,command)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
            if code:print(log.read_text(errors='replace')[-12000:],flush=True)
            return dict(returncode=code,log_sha256=sha(log))
        for name,generator in [('baseline','make_pcie_clock_div2_high_input_v1.py'),('layout','make_pcie_tx_phase_divider_v1.py')]:
            entry=execute([app,'python',ROOT/'hw/soc/flow'/generator,'--pdk',ROOT/'pdk','--out',OUT/name],OUT,'generate-'+name)
            r['steps']['generate_'+name]=entry;save();assert entry['returncode']==0
        entry=execute([app,'python',ROOT/'scripts/tx_phase_divider_native_geometry.py',OUT/'baseline',OUT/'layout',OUT/'geometry-audit.json'],OUT,'geometry-audit')
        r['steps']['geometry_audit']=entry;save();assert entry['returncode']==0
        r['geometry_audit']=json.loads((OUT/'geometry-audit.json').read_text())
        gds=OUT/'layout'/f'{TOP}.gds';reference=OUT/'layout/schematic.cir';generated=json.loads((OUT/'layout/result.json').read_text())
        assert set(generated['ports'])=={'CLKP','CLKN','QP','QN','MP','MN','DIV_AVDD','AVSS','SUB'}
        for name in ('drc','deep_lvs','flat_lvs','master_access_open','master_slave_short','wrong_feedback','wrong_seed','offgrid'):
            directory=OUT/name;directory.mkdir();physical=gds;schematic=reference;positive=name in ('drc','deep_lvs','flat_lvs')
            if name in ('master_access_open','master_slave_short','offgrid'):
                physical=directory/'wrong.gds';script=directory/'mutate.py'
                head='import pya\nl=pya.Layout();l.read('+repr(str(gds))+');c=l.cell('+repr(TOP)+')\n'
                if name=='master_access_open':
                    bb=generated['ports']['MP']['rect_um'];y=(bb[1]+bb[3])/2
                    body='i=l.layer(67,0);r=pya.Region(c.shapes(i));r-=pya.Region(pya.DBox(3,'+repr(y-1.1)+',4,'+repr(y+1.1)+').to_itype(l.dbu));c.shapes(i).clear();c.shapes(i).insert(r)\n'
                elif name=='master_slave_short':
                    ys=[sum(generated['ports'][k]['rect_um'][i]for i in (1,3))/2 for k in ('MP','QP')]
                    body='c.shapes(l.layer(67,0)).insert(pya.DBox(.5,'+repr(min(ys)-.5)+',1.5,'+repr(max(ys)+.5)+'))\n'
                else:body='c.shapes(l.layer(8,0)).insert(pya.DBox(1.001,1.001,1.101,1.101))\n'
                script.write_text(head+body+'l.write('+repr(str(physical))+')\n')
                assert execute([app,'python',script],directory,'mutate')['returncode']==0 and sha(physical)!=sha(gds)
            if name in ('wrong_feedback','wrong_seed'):
                text=reference.read_text();rows=text.splitlines()
                if name=='wrong_feedback':
                    match=[i for i,line in enumerate(rows)if line.startswith('QDIV__XSECOND__XM__XDP ')];assert len(match)==1
                    i=match[0];parts=rows[i].split();assert parts[2]=='QN';parts[2]='QP';rows[i]=' '.join(parts)
                else:
                    match=[i for i,line in enumerate(rows)if line.startswith('CDIV__XSECOND__XSEEDP ')];assert len(match)==1
                    i=match[0];assert rows[i].count('w=2.2u')==1;rows[i]=rows[i].replace('w=2.2u','w=2.4u')
                schematic=directory/'wrong.cir';schematic.write_text('\n'.join(rows)+'\n');assert sha(schematic)!=sha(reference)
            drc=name in ('drc','offgrid');kind='drc'if drc else'lvs'
            deck=ROOT/f'hw/soc/tools/ihp-{kind}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech'/kind/('ihp-sg13g2.drc'if drc else'sg13g2.lvs')
            options={'input':physical,'topcell':TOP,'log':directory/'deck.log','run_mode':'deep'if name=='deep_lvs'or drc else'flat'}
            if drc:options.update(report=directory/'drc.lyrdb',threads=2,no_recommended='False',precheck_drc='False')
            else:options.update(schematic=schematic,report=directory/'result.lvsdb',target_netlist=directory/'extracted.cir',thr=2,no_simplify='true',top_lvl_pins='true',combine_devices='false')
            command=[app,'klayout','-b','-zz','-r',deck]
            for k,v in options.items():command+=['-rd',str(k)+'='+str(v)]
            e=execute(command,directory,'run');assert e['returncode']==0
            step=dict(execution=e,positive=positive)
            if drc:
                result=record_result(directory,TOP,0,pins);step['measurement']=result
                assert result['category_count']==560
                if positive:assert result['status']=='PASS'and result['markers']==0
                else:assert result['status']=='FAIL'and result['categories'].get('metal1_drw_Offgrid',0)>0
            else:
                audit=directory/'audit.json';e=execute([app,'python',ROOT/'hw/soc/flow/audit_klayout_lvs.py',directory/'result.lvsdb','--top',TOP,'--deck-log',directory/'deck.log','--output',audit],directory,'audit')
                result=json.loads(audit.read_text());step['audit']=result;step['audit_execution']=e
                assert not result['extraction_diagnostics']
                if positive:
                    assert e['returncode']==0 and result['status']=='PASS within comparison scope'
                    assert result['circuits'][0]['layout_devices_recursive']==result['circuits'][0]['schematic_devices_recursive']==55
                    step['ports']=compare_ports(reference.read_text(),(directory/'extracted.cir').read_text(),TOP,expected_count=9);assert step['ports']['passed']
                else:assert e['returncode']==1 and result['status']=='FAIL'
            step['expected_verdict_observed']=True;r['steps'][name]=step;save()
        assert all(sha(p)==h for p,h in pins.items())and all(sha(ROOT/n)==v['sha256']for n,v in manifest['files'].items())
        r.update(status='PASS_NATIVE55_PHASE_OUTPUTS_DRC_DEEP_FLAT_LVS_AND_FIVE_FAULTS_REQUIRES_LOADED_PHASE_AND_FRESH_RC',sources_unchanged=True)
    except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
