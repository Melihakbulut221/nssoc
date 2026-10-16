#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Raw100 intrinsic models from actual pullup GDS, not electrical acceptance."""
import argparse,json,os
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import cloud_tx_driver_localpins_intrinsic as intrinsic
from cloud_tx_driver_pullup_junctions import verify_resistors
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'l2p7':dict(summary='43c50321bc631c8d372ee3f69309a344e64e77066534a44fad3f7850d66e82b4',parts='143da498919c8c9375eeef08046fdeaaceafa1a55709a6d23bfcd5d3bc536ac6'),
 'l2p4':dict(summary='3203a70617ecfe3b0e5739022c9a4f884b8b4c1661d4041155109499653e095f',parts='02c4189fe4bfa957210edaf8ddf52d1f65759d5de786699e3b0ad4db439f5529'),
}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=sorted(SOURCES),required=True);args=parser.parse_args()
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out=ROOT/('hw/soc/out/cloud-tx-driver-pullup-intrinsic-'+args.variant);out.mkdir(parents=True,exist_ok=False);reports.OUT=out
    spec=SOURCES[args.variant];source=out/'source'
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],variant=args.variant,source_run=38933670094,source=spec,qualified_pex=False,serial_phy_complete=False,mainchip_integrated=False,wire_parasitics_included=False,simulator_checked=False)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        selected=('native.json','audit.json')
        prior,proof=reports.restore_report('tx-driver-pullup-junctions-'+args.variant,38933670094,spec['summary'],spec['parts'],source,selected);result['restore']=proof
        assert prior['status']=='PASS_ACTUAL_PULLUP_RAW100_JUNCTIONS_AND_RESISTOR_BINDINGS_NOT_WIRE_RC_OR_ELECTRICAL_ACCEPTANCE' and prior['source_unchanged'] and prior['variant']==args.variant
        audit=json.loads((source/'audit.json').read_text());assert audit==prior['junction_audit'] and audit['native_source_sha256']==sha(source/'native.json')
        assert len(audit['negative_controls'])==5 and all(c['rejected']for c in audit['negative_controls'])
        assert len(prior['resistor_controls'])==2 and all(c['rejected']for c in prior['resistor_controls'])
        record=json.loads((source/'native.json').read_text());assert verify_resistors(record)==prior['resistors']
        result['retained_combined_disagreements']=audit['aggregate_comparison']
        assert not audit['aggregate_junction_reproduction_passed'] and sum(not c['equal']for c in audit['aggregate_comparison'])==3
        rows=record['native']['raw_flat_lvs']['devices'];assert len(rows)==100
        models=out/'pdk'
        for path,digest in intrinsic.PINS.items():
            target=models/path;target.parent.mkdir(parents=True,exist_ok=True)
            fetch('https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+intrinsic.PDK+'/ihp-sg13g2/'+path,digest,target)
        intrinsic.validate_model_libraries(models)
        tech=json.loads((models/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json').read_text())['techParams']
        intrinsic.TOP='nssoc_tx_driver_pullup_'+args.variant+'_native100_intrinsic_v1'
        text,bindings=intrinsic.build(rows,tech);model=out/'driver100.spice';model.write_text(text)
        result['positive']=intrinsic.verify(model.read_text(),rows,tech);result['bindings']=bindings
        result['controls']=intrinsic.negative_controls(text,rows,tech,out)
        pullup=next(c for c in prior['resistors']if c['path']=='xdriver.xup');name='XD'+str(pullup['native_id'])
        lines=text.splitlines();index=next(i for i,line in enumerate(lines)if line.startswith(name+' '))
        words=lines[index].split();assert sum(w.startswith('l=')for w in words)==1
        words=['l=3.08u'if w.startswith('l=')else w for w in words];lines[index]=' '.join(words)
        bad='\n'.join(lines)+'\n';(out/'old_pullup_length.spice').write_text(bad)
        try:intrinsic.verify(bad,rows,tech)
        except AssertionError as error:result['controls'].append(dict(fault='old_pullup_length',rejected=True,reason=str(error)))
        else:raise AssertionError('Accepted old pullup geometry in actual model')
        assert len(result['controls'])==8 and all(c['rejected']for c in result['controls'])
        assert all(sha(models/p)==digest for p,digest in intrinsic.PINS.items()) and all(sha(source/p)==prior['outputs'][p]for p in selected)
        result.update(model_sha256=sha(model),models=dict(commit=intrinsic.PDK,hashes=intrinsic.PINS),source_unchanged=True,status='PASS_ACTUAL_PULLUP_NATIVE100_INTRINSIC_AND_EIGHT_FAULTS_NOT_WIRE_RC_OR_ELECTRICAL_ACCEPTANCE')
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()and p!=out/'result.json'};save()
if __name__=='__main__':main()
