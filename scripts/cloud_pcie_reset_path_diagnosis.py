#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Bind the real retrain-to-TX STA path to exact post-ECO mapped cell nets."""
import hashlib,json,os,re,tarfile
from pathlib import Path
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'cloud-pcie-reset-path-diagnosis'
BASE='https://github.com/Melihakbulut221/nssoc/releases/download/'
PROOF_GROUP='corrpre-timing-logic'
PROOF_RUN=39014414337
PROOF_SUMMARY='982d8434120bf1a0ef84be1e500e3231b66d8ac7ec025492ad869e2eb7a6db6f'
ARCHIVE_SHA='276a5cac3bc74ff4c9c900802d7463fe72fdc70e6edb34b6f341d55b354348dc'
PATH_SUMMARY='a448aaed7067c8b7ba77256f18635877ce1a76f44bcaa8fc332a2e664b1770be'
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,
        full_phy_accepted=False,final_timing_complete=False,
        scope='Read-only exact saved native STA and post-ECO mapped JSON cell connectivity. No timing exception, new CAD run or circuit modification.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        stem=f'{PROOF_GROUP}-{PROOF_RUN}-1';url=BASE+f'cloud-results-{PROOF_RUN}-1-{PROOF_GROUP}/'+stem
        fetch(url+'.summary.json',PROOF_SUMMARY,OUT/'proof-summary.json')
        proof=json.loads((OUT/'proof-summary.json').read_text())
        assert proof['status']=='PASS_SAVED_FULLCHIP_TIMING_ECO_EQUATIONS_NOT_TIMING_OR_PHYSICAL_SIGNOFF'
        assert proof['sources_unchanged']and proof['proof']['retained_cells']==96655
        archive=OUT/'source.tar.gz';fetch(url+'.tar.gz.part0000',ARCHIVE_SHA,archive)
        assert archive.stat().st_size==9990849
        dest=OUT/'source';dest.mkdir()
        with tarfile.open(archive)as tar:tar.extractall(dest,filter='data')
        archive.unlink();source=dest/'cloud-corrpre-timing-logic'
        assert sha(source/'result.json')==PROOF_SUMMARY
        assert all(sha(source/n)==digest for n,digest in proof['outputs'].items())
        url=BASE+'cloud-results-39012558696-1-corrpre-timing-path-review/corrpre-timing-path-review-39012558696-1.summary.json'
        fetch(url,PATH_SUMMARY,OUT/'native-paths.json');paths=json.loads((OUT/'native-paths.json').read_text())
        assert paths['status']=='COMPLETE_SOURCE_BOUND_NATIVE_POSTCTS_PATH_REVIEW_NOT_TIMING_CLOSURE'
        assert paths['source_run']==39011120664 and paths['repaired_odb_sha256']=='94e4f21b7ee0018ef0cc9715ed40a2932e8ecda3d23434e770195c77029cd7a6'
        timing=next(s for s in proof['source_specs']if s['run']==paths['source_run'])
        assert timing['archive']==paths['source_archive_sha256']and timing['summary']==paths['source_summary_sha256']
        mapped=source/'proof/after.json';assert sha(mapped)=='cc6e3f09e7fcee3d50441ed62d872b3b837148dc7d1aa32510816af10a47d25e'
        top=json.loads(mapped.read_text())['modules']['soc_top'];aliases={}
        for name,net in top['netnames'].items():
            for i,bit in enumerate(net['bits']):
                aliases.setdefault(bit,[]).append(dict(net=name,bit=i,hidden=bool(net['hide_name'])))
        # OpenROAD STA prints identifiers without the Verilog escape prefix;
        # the saved Yosys JSON retains that prefix. Require a unique spelling
        # normalization and still prove every cell type, pin and native net.
        native_names={}
        for name in top['cells']:
            visible=name.lstrip(chr(92))
            assert visible not in native_names,'Ambiguous native identifier normalization'
            native_names[visible]=name
        def names(bit):return aliases.get(bit,[])
        def bind(path):
            pins=re.findall(r' [\^v] (\S+)/(\S+) \((sg13g2_\S+)\)',path['native_report'])
            assert pins and len(pins)%2==0
            previous=top['ports']['pcie_retrain_done_i']['bits'];assert len(previous)==1
            previous=previous[0];stages=[]
            for index in range(0,len(pins),2):
                a,b=pins[index:index+2];assert a[0]==b[0]and a[2]==b[2]
                native_name=native_names[a[0]];cell=top['cells'][native_name];assert cell['type']==a[2]
                assert cell['port_directions'][a[1]]=='input'and cell['port_directions'][b[1]]=='output'
                incoming=cell['connections'][a[1]];outgoing=cell['connections'][b[1]]
                assert incoming==[previous]and len(outgoing)==1,'STA path and saved mapped connectivity differ'
                stages.append(dict(cell=a[0],native_cell=native_name,type=cell['type'],entry=a[1],exit=b[1],
                    input_aliases=names(incoming[0]),output_aliases=names(outgoing[0]),
                    all_inputs={pin:[names(bit)for bit in bits]for pin,bits in cell['connections'].items()if cell['port_directions'][pin]=='input'}))
                previous=outgoing[0]
            assert previous==top['ports']['pcie_tx_data_o']['bits'][5]
            return stages
        result['paths']={}
        for corner in ('nom_typ_1p20V_25C-max','nom_fast_1p32V_m40C-max'):
            selected=[p for p in paths['worst_paths'][corner]if p['startpoint'].startswith('pcie_retrain_done_i ')]
            assert selected
            path=selected[0];assert path['endpoint'].startswith('pcie_tx_data_o[5] ')
            stages=bind(path)
            result['paths'][corner]=dict(startpoint=path['startpoint'],endpoint=path['endpoint'],slack_ns=path['slack_ns'],stages=stages)
        result['source']={'proof_run':PROOF_RUN,'proof_summary_sha256':PROOF_SUMMARY,'proof_archive_sha256':ARCHIVE_SHA,'path_summary_sha256':PATH_SUMMARY,'mapped_json_sha256':sha(mapped),'native_netlist_sha256':proof['after_netlist_sha256']}
        result['status']='COMPLETE_EXACT_NATIVE_RETRAIN_TX_PATH_CELL_NET_BINDING_NOT_REPAIR'
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
        print(json.dumps({k:result[k]for k in ('status','error')if k in result}),flush=True)
if __name__=='__main__':main()
