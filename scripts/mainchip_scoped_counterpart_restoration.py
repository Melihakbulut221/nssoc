"""Plan only original-class restoration with separately authenticated routing ownership."""
import hashlib
import mainchip_original_clock_restoration as old
import mainchip_targeted_counterpart_routing as scoped
FLAGS=dict(physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def pin(raw):return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def plan(fixed,routed,originals,antenna_plan,scope):
    antenna,extra,protected,routing=scoped.validate_scope(scope,antenna_plan)
    before=old.parse_def(fixed);after=old.parse_def(routed)
    assert list(before['records'])==list(after['records']),'all net names/order'
    names=set(before['records'])
    assert routing|protected<=names and set(originals)==names-antenna,'complete original class ownership'
    assert all(k in (None,'ROUTED','FIXED','COVER')for k in originals.values()),'original class vocabulary'
    sa,sb=before['section'],after['section']
    assert fixed[:sa[0]]+fixed[sa[1]:]==routed[:sb[0]]+routed[sb[1]:],'outside NETS changed'
    for name in names:
        a,b=before['records'][name],after['records'][name]
        assert old.prefix(a)==old.prefix(b),('connection changed',name)
        if name in antenna:
            assert old.classes(a)==old.classes(b)=='ROUTED',('antenna class',name)
        elif name in extra:
            assert originals[name]=='ROUTED'and old.classes(a)=='FIXED'and old.classes(b)=='ROUTED',('counterpart class',name)
        else:
            # The actual diagnostic proved these complete byte records unchanged.
            assert a==b,('unowned fixed record changed',name)
            if originals[name]is None:
                assert not old.ROUTE.search(a),('unwired selected gained route',name)
            else:assert old.classes(a)=='FIXED',('required original temporary fixed overlay',name)
    reduced={n:k for n,k in originals.items()if n not in extra}
    expected=old.restore_classes(routed,reduced)
    check=old.parse_def(expected)
    assert list(check['records'])==list(after['records'])
    changed=[]
    for name in names:
        got=check['records'][name];was=after['records'][name]
        if name in routing:
            assert got==was,('new routed geometry altered during class restoration',name)
        elif originals[name]is None:
            assert got==was,('unwired selected altered',name)
        else:
            assert old.classes(got)==originals[name],('original encoded class',name)
            assert old.route_class(got,'FIXED')==was,('restoration altered anything beyond class',name)
        if got!=was:changed.append(name)
    return expected,dict(schema='scoped-counterpart-class-restoration-v1',input=pin(routed),fixed_reference=pin(fixed),
        expected=pin(expected),total_nets=len(names),antenna_owners=len(antenna),counterpart_owners=len(extra),
        protected_owners=len(protected),diodes=len(antenna_plan['attachments']),routing_records_preserved=len(routing),
        classes_restored=len(changed),class_changed_names=sorted(changed),counterpart_geometry_retained=True,
        all_unowned_records_preserved=True,all_connection_prefixes_preserved=True,net_order_preserved=True,
        outside_nets_preserved=True,native_import_executed=False,**FLAGS)

def canonical_master_snapshot(snapshot):
    """Match persisted JSON box representation without changing any geometry value."""
    import copy,json
    assert type(snapshot)is dict and type(snapshot['masters'])is dict and snapshot['masters']
    before=snapshot['masters'];masters=copy.deepcopy(before);tuples=0;boxes=0
    for name,m in masters.items():
        assert type(name)is str and '/'in name and set(m)=={'width','height','type','pins'}
        assert all(type(m[k])is int and m[k]>=0 for k in ('width','height'))
        assert type(m['type'])is str and type(m['pins'])is dict
        for name,p in m['pins'].items():
            assert type(name)is str and set(p)=={'io','sigtype','boxes'}
            assert type(p['io'])is str and type(p['sigtype'])is str and type(p['boxes'])is list
            normalized=[]
            for group in p['boxes']:
                assert type(group)is list
                rows=[]
                for box in group:
                    assert type(box)in(list,tuple)and len(box)==5 and type(box[0])is str
                    assert all(type(x)is int for x in box[1:])and box[1]<=box[3]and box[2]<=box[4]
                    tuples+=type(box)is tuple;boxes+=1;rows.append(list(box))
                normalized.append(rows)
            p['boxes']=normalized
    a=json.dumps(before,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    b=json.dumps(masters,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    assert a==b,'serialized master values changed'
    result=dict(snapshot,masters=masters)
    assert all(result[k]is snapshot[k]for k in snapshot if k!='masters')
    return result,dict(schema='native-master-box-json-representation-v1',masters=len(masters),
        boxes=boxes,tuples_converted=tuples,serialized_before=pin(a),serialized_after=pin(b),
        all_geometry_values_and_multiplicity_preserved=True,group_order_preserved=True,**FLAGS)
