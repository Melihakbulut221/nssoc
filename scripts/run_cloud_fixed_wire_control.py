#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Cloud native control: encode FIXED routes without changing physical design.

No ECO, timing closure, route acceptance or serial PHY claim. This control is
needed before unchanged routes can be protected in a subsequent physical ECO.
"""
import hashlib,json,os,re,subprocess,sys,tarfile,gzip,itertools
from pathlib import Path
from route_cloud_newer_postcts import fetch,sha
from run_cloud_routed_geometry import BASE,STEM,SUMMARY_SHA,ARCHIVE_SHA
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'cloud-fixed-wire-control'
SECTION=re.compile(r'^NETS ([0-9]+) ;\n(.*?)^END NETS[ \t]*\n',re.M|re.S)
ROUTED=re.compile(r'^([ \t]*\+ )ROUTED(?= )',re.M)
FIXED=re.compile(r'^([ \t]*\+ )FIXED(?= )',re.M)
def omit_patch_connections(body):
    # Update only wire encoding on existing native nets. Reconnecting an
    # already connected ITerm is unnecessary; native end() also reverses its
    # list unconditionally. The caller uses two identical imports to restore it.
    entries=re.split(r'(?m)^(?=[ \t]*- )',body)
    assert not entries[0].strip();out=[];removed=0
    for entry in entries[1:]:
        header=re.match(r'([ \t]*- \S+)(.*?)(?=[ \t]*\+ |[ \t]*;)',entry,re.S)
        assert header,'Unsupported NETS header'
        middle=header.group(2)
        empty,count=re.subn(r'\(\s+(\S+)\s+(\S+)\s+\)','',middle)
        assert not empty.strip(),'Unsupported connection syntax; do not rewrite'
        removed+=count
        out.append(header.group(1)+'\n'+entry[header.end():])
    return ''.join(out),removed

def convert_def(text):
    found=list(SECTION.finditer(text));assert len(found)==1,'Missing or duplicate NETS'
    m=found[0];body=m.group(2)
    assert len(re.findall(r'^[ \t]*- ',body,re.M))==int(m.group(1)),'NETS count mismatch'
    assert ROUTED.search(body),'No ROUTED clauses'
    body,count=ROUTED.subn(r'\1FIXED',body)
    new_section='NETS '+m.group(1)+' ;\n'+body+'END NETS\n'
    full=text[:m.start()]+new_section+text[m.end():]
    header=[]
    for key in ('VERSION','DIVIDERCHAR','BUSBITCHARS','DESIGN','UNITS DISTANCE MICRONS'):
        rows=re.findall(r'^'+key+r' [^\n]+ ;$',text,re.M);assert len(rows)==1,(key,rows);header+=rows
    patch_body,removed=omit_patch_connections(body)
    assert removed>0,'No existing connections verified'
    patch_section='NETS '+m.group(1)+' ;\n'+patch_body+'END NETS\n'
    return full,'\n'.join(header)+'\n'+patch_section+'END DESIGN\n',count

def assert_same_def(expected,actual):
    assert expected==actual,'Native full DEF changed beyond explicit route class conversion'

def controls():
    fixture='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN chip ;\nUNITS DISTANCE MICRONS 1000 ;\nCOMPONENTS 1 ;\n- a cell + FIXED ( 2 3 ) N ;\nEND COMPONENTS\nNETS 1 ;\n    - sig ( a X )\n      + ROUTED Metal1 ( 10 20 ) ( 30 * )\n      NEW Metal2 ( 30 20 ) via\n ;\nEND NETS\nEND DESIGN\n'
    expected,patch,count=convert_def(fixture);assert count==1 and 'COMPONENTS' not in patch and '+ FIXED ( 2 3 )' in expected and '( a X )' not in patch and '( a X )' in expected
    assert_same_def(expected,expected);rejected=[]
    for label,bad in [('coordinate',expected.replace('( 10 20 )','( 11 20 )')),('missing_route',expected.replace('      NEW Metal2 ( 30 20 ) via\n','')),('wrong_class',fixture)]:
        try:assert_same_def(expected,bad)
        except AssertionError:rejected.append(label)
        else:raise AssertionError(label+' accepted')
    for label,bad in [('missing_nets',fixture.replace('NETS 1 ;','XNETS 1 ;')),('count',fixture.replace('NETS 1 ;','NETS 2 ;')),('duplicate_nets',fixture+fixture),('broken_connection',fixture.replace('( a X )','( a X'))]:
        try:convert_def(bad)
        except AssertionError:rejected.append(label)
        else:raise AssertionError(label+' accepted')
    return dict(positive_exact_change=True,negative_controls=rejected)

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(exist_ok=False)
    result=dict(status='RUNNING',accepted=False,source_run=38788529905,source_head=os.environ['GITHUB_SHA'],controls=controls(),full_serial_phy_complete=False,final_timing_complete=False,
      scope='Native FIXED encoding and exact existing design preservation only. No physical ECO or reroute, no fresh RC, no signoff. Original antenna and global overflow failures remain open.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(args,label,extra=None):
        with (OUT/(label+'.log')).open('w') as log:
            p=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,**(extra or {})),timeout=7200)
        text=(OUT/(label+'.log')).read_text(errors='replace');print(label,p.returncode,text[-4000:],flush=True)
        assert p.returncode==0 and not re.search(r'(?m)^\[ERROR|^Error:',text),(label,p.returncode)
        result[label+'_warnings']=[l for l in text.splitlines() if '[WARNING' in l];save()
    def tcl(text,label):
        p=OUT/(label+'.tcl');p.write_text(text);run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit',str(p)],label)
    def snapshot(path,label):
        run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/snapshot_cloud_fixed_wires.py')],label,dict(NSSOC_FIXED_INPUT=str(path),NSSOC_FIXED_OUTPUT=str(OUT/(label+'.json'))))
        return json.loads((OUT/(label+'.json')).read_text())
    save()
    try:
        source=OUT/'source';source.mkdir();fetch(BASE+STEM+'.summary.json',SUMMARY_SHA,source/'summary.json');old=json.loads((source/'summary.json').read_text())
        assert old['native_drt_drvs']==0 and old['audit_after']['counts']['wired_net_count']==113556
        packed=OUT/'original.tar.gz';fetch(BASE+STEM+'.tar.gz',ARCHIVE_SHA,packed);assert packed.stat().st_size==104854492
        with tarfile.open(packed) as a:
            data=a.extractfile('cloud-failed-guide-drt/routed.odb').read();assert hashlib.sha256(data).hexdigest()==old['outputs']['routed.odb'];(source/'routed.odb').write_bytes(data)
        packed.unlink();original=source/'routed.odb';original_sha=sha(original);assert original_sha=='4ecf6f150c7288c43b99fb944bec72e5ad45f693234181ff47c1df7566957493'
        result['source_sha256']=original_sha;result['source_summary_sha256']=SUMMARY_SHA;result['source_archive_sha256']=ARCHIVE_SHA
        result['before']=snapshot(original,'before')
        # Negative control sets metadata to FIXED, but verifies that encoded
        # PATH wire types are still ROUTED. DRT consumes these encoded types.
        assert result['before']['metadata_only_negative_control_rejected']
        tcl(f'read_db {{{original}}}\nwrite_def {{{OUT/"before.def"}}}\n','export-def')
        before=(OUT/'before.def').read_text();expected,patch,count=convert_def(before)
        result['converted_route_clauses']=count
        assert count==113556 and result['before']['wire_type_net_counts']=={'ROUTED':113556}
        (OUT/'expected-fixed.def').write_text(expected);(OUT/'fixed-nets.def').write_text(patch);save()
        # Pinned OpenROAD INCREMENTAL mode does NOT register NETS callbacks.
        # FLOORPLAN mode updates existing nets; this patch contains no cell,
        # port, power, via-definition, grid, row or NDR-definition sections.
        # Pinned definNet::end always reverses native ITerms. Two identical
        # imports restore the original list order; no tolerance or normalization
        # is permitted in the following exact DEF and geometry comparisons.
        tcl(f'read_db {{{original}}}\nread_def -floorplan_initialize {{{OUT/"fixed-nets.def"}}}\nwrite_def {{{OUT/"single-pass.def"}}}\nread_def -floorplan_initialize {{{OUT/"fixed-nets.def"}}}\nwrite_def {{{OUT/"after.def"}}}\nwrite_db {{{OUT/"fixed.odb"}}}\n','encode-fixed')
        result['native_route_patch_passes']=2
        result['after']=snapshot(OUT/'fixed.odb','after')
        assert result['after']['wire_type_net_counts']=={'FIXED':113556},'Decoder did not see FIXED routes'
        for key in ('instances_sha256','nets_sha256','fixed_data_sha256','counts'):
            assert result['before'][key]==result['after'][key],('Native design changed',key)
        actual=(OUT/'after.def').read_text();result['full_def_exact_expected']=expected==actual
        mismatches=[];mismatch_count=0
        for index,(a,z) in enumerate(itertools.zip_longest(expected.splitlines(),actual.splitlines()),1):
            if a!=z:
                mismatch_count+=1
                if len(mismatches)<12:mismatches.append(dict(line=index,expected=a,actual=z))
        result['def_difference']=dict(differing_lines=mismatch_count,first_lines=mismatches,expected_bytes=len(expected.encode()),actual_bytes=len(actual.encode()))
        print('DEF_DIFFERENCE',json.dumps(result['def_difference']),flush=True);save()
        # Separate existing native shape decoder includes every wire segment,
        # NDR width, patch rectangle, physical via routing box and LEF pin.
        for label,path in [('baseline',original),('fixed',OUT/'fixed.odb')]:
            d=OUT/label;(d/'source').mkdir(parents=True);os.link(path,d/'source/routed.odb')
            run([os.environ['CLOUD_APPIMAGE'],'openroad','-exit','-python',str(ROOT/'scripts/export_cloud_routed_shapes.py')],'shapes-'+label,dict(NSSOC_ROUTE_AUDIT_OUT=str(d)))
        left=OUT/'baseline/signal-geometry.jsonl.gz';right=OUT/'fixed/signal-geometry.jsonl.gz'
        def digest(path):
            h=hashlib.sha256()
            with gzip.open(path,'rb') as stream:
                while chunk:=stream.read(1024**2):h.update(chunk)
            return h.hexdigest()
        result['decoded_shapes_sha256']={'before':digest(left),'after':digest(right)}
        result['decoded_shapes_identical']=len(set(result['decoded_shapes_sha256'].values()))==1;save()
        assert_same_def(expected,actual)
        assert result['decoded_shapes_identical'],'Native decoded shapes changed'
        assert sha(original)==original_sha;result['source_unchanged']=True
        result['status']='COMPLETE_ENCODED_FIXED_ROUTE_PRESERVATION_CONTROL_NOT_ECO_NOT_SIGNOFF'
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='result.json'};save()
if __name__=='__main__':
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    if '--controls-only' in sys.argv:print(json.dumps(controls()))
    else:main()
