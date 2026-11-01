"""Diagnose exact master descriptors; never change a layout or acceptance gate."""
import copy,gc,hashlib,json
FLAGS=dict(layout_modified=False,native_cad_executed=False,physical_acceptance=False,timing_accepted=False,full_phy_accepted=False)
def json_pin(value):
    h=hashlib.sha256();size=0
    for part in json.JSONEncoder(sort_keys=True,separators=(',',':'),allow_nan=False).iterencode(value):
        raw=part.encode();size+=len(raw);h.update(raw)
    return dict(bytes=size,sha256=h.hexdigest())
def validate(masters):
    assert type(masters)is dict and masters,'nonempty master map'
    for name,m in masters.items():
        assert type(name)is str and '/'in name and set(m)=={'width','height','type','pins'}
        assert all(type(m[k])is int and m[k]>=0 for k in ('width','height'))
        assert type(m['type'])is str and type(m['pins'])is dict
        for name,p in m['pins'].items():
            assert type(name)is str and set(p)=={'io','sigtype','boxes'}
            assert type(p['io'])is str and type(p['sigtype'])is str and type(p['boxes'])is list
            for mpin in p['boxes']:
                assert type(mpin)is list
                for box in mpin:
                    assert type(box)is list and len(box)==5 and type(box[0])is str
                    assert all(type(x)is int for x in box[1:])and box[1]<=box[3]and box[2]<=box[4]
def sorted_mpin_groups(master):
    result=copy.deepcopy(master)
    for pin in result['pins'].values():
        pin['boxes']=sorted(pin['boxes'],key=lambda x:json.dumps(x,sort_keys=True,separators=(',',':')))
    return result
def compare(before,after):
    validate(before);validate(after)
    common=set(before)&set(after);added=sorted(set(after)-set(before));removed=sorted(set(before)-set(after))
    changed=sorted(n for n in common if before[n]!=after[n])
    order_only=[n for n in changed if sorted_mpin_groups(before[n])==sorted_mpin_groups(after[n])]
    details={n:dict(before=before.get(n),after=after.get(n),only_mpin_group_order=n in order_only)for n in sorted(set(changed)|set(added)|set(removed))}
    return dict(before_count=len(before),after_count=len(after),added=added,removed=removed,changed=changed,
        mpin_order_only=order_only,other_changed=sorted(set(changed)-set(order_only)),
        exact_equal=before==after,all_differences_only_mpin_order=bool(changed)and not added and not removed and changed==order_only,
        **FLAGS),details
def projection(path):
    with path.open()as f:value=json.load(f)
    assert set(value)=={'nets','instances','masters','protected','block','immutable','diode_template','def_pin','clock_record_pins'}
    assert len(value['nets'])==143820 and len(value['protected'])==1691
    masters=value['masters'];validate(masters)
    result=dict(net_count=len(value['nets']),instance_count=len(value['instances']),protected_count=len(value['protected']),
        nonroute_fields={k:json_pin(v)for k,v in value.items()if k not in ('nets','masters','def_pin')},
        masters=masters,masters_pin=json_pin(masters),def_pin=value['def_pin'])
    del value;gc.collect()
    return result
