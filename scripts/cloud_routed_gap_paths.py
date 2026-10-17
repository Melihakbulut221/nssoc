#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only native clock/path diagnostics for connected routed coverage gaps."""
import argparse,json,os,re,subprocess,tarfile
from collections import Counter
from pcie_soc_constraints import clock_port_delay_cleanup
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from route_cloud_newer_postcts import fetch,sha
from read_opensta_phase_slacks import parse_phases
from native_graph_path_coverage import verify as verify_graph
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-routed-gap-paths'
SOURCE=ROOT/'cloud-routed-extraction'

def main(clock_cleanup=False):
    global OUT
    if clock_cleanup:OUT=ROOT/'cloud-clock-port-delay'
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,constraints_changed=clock_cleanup,clock_cleanup=clock_cleanup,
        scope='Exact original SDC/libraries/native routed ODB/SPEF. Optional explicit clock-port cleanup removes only four inherited data-delay records, with all other effective constraints compared unchanged. No new false paths or generated clocks. This is not full timing closure or functional/CDC proof.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        conn,cp=reports.restore_report('routed-gap-connectivity',38999476919,
            '12e090a480943b60b0ff3d4e6c87aa35cb4bb02c7fcd0562ef234d97e70440ee',
            'e9fac871fcdb670119d23b54803c446b9a3ac61c7f50e8b2a007f4a48d413eee',OUT/'connectivity',('native-connectivity.json',))
        assert conn['status']=='COMPLETE_ROUTED_GAP_NATIVE_CONNECTIVITY_NOT_TIMING_ACCEPTANCE'and conn['source_unchanged']
        detail=json.loads((OUT/'connectivity/native-connectivity.json').read_text())
        targets=[d for d in detail['coverage']['min']['endpoints']if d['direction']=='INPUT'or d['classification']=='output_with_loads']
        assert len(targets)==55 and len({d['endpoint']for d in targets})==55
        source,sp=reports.restore_report('ethernet-compatible-rc',38992990610,
            '40ef6346436194693fea5797abbec711be536a28341fd177d81c3166b47226c1',
            '9987410d8eac9ec94c53ee3d2bfed3643bde1281098b142bdeede27e2bb80858',OUT/'source',('routed.odb','candidate.nominal.spef','fresh-routed-sta.tcl','routed-census/native-census.json','routed-census/endpoint-slacks.tsv'))
        assert source['candidate_odb_sha256']==detail['odb_sha256']and source['source_unchanged']
        fetch(reports.BASE+'.summary.json',reports.SUMMARY_SHA,OUT/'original-summary.json');original_result=json.loads((OUT/'original-summary.json').read_text())
        packed=OUT/'original.tar.gz';fetch(reports.BASE+'.tar.gz.part0000',reports.ARCHIVE_SHA,packed)
        assert packed.stat().st_size==225682086 and not SOURCE.exists()
        with tarfile.open(packed)as archive:
            for m in archive:
                p=Path(m.name);assert not p.is_absolute()and'..'not in p.parts and p.parts[0]==SOURCE.name and(m.isfile()or m.isdir())
                archive.extract(m,ROOT,filter='data')
        packed.unlink();assert sha(SOURCE/'result.json')==reports.SUMMARY_SHA
        assert all(sha(SOURCE/n)==v for n,v in original_result['outputs'].items())
        assert all(sha(Path(n))==v for n,v in original_result['protected_inputs'].items())
        original=(SOURCE/'actual-routed-sta.tcl').read_text()
        prior=original.replace(str(SOURCE/'source/routed.odb'),str(ROOT/'cloud-ethernet-compatible-rc/routed.odb')).replace(str(SOURCE/'actual-route.nominal.spef'),str(ROOT/'cloud-ethernet-compatible-rc/candidate.nominal.spef'))
        assert prior==(OUT/'source/fresh-routed-sta.tcl').read_text()
        actual=original.replace(str(SOURCE/'source/routed.odb'),str(OUT/'source/routed.odb')).replace(str(SOURCE/'actual-route.nominal.spef'),str(OUT/'source/candidate.nominal.spef'))
        # Name fields are original native identities, never glob patterns.
        lines=[]
        for d in targets:
            p=d['physical_pin'];assert p['kind']=='instance'
            row=[d['endpoint'],p['instance'],p['pin']]
            assert all(not any(c in v for c in '\t\r\n')for v in row)
            lines.append('\t'.join(row))
        (OUT/'targets.tsv').write_text('\n'.join(lines)+'\n')
        diagnostic=r"""
set target_names {}
set tf [open TARGET_FILE r]
while {[gets $tf row]>=0} {
    set fields [split $row \t]
    if {[llength $fields]!=3} {error "Malformed target identity"}
    lassign $fields name instance term
    if {[dict exists $target_names $name]} {error "Duplicate target identity"}
    dict set target_names $name [list $instance $term]
}
close $tf
if {[dict size $target_names]!=55} {error "Target census differs"}
set target_pins {}
foreach pin [sta::endpoints] {
    set name [get_property $pin full_name]
    if {![dict exists $target_names $name]} {continue}
    set iterm [sta::sta_to_db_pin $pin]
    if {$iterm eq "NULL"} {error "Expected exact instance terminal"}
    set identity [list [[$iterm getInst] getName] [[$iterm getMTerm] getName]]
    if {$identity ne [dict get $target_names $name]} {error "Native physical identity mismatch"}
    dict set target_pins $name $pin
}
if {[lsort [dict keys $target_pins]] ne [lsort [dict keys $target_names]]} {error "Missing native target"}
puts NSSOC_GAP_CLOCKS_BEGIN
report_clock_properties
puts NSSOC_GAP_CLOCKS_END
write_sdc -no_timestamp -digits 12 EFFECTIVE_SDC
puts NSSOC_GAP_DISABLED_EDGES_BEGIN
report_disabled_edges
puts NSSOC_GAP_DISABLED_EDGES_END
set index 0
foreach name [lsort [dict keys $target_pins]] {
    set pin [dict get $target_pins $name]
    puts "NSSOC_GAP_TARGET_BEGIN $index $name"
    foreach corner {fast typical slow} {
        foreach delay {min max} {
            puts "NSSOC_GAP_PATH_BEGIN $index $corner $delay"
            report_checks -to [list $pin] -corner $corner -path_delay $delay -unconstrained -group_path_count 2 -endpoint_path_count 2 -format full_clock_expanded -fields {slew capacitance fanout input_pin net} -digits 12
            puts "NSSOC_GAP_PATH_END $index $corner $delay"
        }
    }
    puts "NSSOC_GAP_TARGET_END $index"
    incr index
}
puts "NSSOC_GAP_DIAGNOSTIC_COMPLETE $index"
"""
        diagnostic=diagnostic.replace('TARGET_FILE','{'+str(OUT/'targets.tsv')+'}').replace('EFFECTIVE_SDC','{'+str(OUT/'effective.sdc')+'}')
        cleanup=''
        if clock_cleanup:
            cleanup='write_sdc -no_timestamp -digits 12 {'+str(OUT/'before-cleanup.sdc')+'}\n'+'\n'.join(clock_port_delay_cleanup())+'\n'
        if clock_cleanup:
            helper=ROOT/'hw/soc/pnr/timing_hold_reproducibility.tcl'
            method=ROOT/'hw/soc/pnr/routed_endpoint_census.tcl'
            graph=ROOT/'hw/soc/pnr/native_graph_path_coverage.tcl'
            assert sha(helper)==reports.HELPER_SHA and sha(method)==reports.CENSUS_METHOD_SHA
            directory=OUT/'routed-census';directory.mkdir()
            diagnostic+=f'\nsource {{{helper}}}\nsource {{{graph}}}\nset nssoc_endpoint_out {{{directory}}}\nsource {{{method}}}\nnssoc_graph_finish {{{directory/"native-graph-coverage.json"}}}\n'
        path=OUT/'diagnostic.tcl';path.write_text(actual+'\n'+cleanup+diagnostic)
        result.update(connectivity_source=cp,routed_source=sp,original_runtime_source=dict(summary_sha256=reports.SUMMARY_SHA,archive_sha256=reports.ARCHIVE_SHA),targets=targets);save()
        runtime=Path(os.environ['CLOUD_APPIMAGE']);assert sha(runtime)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
        with(OUT/'diagnostic.log').open('w')as log:
            proc=subprocess.Popen([str(runtime),'openroad','-exit',str(path)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            for line in proc.stdout:log.write(line);log.flush();print(line,end='',flush=True)
            code=proc.wait()
        text=(OUT/'diagnostic.log').read_text(errors='replace')
        assert code==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(code,text[-3000:])
        # Extra targeted path reports are outside the original phase groups.
        # Keep the parser strict within its original output rather than feeding
        # the added diagnostic paths into the last original timing phase.
        assert text.count('NSSOC_GAP_CLOCKS_BEGIN')==1
        phases=parse_phases(text.split('NSSOC_GAP_CLOCKS_BEGIN',1)[0],'CORNER')
        for k,v in source['routed_timing'].items():assert phases[k]['groups']==v['groups'],k
        assert text.count('NSSOC_GAP_DIAGNOSTIC_COMPLETE 55')==1
        begins=re.findall(r'^NSSOC_GAP_PATH_BEGIN (\d+) (fast|typical|slow) (min|max)$',text,re.M)
        ends=re.findall(r'^NSSOC_GAP_PATH_END (\d+) (fast|typical|slow) (min|max)$',text,re.M)
        assert begins==ends and len(begins)==330 and len(set(begins))==330
        assert (OUT/'effective.sdc').stat().st_size>0
        if clock_cleanup:
            # Compare every effective command; only four known wrong data
            # delays may disappear. Every other I/O budget/clock/exception stays.
            def commands(path):
                text=path.read_text().replace('\\\n','')
                return Counter(line.strip()for line in text.splitlines()if line.strip()and not line.lstrip().startswith('#'))
            before=commands(OUT/'before-cleanup.sdc');after=commands(OUT/'effective.sdc')
            removed=list((before-after).elements());added=list((after-before).elements())
            expected={
                'set_input_delay 4.000000000000 -clock [get_clocks {clk_i}] -add_delay [get_ports {'+p+'}]'
                for p in ('pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i')}
            expected.add('set_output_delay 4.000000000000 -clock [get_clocks {clk_i}] -add_delay [get_ports {eth_gtx_clk_o}]')
            assert set(removed)==expected and len(removed)==4 and not added,(removed,added)
            result['clock_cleanup_effective_delta']=dict(removed=removed,added=added,all_other_commands_unchanged=True,
                original_clock_unqualified_unset_failed=True,explicit_clock_unset_passed=True)
        if clock_cleanup:
            before,old_rows=reports.load_census(OUT/'source/routed-census')
            after,new_rows=reports.load_census(OUT/'routed-census')
            result['post_cleanup_native_graph']=verify_graph(OUT/'routed-census',after)
            old_names=set(before['endpoints']);new_names=set(after['endpoints']);common=old_names&new_names
            assert all(before['native_pin_mapping'][n]==after['native_pin_mapping'][n]for n in common)
            shared=set(old_rows)&set(new_rows)
            result['post_cleanup_timing']=dict(endpoint_count=after['engine_endpoint_count'],rows=len(new_rows),
                common_endpoint_count=len(common),added_endpoints=sorted(new_names-old_names),removed_endpoints=sorted(old_names-new_names),
                negative_endpoint_count=after['negative_endpoint_count'],native_wns_seconds=after['native_wns_seconds'],
                shared_rows_comparison=reports.compare_rows({k:old_rows[k]for k in shared},{k:new_rows[k]for k in shared}),
                acceptance='NOT_FINAL_TIMING: exact native census after four clock-port data-delay removals; unchanged physical ODB/SPEF, no new routing. Setup/coverage/qualifiedRC/functional CDC and full PHY remain required.')
        for directory,proof in [(OUT/'source',sp),(OUT/'connectivity',cp)]:assert all(sha(directory/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        assert all(sha(SOURCE/n)==v for n,v in original_result['outputs'].items())and all(sha(Path(n))==v for n,v in original_result['protected_inputs'].items())
        result.update(status='COMPLETE_EXACT_ROUTED_GAP_PATH_DIAGNOSTIC_NOT_TIMING_ACCEPTANCE',source_unchanged=True,original_timing_reproduced=True,queries=len(begins),target_count=55,
            effective_sdc_sha256=sha(OUT/'effective.sdc'),diagnostic_log_sha256=sha(OUT/'diagnostic.log'))
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--clock-cleanup',action='store_true');main(p.parse_args().clock_cleanup)
