import runpy,json,hashlib,itertools
from pathlib import Path
import klayout.db as db
c=runpy.run_path('scripts/audit_current650_placement.py')
L=c['layout'];old=c['top'];out=c['out'];parent=c['parent'];children=c['ordered'];plans=c['cut_plans']
assert len(children)==16 and all(p['selected_cut_dbu'] is not None for p in plans)
cuts=[p['selected_cut_dbu']for p in plans];bbox=old.bbox()
edges=[bbox.bottom-1000,*cuts,bbox.top+1000]
assert all(edges[i]<edges[i+1]for i in range(16))
def owner(y):
    hits=[i for i in range(16)if edges[i]<=y<edges[i+1]]
    assert len(hits)==1,(y,hits)
    return hits[0]
for i,inst in enumerate(children):
    assert owner(inst.bbox().bottom)==owner(inst.bbox().top)==i
raw={tuple(p['bbox_dbu'])for q in plans for p in q['crossing_tm1_polygons']}
assert len(raw)==37 and all(p['rectangle']for q in plans for p in q['crossing_tm1_polygons'])
trunks=[db.Box(*x)for x in sorted(raw)]
assert all(b.right<min(i.bbox().left for i in children)for b in trunks)
removed=db.Region()
for b in trunks:removed.insert(b)
assert (removed-parent[(126,0)]).is_empty()
local={k:((v-removed).merged()if k==(126,0)else v)for k,v in parent.items()}
for key,r in local.items():
    for p in r.each():
        assert not any(p.bbox().bottom<y<p.bbox().top for y in cuts),(key,str(p.bbox()))
# Native contact cuts, not synthetic points, determine every trunk extent.
via=db.Region()
for layer in [125,133]:via+=db.Region(old.begin_shapes_rec(L.layer(layer,0)))
via=via.merged()
records=[]
for t in trunks:
    pieces=via.interacting(db.Region(t))
    contacts=[]
    for p in pieces.each():
        b=p.bbox()
        assert (db.Region(p)-db.Region(t)).is_empty(),('contact not inside trunk',str(t),str(b))
        i=owner(b.bottom);assert owner(b.top)==i
        contacts.append((i,b.bottom,b.top))
    assert contacts,('trunk without native contacts',str(t))
    lo=min(x[1]for x in contacts);hi=max(x[2]for x in contacts)
    records.append(dict(box=[t.left,t.bottom,t.right,t.top],contacts=contacts,
                        bottom_margin=lo-t.bottom,top_margin=t.top-hi))
def offsets(order):
    cursor=edges[0];shift=[None]*16
    for i in order:
        shift[i]=cursor-edges[i];cursor+=edges[i+1]-edges[i]
    assert cursor==edges[-1] and all(x%5==0 for x in shift)
    return shift
def rebuilt(shift):
    return [db.Box(r['box'][0],min(lo+shift[i]for i,lo,hi in r['contacts'])-r['bottom_margin'],
                   r['box'][2],max(hi+shift[i]for i,lo,hi in r['contacts'])+r['top_margin'])for r in records]
def evaluate(order):
    shift=offsets(order);boxes=rebuilt(shift)
    for i,a in enumerate(boxes):
        for b in boxes[i+1:]:
            # Original separate metal polygons must remain separate with margin.
            if a.enlarged(1000).overlaps(b):return None
    return sum(b.height()for b in boxes if b.width()<10000)
base=tuple(range(16));assert rebuilt(offsets(base))==trunks
baseline=evaluate(base);assert baseline is not None
best=base;score=baseline;history=[]
while True:
    choices=[]
    for a,b in itertools.combinations(range(6,15),2):
        q=list(best);q[a],q[b]=q[b],q[a];q=tuple(q);value=evaluate(q)
        if value is not None and value<score:choices.append((value,q))
    if not choices:break
    value,q=min(choices);history.append(dict(before=list(best),after=list(q),before_score=score,after_score=value))
    score,best=value,q
