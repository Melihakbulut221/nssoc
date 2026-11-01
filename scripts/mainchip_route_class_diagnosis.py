#!/usr/bin/env python3
"""Inspect actual protected DEF records; never repair or accept a layout."""
import hashlib,json
import mainchip_original_clock_restoration as original
def digest(b):return hashlib.sha256(b).hexdigest()
def classify(record):
    hits=list(original.ROUTE.finditer(record))
    if not hits:
        assert not any(x in record for x in (b'+ ROUTED',b'+ FIXED',b'+ COVER')), 'unsupported wire syntax'
        return None
    assert len(hits)==1,'mixed wire clauses require separate qualification'
    return original.classes(record)
def normalize(record):
    return original.route_class(record,'ROUTED') if classify(record) is not None else record
def analyze(before,after,classes,mutable,counterparts=()):
    assert isinstance(classes,dict) and classes and isinstance(mutable,list)
    assert len(mutable)==len(set(mutable)) and not set(classes)&set(mutable),'selected/mutable overlap'
    extra=set(counterparts)
    assert len(extra)==len(counterparts) and extra<=set(classes) and not extra&set(mutable),'counterpart ownership'
    assert all(classes[n]=='ROUTED'for n in extra),'counterpart original class'
    a,b=original.parse_def(before),original.parse_def(after)
    assert set(a['records'])==set(b['records']),'net census'
    assert set(classes)|set(mutable)==set(a['records']),'complete selected/mutable partition'
    assert all(v in (None,'ROUTED','FIXED','COVER')for v in classes.values())
    counts={};changes={};pins={};strict_failures=[]
    for name,kind in classes.items():
        x,y=a['records'][name],b['records'][name];xc,yc=classify(x),classify(y)
        assert xc==('FIXED' if kind is not None else None),('actual pre-route overlay class',name,xc,kind)
        same=normalize(x)==normalize(y)
        prefix_equal=original.prefix(x)==original.prefix(y)
        row=dict(routing_counterpart=name in extra,original_class=kind,before_class=xc,after_class=yc,record_equal=x==y,
            class_normalized_record_equal=same,connection_prefix_equal=prefix_equal,
            before_sha256=digest(x),after_sha256=digest(y),
            before_normalized_sha256=digest(normalize(x)),after_normalized_sha256=digest(normalize(y)))
        pins[name]=row
        transition=str(xc)+'->'+str(yc);counts[transition]=counts.get(transition,0)+1
        if x!=y:changes[name]=row
        if (kind is None and yc is not None) or (kind is not None and yc!='FIXED'):strict_failures.append(name)
    try:
        original.restore_classes(after,classes)
        original_failure=None
    except AssertionError as exc:original_failure=repr(exc)
    assert bool(strict_failures)==(original_failure is not None),'actual original restorer mismatch'
    sa,sb=a['section'],b['section']
    result=dict(status='COMPLETE_READ_ONLY_CLASS_DIAGNOSIS',selected_records=len(classes),mutable_records=len(mutable),
        total_records=len(a['records']),counterpart_records=len(extra),routing_records=len(set(mutable)|extra),net_order_equal=list(a['records'])==list(b['records']),
        outside_nets_bytes_equal=before[:sa[0]]+before[sa[1]:]==after[:sb[0]]+after[sb[1]:],
        class_transitions=counts,changed_records=len(changes),strict_restorer_failures=len(strict_failures),
        first_strict_failure=strict_failures[0]if strict_failures else None,original_restore_exception=original_failure,
        class_normalized_changed_records=sum(not r['class_normalized_record_equal']for r in pins.values()),
        connection_prefix_changes=sum(not r['connection_prefix_equal']for r in pins.values()),
        strict_failures_outside_counterparts=sum(n not in extra for n in strict_failures),
        normalized_changes_outside_counterparts=sum(not r['class_normalized_record_equal']for n,r in pins.items()if n not in extra),
        normalized_counterpart_changes=sum(not r['class_normalized_record_equal']for n,r in pins.items()if n in extra),
        full_phy_accepted=False,physical_acceptance=False,timing_accepted=False,layout_modified=False)
    return result,pins,changes
