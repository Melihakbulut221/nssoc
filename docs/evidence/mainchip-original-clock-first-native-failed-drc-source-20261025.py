#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Initial restored-wire DRT measurement only; no detailed_route or repair."""
import json,os
from pathlib import Path
import mainchip_original_clock_restoration as c
CATEGORY='NSSOC_INITIAL_ORIGINAL_CLOCK_RESTORE_DRC'

def marker_tree(category):
    """Require actual uncapped native category counts, including the zero case."""
    assert category is not None,'Missing native DRT marker category'
    assert category.getName()==CATEGORY and category.getSource()=='DRT'
    def walk(node,path):
        direct=list(node.getMarkers());children=list(node.getMarkerCategories())
        maximum=node.getMaxMarkers()
        assert type(maximum)is int and maximum>0,'Unknown marker cap'
        assert len(direct)<maximum,'Marker category may have been truncated at native cap'
        names=[x.getName()for x in children]
        assert len(names)==len(set(names)),'Duplicate marker category'
        rows=[dict(path=path,direct_markers=len(direct),maximum_markers=maximum)]
        total=len(direct)
        for child in children:
            n,more=walk(child,path+[child.getName()]);total+=n;rows+=more
        assert node.getMarkerCount()==total
        assert len(list(node.getAllMarkers()))==total
        return total,rows
    count,rows=walk(category,[CATEGORY])
    return dict(marker_count=count,categories=rows,all_categories_below_native_cap=True,
                zero_reported_DRT_markers=count==0,full_signoff_DRC=False)

def tcl(source,out,path_quote):
    return ('read_db '+path_quote(source)+'\nset_thread_count 2\nwrite_def '+
        path_quote(out/'drc-before.def')+'\ndrt::check_drc -output_file '+
        path_quote(out/'initial-drc.rpt')+' -marker_name '+CATEGORY+
        '\nwrite_def '+path_quote(out/'drc-after.def')+
        '\nwrite_db '+path_quote(out/'drc-observed.odb')+'\n')

def measure_report(category,report,reexport):
    result=marker_tree(category)
    category.writeTR(str(reexport))
    raw=c.regular(report).read_bytes()
    assert raw==c.regular(reexport).read_bytes(),'Native marker DB/report differ'
    assert (raw==b'')==(result['marker_count']==0),'Empty report/native zero mismatch'
    assert sum(x.startswith(b'violation type: ')for x in raw.splitlines())==result['marker_count']
    result.update(report_bytes=len(raw),report_sha256=c.digest(raw))
    return result

def master_pin_boxes(pin):
    """dbMPin box geometry includes polygon decomposition, not original polygon identity."""
    return sorted((b.getTechLayer().getName(),b.xMin(),b.yMin(),b.xMax(),b.yMax())
                  for b in pin.getGeometry(True))

def geometry_projection(db,block,native):
    """Stream native nonmarker connectivity/placement/pin/via geometry plus exact DEF separately."""
    import hashlib
    digest=hashlib.sha256();counts={}
    def feed(kind,rows):
        count=0
        for row in rows:
            encoded=c.canonical([kind,row]);digest.update(len(encoded).to_bytes(8,'big'));digest.update(encoded);count+=1
        counts[kind]=count
    nets=sorted(block.getNets(),key=lambda n:n.getName())
    feed('net',((native.identity(db,n),native.encoded(n))for n in nets))
    feed('instance',([i.getName(),i.getMaster().getName(),list(i.getLocation()),
        str(i.getOrient()),str(i.getPlacementStatus()),list(i.getOrigin())]
        for i in sorted(block.getInsts(),key=lambda i:i.getName())))
    masters={i.getMaster().getName():i.getMaster()for i in block.getInsts()}
    feed('master-pin',([name,t.getName(),str(t.getIoType()),str(t.getSigType()),
        [master_pin_boxes(p)for p in t.getMPins()]]
        for name,master in sorted(masters.items())for t in sorted(master.getMTerms(),key=lambda t:t.getName())))
    used=native.vias(db,block,[n.getName()for n in nets])
    feed('used-via',sorted(used.items()))
    return dict(sha256=digest.hexdigest(),counts=counts,
       scope='All native net terminals/BTerms/NDR projection/encoded classes, every instance placement, instantiated master pin getGeometry(True) boxes including decomposed polygons and all used via boxes; original polygon segmentation/vertex identity is not separately projected. Full DEF is compared separately; not a claim of byte-identical serialized database.')