planning=dict(original_order=list(base),candidate_order=list(best),original_signal_trunk_span_dbu=baseline,
              candidate_signal_trunk_span_dbu=score,history=history,trunks=records,cuts_dbu=cuts,
              scope='Geometric span objective only. First six sampler/clock bands and final V-I band fixed. No electrical acceptance.')
(out/'compact-planning.json').write_text(json.dumps(planning,indent=2))
assert score<baseline and best!=base,'No safe geometric improvement'
shift=offsets(best);assert shift[:6]==[0]*6 and shift[15]==0
# Preserve local material band by band; only authenticated trunk rectangles change.
moved={}
for key,r in local.items():
    total=db.Region();original_parts=db.Region()
    for i in range(16):
        window=db.Region(db.Box(bbox.left-1000,edges[i],bbox.right+1000,edges[i+1]))
        part=(r&window).merged();original_parts+=part
        total+=part.transformed(db.Trans(0,shift[i]))
    assert (original_parts.merged()^r).is_empty(),('unaccounted material',key)
    moved[key]=total.merged()
for box in rebuilt(shift):moved[(126,0)].insert(box)
moved[(126,0)]=moved[(126,0)].merged()
name=old.name;old.name=name+'_source_preserved';new=L.create_cell(name)
for i,inst in enumerate(children):
    assert not inst.is_regular_array()
    tr=inst.cplx_trans
    assert tr.mag==1 and tr.angle==0 and not tr.is_mirror()
    new.insert(db.CellInstArray(inst.cell_index,db.Trans(tr.disp.x,tr.disp.y+shift[i])))
for (layer,dt),r in moved.items():new.shapes(L.layer(layer,dt)).insert(r)
for li in L.layer_indexes():
    for shape in old.each_shape(li):
        if shape.is_text():
            text=shape.text.dup();text.trans=db.Trans(text.trans.rot,text.trans.disp.x,text.trans.disp.y+shift[owner(text.trans.disp.y)])
            new.shapes(li).insert(text)
def regions(layout,cell):
    return {(layout.get_info(li).layer,layout.get_info(li).datatype):db.Region(cell.begin_shapes_rec(li)).merged()for li in layout.layer_indexes()}
expected=regions(L,new);target=out/'compact-current650.gds';opt=db.SaveLayoutOptions();opt.select_cell(new.cell_index());opt.write_context_info=False;L.write(str(target),opt)
check=db.Layout();check.read(str(target));assert len(check.top_cells())==1 and check.top_cell().name==name
actual=regions(check,check.top_cell())
for k in set(expected)|set(actual):assert (expected.get(k,db.Region())^actual.get(k,db.Region())).is_empty(),k
reference=c['z'].read('schematic650-select-width2.cir');(out/'compact-current650.cir').write_bytes(reference)
r=dict(status='GENERATED_COMPACT_CURRENT650_REQUIRES_DRC_LVS_FRESH_RC_AND_ELECTRICAL',
       planning=planning,source_gds_sha256=c['r']['source_gds_sha256'],candidate_gds_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
       reference_sha256=hashlib.sha256(reference).hexdigest(),immutable_child_count=16,
       fixed_first_six_and_last_bands=True,local_material_conserved=True,roundtrip_regions_equal=True,
       full_phy_accepted=False,physical_acceptance=False,qualified_pex=False,
       limitation='Native DRC/LVS and complete actual RC/electrical validation pending. No LEF/mainchip integration or production acceptance.')
(out/'compact-result.json').write_text(json.dumps(r,indent=2))

def text_rows(layout,cell):
    return [dict(layer=str(layout.get_info(li)),string=sh.text.string,x=sh.text.x,y=sh.text.y,trans=str(sh.text.trans)) for li in layout.layer_indexes() for sh in cell.each_shape(li) if sh.is_text()]
(out/'text-diagnostic.json').write_text(json.dumps(dict(source=text_rows(L,old),candidate=text_rows(L,new),serialized=text_rows(check,check.top_cell()),offsets=shift),indent=2))
