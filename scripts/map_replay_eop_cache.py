#!/usr/bin/env python3
"""Actual identical-library mapping comparison; not a timing/layout verdict."""
import pathlib,json,subprocess,base64,hashlib,collections,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
P=pathlib.Path;out=P('out');native=out/'native';native.mkdir(parents=True)
rtl=P('hw/soc/rtl/pcie/soc_pcie_replay_tx.v')
assert hashlib.sha256(rtl.read_bytes()).hexdigest()=='e478d785013174a7a7ce63b6fcbd8aa609736e65e292748eb8c0311e453f69e8'
blob='9654b7cb685cf7d376b9842089ea2903540448e8'
r=json.loads(subprocess.check_output(['gh','api','repos/IHP-GmbH/IHP-Open-PDK/git/blobs/'+blob],timeout=60))
b=base64.b64decode(r['content']);assert hashlib.sha256(b).hexdigest()=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==blob
lib=native/'typ.lib';lib.write_bytes(b)
con=native/'abc.constr';con.write_text('set_driving_cell sg13g2_buf_4\nset_load 0.005\n')
report=dict(scope='Mapped isolated replay structural comparison only. Same typical Liberty, ABC constraints and RTL options. No placement, clocks, RC, STA or physical acceptance.',library_sha256=hashlib.sha256(b).hexdigest(),timing_accepted=False,cases={})
for label,extra in [('baseline',''),('cache','-D SOC_PCIE_REPLAY_EOP_CACHE')]:
    prefix=native/label
    flags='-D SOC_PCIE_REPLAY_WRITE_PREDECODE -D SOC_PCIE_REPLAY_AHEAD -D SOC_PCIE_REPLAY_INBANK -D SOC_PCIE_RESET_COPIES'
    ys=f"""read_liberty -lib {lib}
read_verilog -sv {flags} {extra} hw/soc/rtl/pcie/soc_pcie_crc32_byte.v {rtl}
hierarchy -check -top soc_pcie_replay_tx
synth -flatten -top soc_pcie_replay_tx -run begin:fine
techmap -map +/techmap.v -map +/choices/kogge-stone.v
synth -top soc_pcie_replay_tx -run fine
opt
dfflibmap -liberty {lib}
opt
abc -liberty {lib} -constr {con} -D 20
opt_clean
check -assert
write_json {prefix}.json
write_verilog -noattr -noexpr {prefix}.v
stat -liberty {lib}
"""
    (native/(label+'.ys')).write_text(ys)
    with (out/(label+'.log')).open('w') as f:
        r=subprocess.run(['yosys','-Q','-T','-s',str(native/(label+'.ys'))],stdout=f,stderr=subprocess.STDOUT,timeout=900)
    assert r.returncode==0,label
    d=json.loads((native/(label+'.json')).read_text())['modules']['soc_pcie_replay_tx']
    fanout=collections.Counter();types=collections.Counter();metadata=0
    for c in d['cells'].values():
        if c['type']=='$scopeinfo':
            assert not c['connections'] and not c['port_directions']
            metadata+=1
            continue
        types[c['type']]+=1
        for pin,bits in c['connections'].items():
            if c['port_directions'][pin]=='input':fanout.update(x for x in bits if isinstance(x,int))
    assert all(k.startswith('sg13g2_') for k in types),types
    selected={n:[fanout[b] for b in v['bits']] for n,v in d['netnames'].items() if n in ('write_valid','write_address','write_low','write_group','write_data')}
    assert 'write_group' in selected and 'write_low' in selected
    if label=='cache':
        aliases={n:v['bits'] for n,v in d['netnames'].items() if 'eop' in n.lower()}
        print('EOP aliases',json.dumps(aliases),flush=True)
        candidates=[v['bits'][0] for n,v in d['netnames'].items() if n in ('replay_eop_q','core_eop')]
        assert candidates,'Mapped EOP signal missing'
        drivers={}
        for cell in d['cells'].values():
            for pin,bits in cell['connections'].items():
                if cell['port_directions'][pin]=='output':
                    for bit in bits:drivers[bit]=cell
        def registered(bit,seen):
            assert bit not in seen,'Driver loop'
            cell=drivers[bit];kind=cell['type'];seen=seen|{bit}
            if kind.startswith('sg13g2_df'):return kind
            assert kind.startswith(('sg13g2_buf_','sg13g2_inv_')),kind
            return registered(cell['connections']['A'][0],seen)
        report['cached_eop_sequential_driver']=registered(candidates[0],set())
    report['cases'][label]=dict(nonphysical_zero_port_scopeinfo_records=metadata,cell_count=sum(types.values()),cell_types=dict(types),named_write_net_sink_pins=selected,netlist_sha256=hashlib.sha256((native/(label+'.v')).read_bytes()).hexdigest())
    (out/'mapping.json').write_text(json.dumps(report,indent=2)+'\n')
report['status']='MAPPED_BOTH_CANDIDATES_NOT_PHYSICAL_TIMING';(out/'mapping.json').write_text(json.dumps(report,indent=2)+'\n')