def main():
    import odb
    import mainchip_original_clock_restoration_native as native
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    m=c.source_gate()
    assert m['native_prepare_audit_authorized']is True
    assert m['native_routing_authorized']is False and m['simulation_authorized']is False
    mode=os.environ['NSSOC_CLOCK_DRC_PHASE'];assert mode in ('prepare','audit')
    out=Path(os.environ['NSSOC_CLOCK_RESTORE_OUT'])
    source=c.regular(out/'restored.odb')
    donor=c.regular(Path(os.environ['NSSOC_CLOCK_RESTORE_DONOR']))
    recipient=c.regular(Path(os.environ['NSSOC_CLOCK_RESTORE_RECIPIENT']))
    result=dict(status='RUNNING',accepted=False,full_signoff_DRC=False,
                native_routing_started=False,final_timing_complete=False,full_phy_accepted=False)
    target=out/('drc-'+mode+'-result.json')
    try:
        prior=json.loads(c.regular(out/'audit-restored-result.json').read_bytes())
        assert prior['status']=='PASS_EXACT_ORIGINAL_CLOCK_RESTORE_REQUIRES_ZERO_DRC_DETERMINATION'
        assert prior['restored_odb_sha256']==c.file_sha(source)
        assert c.file_sha(out/'original-gate-restored/result.json')==prior['original_gate']['sha256']
        a,b,expected,plan=native.context(donor,recipient,out)
        restored=native.audit_view(source,expected,b,out,'drc-source')
        assert restored['encoded']==a['encoded'] and restored['snapshot']==a['snapshot']
        assert not(out/'fixed.odb').exists(),'Initial DRC must precede temporary FIXED encoding'
        if mode=='prepare':
            db,block=native.load(source)
            try:
                assert block.findMarkerCategory(CATEGORY)is None,'Pre-existing diagnostic category'
                geometry=geometry_projection(db,block,native)
            finally:odb.dbDatabase.destroy(db)
            (out/'initial-drc.tcl').write_text(tcl(source,out,native.tcl_path))
            result.update(status='PREPARED_READ_ONLY_INITIAL_DRT_CHECK',
                input_odb_sha256=c.file_sha(source),expected_def_sha256=c.digest(expected),
                tcl_sha256=c.file_sha(out/'initial-drc.tcl'),marker_category=CATEGORY,native_geometry=geometry)
        else:
            prep=json.loads(c.regular(out/'drc-prepare-result.json').read_bytes())
            assert prep['status']=='PREPARED_READ_ONLY_INITIAL_DRT_CHECK'
            assert prep['input_odb_sha256']==c.file_sha(source)
            assert prep['tcl_sha256']==c.file_sha(out/'initial-drc.tcl')
            for name in ['drc-before.def','drc-after.def']:
                c.verify_exact(expected,c.regular(out/name).read_bytes())
            measured=c.regular(out/'drc-observed.odb')
            got=native.audit_view(measured,expected,b,out,'drc-final')
            assert got['encoded']==a['encoded'] and got['snapshot']==a['snapshot']
            db,block=native.load(measured)
            try:
                category=block.findMarkerCategory(CATEGORY)
                geometry=geometry_projection(db,block,native)
                assert geometry==prep['native_geometry'],'Nonmarker native geometry projection changed'
                result['native_geometry']=geometry
                if category is not None:category.writeJSON(str(out/'initial-drc-markers.json'))
                result['measurement']=measure_report(category,out/'initial-drc.rpt',out/'initial-drc-reread.rpt')
            finally:odb.dbDatabase.destroy(db)
            result['original_gate']=native.original_gate(donor,measured,out,'original-gate-after-drc')
            result.update(status='COMPLETE_INITIAL_DRT_MEASUREMENT_NOT_SIGNOFF',
                geometry_DEF_byte_exact=True,original_clock_gate_passed=True,
                measured_odb_sha256=c.file_sha(measured),original_class_input_sha256=c.file_sha(source))
    except BaseException as e:
        result.update(status='FAIL_INITIAL_DRT_DIAGNOSTIC',error=repr(e));raise
    finally:
        result['source_inputs_unchanged']=c.file_sha(donor)==c.DONOR_SHA and c.file_sha(recipient)==c.RECIPIENT_SHA
        target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':main()
