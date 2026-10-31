#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic geometry controls; no archived native input is acquired."""
import copy,json,tempfile,traceback
from pathlib import Path
import cdr_current_via2_m3_access_candidate as c

def controls(pya,plan):
    c.validate_plan(plan);checks=[]
    def reject(name,call):
        try:call()
        except(AssertionError,KeyError,TypeError,ValueError):checks.append(dict(name=name,rejected=True));return
        raise AssertionError('Accepted fault: '+name)
    for name,change in[
      ('missing_drain',lambda p:p['targets'].pop()),
      ('duplicate_drain',lambda p:p['targets'].__setitem__(7,copy.deepcopy(p['targets'][6]))),
      ('old_cluster_124',lambda p:p['targets'][4].__setitem__('native_cluster',124)),
      ('wrong_units',lambda p:p.__setitem__('dbu_um',.005)),
      ('width_not_single_candidate',lambda p:p['parameters'].__setitem__('metal3_width_dbu',1000)),
      ('foreign_upper_m3',lambda p:p['targets'][0]['upper_metal3']['ownership']['candidates'][0].__setitem__('component',14)),
      ('unproved_upper_m3',lambda p:p['targets'][0]['upper_metal3']['ownership'].__setitem__('electrical_owner_proved',False)),
      ('native_authority_not_source_control',lambda p:p.__setitem__('candidate_generation_authorized',True)),
      ('changed_anchor',lambda p:p['targets'][0].__setitem__('anchor_dbu',[1,2]))]:
        changed=copy.deepcopy(plan);change(changed);reject(name,lambda:c.validate_plan(changed))
    def regions(row):
        rail=row['existing_rail']['coverage']['existing_M2_300nm_x35_6um']['top_box_dbu']
        own={10:pya.Region(pya.Box(*rail)),29:pya.Region(),30:pya.Region(pya.Box(*row['upper_metal3']['top_bbox_dbu'])),49:pya.Region()}
        return own,{k:r.dup()for k,r in own.items()}
    for row in plan['targets']:
        own,full=regions(row);boxes=c.guard_regions(pya,row,own,full)
        c.require(set(boxes)=={29,30},'only Via2 and M3');checks.append(dict(name='synthetic_owner_positive_'+str(row['device']),passed=True))
    row=plan['targets'][0];x,y=row['anchor_dbu']
    def altered(name,callback):
        own,full=regions(row);extra={};callback(own,full,extra)
        reject(name,lambda:c.guard_regions(pya,row,own,full,extra))
    altered('foreign_M3_inside_route',lambda o,f,e:f.__setitem__(30,f[30]+pya.Region(pya.Box(x-30,y+3000,x+30,y+3500))))
    altered('foreign_M3_within_conservative_clearance',lambda o,f,e:f.__setitem__(30,f[30]+pya.Region(pya.Box(x+800,y+3000,x+900,y+3500))))
    altered('existing_Via2_near_new_cut',lambda o,f,e:f.__setitem__(29,pya.Region(pya.Box(x+300,y-95,x+490,y+95))))
    altered('foreign_Via3_new_upper_contact',lambda o,f,e:f.__setitem__(49,pya.Region(pya.Box(x-95,y+1000,x+95,y+1190))))
    altered('missing_lower_M2_enclosure',lambda o,f,e:o.__setitem__(10,pya.Region(pya.Box(x-140,y-200,x+140,y+200))))
    altered('partial_upper_landing',lambda o,f,e:o.__setitem__(30,o[30]-pya.Region(pya.Box(x-200,y+17400,x-195,y+17800))))
    altered('lower_M2_belongs_to_foreign_owner',lambda o,f,e:o.__setitem__(10,pya.Region()))
    altered('non_drawing_M3_collision',lambda o,f,e:e.__setitem__((30,22),pya.Region(pya.Box(x-50,y+500,x+50,y+800))))
    with tempfile.TemporaryDirectory()as temp:
        root=Path(temp);layout=pya.Layout();layout.dbu=.001;top=layout.create_cell(plan['top']);leaf=layout.create_cell('synthetic_primitive')
        leaf.shapes(layout.layer(1,0)).insert(pya.Box(0,0,100,100));top.insert(pya.CellInstArray(leaf.cell_index(),pya.Trans()))
        top.shapes(layout.layer(1,0)).insert(pya.Box(0,0,2200000,1800000))
        rows=[]
        for row in plan['targets']:
            own,full=regions(row)
            top.shapes(layout.layer(10,0)).insert(pya.Box(*row['existing_rail']['coverage']['existing_M2_300nm_x35_6um']['top_box_dbu']))
            top.shapes(layout.layer(30,0)).insert(pya.Box(*row['upper_metal3']['top_bbox_dbu']))
            for layer,box in c.guard_regions(pya,row,own,full).items():rows.append(dict(device=row['device'],component=row['component'],native_cluster=row['native_cluster'],layer=layer,datatype=0,box_dbu=box))
        baseline=c.snapshot(pya,layout);bbox=top.bbox()
        proof=c.add_and_reverse(pya,layout,rows,root)
        c.require(proof['structural_reversal_exact']is True and len(proof['added_records'])==16,'actual pya serialized structural reversal')
        checks.append(dict(name='synthetic_16_additions_serialized_and_reversed',passed=True))
        for mode in('original_primitive_removed','duplicate_instance','changed_instance_property','changed_shape_property'):
            altered_layout=pya.Layout();altered_layout.read(str(root/'reversed-original-geometry.gds'));t=altered_layout.cell(plan['top'])
            if mode=='original_primitive_removed':next(altered_layout.cell('synthetic_primitive').shapes(altered_layout.layer(1,0)).each()).delete()
            elif mode=='duplicate_instance':t.insert(next(t.each_inst()).cell_inst)
            elif mode=='changed_instance_property':next(t.each_inst()).set_property(999,'intentional-control')
            else:next(t.shapes(altered_layout.layer(10,0)).each()).set_property(999,'intentional-control')
            reject(mode,lambda:c.validate_serialized(pya,altered_layout,baseline,plan['top'],baseline[plan['top']]['raw'],baseline[plan['top']]['material'],bbox))
    return dict(status='PASS_VIA2_M3_SOURCE_AND_SYNTHETIC_GEOMETRY_CONTROLS',cases=checks,
      actual_native_acquired=False,actual_candidate_generated=False,synthetic_geometry_only=True,**c.FLAGS)

def main():
    import pya
    plan=c.source_guard();output=Path('cdr-via2-m3-source-controls');output.mkdir(exist_ok=False)
    try:
        result=controls(pya,plan);result['source']=__import__('os').environ['GITHUB_SHA'];result['run_id']=int(__import__('os').environ['GITHUB_RUN_ID'])
        (output/'result.json').write_bytes(c.encoded(result));print('VIA2_M3_SOURCE_CONTROLS '+c.encoded(result).decode(),flush=True)
    except BaseException as error:
        value=dict(error=repr(error),traceback=traceback.format_exc(),actual_native_acquired=False,**c.FLAGS)
        (output/'failure.json').write_bytes(c.encoded(value));raise
if __name__=='__main__':main()
