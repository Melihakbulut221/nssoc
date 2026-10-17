#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Inventory exact routed timing coverage gaps; no constraint change or waiver."""
import json,os
from collections import Counter
from pathlib import Path
import compare_cloud_routed_endpoints as reports
from run_cloud_tx_layout_repair import sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-routed-coverage-gaps'

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    OUT.mkdir(exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
        final_timing_complete=False,constraints_changed=False,new_sta_execution=False,
        scope='Read-only exact native endpoint census from routed freshRC38992990610. Lexical groups identify affected hierarchy, not causes or authorized false paths. No signoff or timing closure inferred.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        source,proof=reports.restore_report('ethernet-compatible-rc',38992990610,
            '40ef6346436194693fea5797abbec711be536a28341fd177d81c3166b47226c1',
            '9987410d8eac9ec94c53ee3d2bfed3643bde1281098b142bdeede27e2bb80858',
            OUT/'source',('routed-census/native-census.json','routed-census/endpoint-slacks.tsv','routed-census/native-graph-coverage.json','fresh-routed-sta.tcl'))
        assert source['status']=='COMPLETE_PIN_COMPATIBLE_ETHERNET_ROUTES_FRESH_RC_ALL_ENDPOINTS_NOT_SIGNOFF'and source['source_unchanged']
        record,rows=reports.load_census(OUT/'source/routed-census')
        assert record['engine_endpoint_count']==22544 and len(rows)==135264
        graph=json.loads((OUT/'source/routed-census/native-graph-coverage.json').read_text())
        assert graph==source['graph_coverage']['native_report']
        assert not graph['mismatches']and not graph['original_guard_failures']
        mapping=record['native_pin_mapping'];corners=record['corners'];coverage={}
        for delay,expected in [('max',1072),('min',1117)]:
            missing={corner:{name for name in record['endpoints']if rows[corner,delay,name][2]is None}for corner in corners}
            common=set.intersection(*missing.values());union=set.union(*missing.values())
            assert all(v==common for v in missing.values())and len(common)==expected
            native=next(c for c in graph['checks']if c['delay']==delay)
            assert native['endpoints']==22544 and native['constrained']==22544-len(common)
            details=[]
            for name in sorted(common):
                pin=mapping[name]
                assert pin['kind']in ('instance','boundary')
                lexical='BOUNDARY'if pin['kind']=='boundary'else '.'.join(pin['instance'].split('.')[:3])
                opposite='min'if delay=='max'else'max'
                details.append(dict(endpoint=name,physical_pin=pin,lexical_group=lexical,
                    opposite_delay_slacks_seconds={c:rows[c,opposite,name][2]for c in corners}))
            counts=Counter(d['lexical_group']for d in details)
            coverage[delay]=dict(unconstrained_all_corners=len(common),unconstrained_any_corner=len(union),
                by_pin_kind=dict(Counter(d['physical_pin']['kind']for d in details)),
                lexical_groups=dict(sorted(counts.items(),key=lambda v:(-v[1],v[0]))),endpoints=details,
                cause='UNRESOLVED: requires actual clock/arrival/exception/cone evidence; names alone are insufficient')
        missing_min={d['endpoint']for d in coverage['min']['endpoints']}
        missing_max={d['endpoint']for d in coverage['max']['endpoints']}
        result['coverage_intersection']=dict(both=sorted(missing_min&missing_max),hold_only=sorted(missing_min-missing_max),setup_only=sorted(missing_max-missing_min))
        setup={}
        for c in corners:
            ordered=sorted((rows[c,'max',n][2],n)for n in record['endpoints']if rows[c,'max',n][2]is not None)
            setup[c]=dict(negative=sum(v<0 for v,n in ordered),worst_seconds=ordered[0][0],
                worst32=[dict(endpoint=n,slack_seconds=v,physical_pin=mapping[n])for v,n in ordered[:32]])
        assert all(sha(OUT/'source'/n)==v['sha256']for n,v in proof['restore']['selected_files'].items())
        result.update(status='COMPLETE_EXACT_ROUTED_COVERAGE_GAP_INVENTORY_NOT_TIMING_ACCEPTANCE',source=proof,
            native_graph_checks=graph['checks'],coverage=coverage,setup=setup,source_unchanged=True)
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:result[k]for k in ('status','accepted','constraints_changed')}),flush=True)
if __name__=='__main__':main()
