#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove an EOP-owner ready refinement on the actual physical packet arbiter."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-advert-eop'
URL='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38472422176-1-ack-map-physical_idle_credit/ack-map-physical_idle_credit-38472422176-1.tar.gz'
ARCHIVE_SHA='ed43f52d14422ffb15c450350b5b697b61031ff50cee16d1e051a3e4374aa2be'
PARENT_SHA='459d69ddaf287004099f91edf1d0c57d35fd324edf4fa9838cb994d398dd2509'
FC_SHA='599755ec5824cdea24379dbac7de7eff20cb5dd738cc4f4fd2767c8ddf73b904'
OLD='    assign advert_ready=local_reset && !chosen && selected_ready;'
NEW='    assign advert_ready=local_reset && selected_ready && (advert_eop ? (locked && !owner) : !chosen);'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def candidate(text):
    assert text.count(OLD)==1
    return text.replace(OLD,NEW)

def region(parent,fc,name,refresh,gate=False):
    # Copy the exact producer, arbitration and output register region.
    # Other packet/RX modules are replaced by unconstrained boundary inputs:
    # proof therefore allows every request, backpressure, credit and link trace.
    begin=parent.index('    soc_pcie_fc_tx #(')
    end=parent.index('    // END_REGISTERED_TX_EGRESS')+len('    // END_REGISTERED_TX_EGRESS')
    body=parent[begin:end]
    reset=re.findall(r'^\s*wire local_reset\s*=\s*(.+);',parent,re.M)
    assert len(reset)==1 and re.sub(r'\s','',reset[0])=='rst_ni&&link_up_i&&!retrain_done_i',reset
    header="""module NAME (
    input wire clk_i,rst_ni,link_up_i,training_i,retrain_done_i,
    input wire peer_init1_done_o,peer_init2_seen_o,
    input wire [23:0] rx_header_limit_o,
    input wire [35:0] rx_data_limit_o,
    input wire [7:0] flow_data,
    input wire flow_sop,flow_eop,flow_valid,flow_dllp,flow_replay,tx_ready_i,
    output wire local_init_done_o,local_init2_sent_o,fc_sent_o,
    output wire [23:0] fc_sent_header_o,
    output wire [35:0] fc_sent_data_o,
    output wire [1:0] fc_sent_phase_o,fc_sent_class_o,
    output wire [7:0] tx_data_o,
    output wire tx_sop_o,tx_eop_o,tx_valid_o,tx_dllp_o,tx_replay_o,
    output wire flow_ready
);
    localparam integer FC_REFRESH_CYCLES=REFRESH;
    wire local_reset=rst_ni && link_up_i && !retrain_done_i;
    wire [7:0] advert_data;
    wire advert_sop,advert_eop,advert_valid,advert_ready;
""".replace('NAME',name).replace('REFRESH;',str(refresh)+';')
    declaration='module soc_pcie_fc_tx #('
    assert fc.count(declaration)==1
    fc=fc.replace(declaration,'module '+name+'_fc #(')
    body=body.replace('soc_pcie_fc_tx #(',name+'_fc #(')
    if gate:
        # Ready may differ on an unoffered byte; it is internal, not an output.
        # Avoid matching that intentionally refined internal alias in equiv_make.
        header=re.sub(r'\badvert_ready\b','eop_ready',header)
        body=re.sub(r'\badvert_ready\b','eop_ready',body)
        fc=re.sub(r'\btx_ready_i\b','gate_ready_i',fc)
        body=body.replace('.tx_ready_i(eop_ready)','.gate_ready_i(eop_ready)')
    return fc+'\n'+header+body+'\nendmodule\n'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False)
    record=dict(status='RUNNING',adopted=False,production_rtl_modified=False,
        scope='Actual advertiser/arbiter/registered-egress region, every output including invalid payload, explicit clock/asynchronous reset, arbitrary boundary requests. Full frozen physical buffered port tests and bad-owner control. Not mapped timing, routed chip or PHY acceptance.')
    def save():
        (OUT/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    def execute(command,label,cwd=None):
        with (OUT/(label+'.log')).open('w') as stream:
            code=subprocess.call(list(map(str,command)),cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
        return code,(OUT/(label+'.log')).read_text(errors='replace')
    try:
        packed=OUT/'source.tar.gz'
        subprocess.run(['curl','--fail','--location','--retry','4',URL,'-o',str(packed)],check=True)
        assert packed.stat().st_size==16843323 and sha(packed)==ARCHIVE_SHA
        prefix='cloud-ack-map/physical_idle_credit/'
        selected={};pins={}
        with tarfile.open(packed) as tar:
            source=json.load(tar.extractfile(prefix+'result.json'))
            assert source['status']=='COMPLETE_UNPLACED_SCREEN_NOT_TIMING_CLOSURE'
            for original,pin in source['physical_source_binding']['selected'].items():
                name=Path(original).name
                if not name.startswith('soc_pcie_') or not name.endswith('.v'):
                    continue
                member=pin['path'].split('/nssoc/nssoc/',1)[1]
                raw=tar.extractfile(member).read()
                assert hashlib.sha256(raw).hexdigest()==pin['sha256']
                assert name not in selected
                selected[name]=raw;pins[name]=dict(member=member,sha256=pin['sha256'])
            for name,digest in [
                ('soc_pcie_replay_tx.v','1bfa8971728d65ec2cfad2337d083298d7bcec8e56ce1fe4dc19f38fbcaa2edc'),
                ('soc_pcie_credit_tx.v','7fc31891f0ae48a8df5247b6df72388ff12cf2603de9f9dc9654b30a0256d38a')]:
                member=prefix+'candidate-'+name
                raw=tar.extractfile(member).read()
                assert hashlib.sha256(raw).hexdigest()==digest
                selected[name]=raw;pins[name]=dict(member=member,sha256=digest)
        packed.unlink()
        assert len(selected)==21
        name='soc_pcie_buffered_flow_packets.v'
        assert pins[name]['sha256']==PARENT_SHA
        assert pins['soc_pcie_fc_tx.v']['sha256']==FC_SHA
        original=selected[name].decode();altered=candidate(original)
        assert altered.count('(locked && !owner)')==1
        wrong=altered.replace('(locked && !owner)','(locked && owner)')
        dirs={}
        for case,text in [('baseline',original),('candidate',altered),('wrong_owner',wrong)]:
            directory=OUT/(case+'-rtl');directory.mkdir()
            for filename,raw in selected.items():(directory/filename).write_bytes(raw)
            (directory/name).write_text(text);dirs[case]=directory
        record['source_binding']=dict(archive_url=URL,archive_sha256=ARCHIVE_SHA,selected=pins,
            source_sha256=PARENT_SHA,candidate_sha256=sha(dirs['candidate']/name),
            negative_sha256=sha(dirs['wrong_owner']/name))
        yosys=shutil.which('yosys');iverilog=shutil.which('iverilog')
        assert yosys and iverilog
        record['proofs']=[]
        fc=selected['soc_pcie_fc_tx.v'].decode()
        for case,text,refresh in [('candidate',altered,128),('candidate_refresh0',altered,0),('candidate_refresh1',altered,1),('wrong_owner',wrong,128)]:
            directory=OUT/('proof-'+case);directory.mkdir()
            (directory/'gold.v').write_text(region(original,fc,'gold',refresh))
            (directory/'gate.v').write_text(region(text,fc,'gate',refresh,True))
            (directory/'crc.v').write_bytes(selected['soc_pcie_crc16_byte.v'])
            (directory/'proof.ys').write_text('\n'.join([
                'read_verilog -sv crc.v gold.v gate.v','hierarchy -check',
                'proc','memory_map','opt','flatten gold gate','opt',
                'clk2fflogic','opt','equiv_make gold gate equiv','hierarchy -top equiv',
                'equiv_simple','equiv_induct -seq 12','equiv_status -assert','']))
            code,log=execute([yosys,'-s','proof.ys'],'proof-'+case,directory)
            counts=re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven',log)
            passed=code==0 and len(counts)==1 and int(counts[0][0])>0 and int(counts[0][1])==0 and 'Equivalence successfully proven!' in log
            rejected=code!=0 and bool(counts) and int(counts[-1][1])>0
            record['proofs'].append(dict(case=case,refresh_cycles=refresh,returncode=code,counts=counts,
                passed=passed,negative_rejected=rejected,log_sha256=sha(OUT/('proof-'+case+'.log')),
                unproven=[line for line in log.splitlines() if 'Unproven' in line][-60:]))
            save()
        record['ports']=[]
        for case in ['baseline','candidate','wrong_owner']:
            out=OUT/('ports-'+case)
            code,log=execute([sys.executable,ROOT/'scripts/check_pcie_rx_flow.py',
                '--top','soc_pcie_buffered_flow_packets','--out',out,
                '--rtl-dir',dirs[case],'--iverilog-dir',Path(iverilog).parent],'ports-'+case)
            result=json.loads((out/'result.json').read_text())
            from cocotb_results import count_results
            xml=out/'results.xml';assert xml.is_file()
            passed,failed,skipped=count_results([xml])
            record['ports'].append(dict(case=case,returncode=code,result=result,
                actual_tests=dict(passed=passed,failed=failed,skipped=skipped),xml_sha256=sha(xml)));save()
            assert skipped==0 and passed+failed==result['expected_tests']
            if case=='wrong_owner':
                assert code!=0 and failed>0 and 'AssertionError' in (out/'simulation.log').read_text(errors='replace')
            else:
                assert code==0 and failed==0 and result['status']=='PASS_PORT_ONLY_PCIE_RX_FLOW'
        assert all(p['passed'] for p in record['proofs'][:3]) and record['proofs'][3]['negative_rejected']
        record['status']='PASS_ACTUAL_ADVERTISER_ARBITER_REGION_EQUIVALENCE_AND_BUFFERED_PORTS_NOT_TIMING'
    except BaseException as error:
        record.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        save()

if __name__=='__main__':
    main()
