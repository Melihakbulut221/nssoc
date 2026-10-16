#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Validate exact graph coverage and reproduce native selection, not a tolerance gate."""
import argparse,copy,json,math,os,struct,subprocess,tempfile
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha
REV='857316ff001b2a8dbbdc5996944d08a6d38c87ab'
SOURCES={
 'util/Fuzzy.cc':'6994742a570428caba13dae80d6293c3da9d7658f6762ed013c4a6cc5fc7c26c',
 'include/sta/Fuzzy.hh':'d2d2b15c94ab2bd5b5bc85db0a56bb62be7756a78d6214f6a62d945a4e071ac2',
 'include/sta/MinMax.hh':'88e2b4b6b2b4246f88fbb7b905a9e1daee1016897ed640f23f678d21788b7843',
 'include/sta/Iterator.hh':'89a17969378e841c794aa88fd58008ce69d2feae34915e39206740b53fd7b6dc',
}
DRIVER=r'''#include <iostream>
#include <iomanip>
#include "Fuzzy.hh"
int main() {
  float a, b;
  while (std::cin >> a >> b)
    std::cout << std::setprecision(17) << double(a) << " " << double(b) << " "
              << sta::fuzzyEqual(a,b) << " " << sta::fuzzyLess(a,b) << "\n";
  return std::cin.eof() ? 0 : 1;
}
'''
def build(directory):
    directory.mkdir(exist_ok=False)
    for path,digest in SOURCES.items():
        fetch('https://raw.githubusercontent.com/The-OpenROAD-Project/OpenSTA/'+REV+'/'+path,digest,directory/Path(path).name)
    source=directory/'driver.cc';source.write_text(DRIVER)
    binary=directory/'native-selection'
    command=['g++','-std=c++17','-O2','-fno-fast-math','-ffp-contract=off','-ffunction-sections','-fdata-sections','-Wl,--gc-sections','-I',str(directory),str(source),str(directory/'Fuzzy.cc'),'-o',str(binary)]
    p=subprocess.run(command,capture_output=True,text=True)
    (directory/'build.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
    return binary,dict(revision=REV,sources=SOURCES,command=command,driver_sha256=sha(source),executable_sha256=sha(binary))

def run_pairs(binary,pairs):
    p=subprocess.run([str(binary)],input=''.join(f'{a:.17g} {b:.17g}\n' for a,b in pairs),capture_output=True,text=True,check=True)
    rows=[line.split() for line in p.stdout.splitlines()];assert len(rows)==len(pairs)
    answer=[]
    for (a,b),row in zip(pairs,rows):
        assert len(row)==4 and float(row[0])==a and float(row[1])==b,'Native binary32 roundtrip changed'
        assert row[2] in ('0','1') and row[3] in ('0','1')
        answer.append(dict(a_seconds=a,b_seconds=b,fuzzy_equal=row[2]=='1',fuzzy_less=row[3]=='1'))
    return answer

def validate(report,meta,binary):
    assert report['status']=='COMPLETE_EXACT_GRAPH_PATH_COVERAGE_REQUIRES_NATIVE_SELECTION_CHECK'
    assert report['accepted'] is False and report['value_units']=='seconds'
    names=meta['endpoints'];assert len(names)==len(set(names))==meta['engine_endpoint_count']>0
    checks=report['checks'];assert len(checks)==2 and {x['delay'] for x in checks}=={'min','max'}
    for row in checks:
        assert row['endpoints']==len(names) and 0<row['constrained']<=len(names)
        assert row['raw_graph_paths']>=row['constrained']
        assert row['graph_minimum_exactly_equals_pathend_minimum'] is True
        assert row['negative']==meta['negative_endpoint_count'][row['delay']]
    failures=report['original_guard_failures'];mismatches=report['mismatches'];seen=set();pairs=[]
    for row in mismatches:
        key=(row['delay'],row['endpoint']);assert key not in seen and key[0] in ('min','max') and key[1] in names;seen.add(key)
        a=row['graph_minimum_seconds'];b=row['vertex_seconds']
        assert math.isfinite(a) and math.isfinite(b) and abs(a)<1e20 and abs(b)<1e20
        assert a<b and (a<0)==(b<0) and b==row['native_chosen_path_seconds']
        assert row['native_chosen_path_transition'] in ('rise','fall') and row['native_chosen_path_tag'] and row['raw_graph_paths']>1
        pairs.append((a,b))
    assert len({x['delay'] for x in failures})==len(failures)
    assert {x['delay'] for x in failures}=={x[0] for x in seen}
    for failure in failures:
        prefix='Unsupported native vertex-versus-PathEnd slack semantics: '
        assert failure['error'].startswith(prefix)
        assert (failure['delay'],failure['error'][len(prefix):]) in seen
    native=run_pairs(binary,pairs)
    assert all(x['fuzzy_equal'] and not x['fuzzy_less'] for x in native),'Native source does not explain chosen slack'
    return dict(status='PASS_EXACT_GRAPH_MINIMA_AND_NATIVE_SELECTION_NOT_TIMING_ACCEPTANCE',accepted=False,endpoint_delay_checks=2*len(names),exact_minimum_equality=True,original_guard_failures_preserved=failures,native_selection=native)

def controls(binary):
    a=1.4382139035262753e-08;b=1.438214791704695e-08
    m={'engine_endpoint_count':1,'endpoints':['a/D'],'negative_endpoint_count':{'min':0,'max':0}}
    r={'status':'COMPLETE_EXACT_GRAPH_PATH_COVERAGE_REQUIRES_NATIVE_SELECTION_CHECK','accepted':False,'value_units':'seconds','checks':[dict(delay=d,endpoints=1,constrained=1,raw_graph_paths=2,negative=0,graph_minimum_exactly_equals_pathend_minimum=True) for d in ('min','max')],'mismatches':[dict(delay='max',endpoint='a/D',graph_minimum_seconds=a,vertex_seconds=b,native_chosen_path_seconds=b,native_chosen_path_transition='rise',native_chosen_path_tag='source-bound control',raw_graph_paths=2)],'original_guard_failures':[dict(delay='max',error='Unsupported native vertex-versus-PathEnd slack semantics: a/D')]}
    validate(r,m,binary)
    faults=[]
    for field,value in [('graph_minimum_seconds',1e-9),('graph_minimum_seconds',-1e-16),('native_chosen_path_seconds',a),('endpoint','other/D'),('raw_graph_paths',1),('native_chosen_path_transition','unknown')]:
        x=copy.deepcopy(r);x['mismatches'][0][field]=value;faults.append(x)
    x=copy.deepcopy(r);x['checks'].pop();faults.append(x)
    x=copy.deepcopy(r);x['checks'][0]['endpoints']=2;faults.append(x)
    x=copy.deepcopy(r);x['checks'][0]['negative']=1;faults.append(x)
    x=copy.deepcopy(r);x['checks'][0]['graph_minimum_exactly_equals_pathend_minimum']=False;faults.append(x)
    x=copy.deepcopy(r);x['mismatches']*=2;faults.append(x)
    x=copy.deepcopy(r);x['original_guard_failures']=[];faults.append(x)
    x=copy.deepcopy(r);x['original_guard_failures'][0]['error']='Finite native endpoint omitted';faults.append(x)
    for bad in faults:
        try:validate(bad,m,binary)
        except AssertionError:continue
        raise AssertionError('Corrupt graph coverage accepted')
    assert run_pairs(binary,[(a,b)])[0]['fuzzy_equal']
    return dict(valid_native_case=1,malformed_cases_rejected=len(faults),exact_minimum_gate_unchanged=True)

def verify(directory,meta):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    binary,build_receipt=build(directory/'native-selection-source')
    report=json.loads((directory/'native-graph-coverage.json').read_text())
    return dict(build=build_receipt,controls=controls(binary),verification=validate(report,meta,binary),native_report=report)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--controls-only',action='store_true');args=parser.parse_args()
    assert args.controls_only and os.environ.get('GITHUB_ACTIONS')=='true'
    with tempfile.TemporaryDirectory() as tmp:
        binary,receipt=build(Path(tmp)/'native');print(json.dumps(dict(build=receipt,controls=controls(binary))))
