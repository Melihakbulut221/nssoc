#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Complete saved marker/source classification; no native database or route execution."""
import collections,decimal,json,re
import mainchip_original_clock_restoration as c
import mainchip_original_clock_drc as drc

def unique(pairs):
    out={}
    for k,v in pairs:
        assert k not in out,'Duplicate JSON key'
        out[k]=v
    return out

def json_read(raw):
    return json.loads(raw,object_pairs_hook=unique)

def selected_plan(raw):
    r=json_read(raw)
    assert r['status']=='PASS_EXACT_ORIGINAL_CLOCK_RESTORE_REQUIRES_ZERO_DRC_DETERMINATION'
    assert r['source_inputs_unchanged']is True
    assert r['restored_odb_sha256']=='2d75a1e620c74cbe24a762683db17b1708aaac003a0b3e4b54099c769748c7da'
    g=r['original_gate']['result']
    assert g['clock_or_fixed_nets']==1691 and g['all_source_clock_and_fixed_records_preserved']is True
    p=r['plan'];names=p['all_clock_names'];changed=p['changed_names']
    assert names==sorted(set(names)) and len(names)==1691
    assert changed==sorted(set(changed)) and len(changed)==218 and set(changed)<=set(names)
    assert c.digest(c.canonical(names))==p['all_clock_names_sha256']
    assert c.digest(c.canonical(changed))==p['changed_names_sha256']
    assert p['expected_def_sha256']=='55fbc30c508b42a27301054206a8820b020bbbb3a525beeef0aed73692870ece'
    return p

def net_inventory(raw,selected):
    records=c.parse_def(raw)['records'];selected=set(selected)
    assert selected<=records.keys(),'Selected clock/fixed net missing from DEF'
    result={}
    for n,record in records.items():
        uses=re.findall(rb'\+ USE ([A-Z]+)(?=\s)',record)
        assert len(uses)<=1,'Multiple net USE fields'
        kind=uses[0].decode()if uses else None
        assert kind is None or kind in ('SIGNAL','CLOCK','POWER','GROUND','ANALOG','RESET','SCAN','TIEOFF'),'Unknown net USE'
        assert kind!='CLOCK'or n in selected,'Unselected native CLOCK net'
        result[n]=dict(selected_clock_fixed=n in selected,use=kind)
    return result

def markers(raw,measurement):
    drc.bind_serialized_markers(measurement,raw)
    tree=json_read(raw);rows=[]
    def walk(node,path):
        for index,m in enumerate(node.get('violations',[])):
            rows.append((path,index,m))
        for name,child in node.get('category',{}).items():walk(child,path+[name])
    walk(tree[drc.CATEGORY],[drc.CATEGORY])
    assert len(rows)==measurement['marker_count']
    return rows

def text_value(x):
    assert type(x)is str and x and not any(ch in x for ch in '\r\n\0'),'Unsupported text field'
    return x

def source_rows(marker):
    sources=marker['sources']
    # The pinned Boost property_tree serializes an empty child as an empty string.
    if sources=='':return []
    assert type(sources)is list and sources,'Malformed sources'
    for s in sources:
        assert type(s)is dict and s.get('type')in ('net','inst','iterm','bterm','obstruction'),'Unknown source type'
        assert set(s)==({'type'}if s['type']=='obstruction'else {'type','name'}),'Source schema'
        if 'name'in s:text_value(s['name'])
    return sources

def marker_body(marker):
    required={'visited','visible','waived','shape','sources'}
    assert required<=set(marker)<=required|{'comment','line_number','layer'},'Unknown marker field'
    for k in ('visited','visible','waived'):assert marker[k]in ('true','false')and type(marker[k])is str
    if 'comment'in marker:text_value(marker['comment'])
    if 'layer'in marker:text_value(marker['layer'])
    if 'line_number'in marker:assert re.fullmatch(r'[1-9][0-9]*',marker['line_number'])
    shape=marker['shape'];assert type(shape)is list and shape,'Marker has no independently bounded shape'
    points=[]
    for s in shape:
        assert set(s)=={'type','points'}and s['type']in ('point','line','box','polygon'),'Shape schema'
        ps=s['points'];assert type(ps)is list
        count={'point':1,'line':2,'box':2}.get(s['type'])
        assert (len(ps)==count)if count is not None else (len(ps)>=3)
        parsed=[]
        for p in ps:
            assert set(p)=={'x','y'}
            assert all(type(p[k])is str and re.fullmatch(r'-?[0-9]+\.[0-9]{4}',p[k])for k in ('x','y')),'Noncanonical coordinate'
            parsed.append(tuple(decimal.Decimal(p[k])for k in ('x','y')))
        if s['type']=='box':assert parsed[0][0]<=parsed[1][0]and parsed[0][1]<=parsed[1][1],'Inverted box'
        points+=parsed
    bbox=[min(p[0]for p in points),min(p[1]for p in points),max(p[0]for p in points),max(p[1]for p in points)]
    return source_rows(marker),[format(x,'.4f')for x in bbox]

def expected_tr(path,marker):
    sources,bbox=marker_body(marker)
    line='violation type: '+path[-1]+'\n\tsrcs:'
    for s in sources:
        line+=' '+s['type']+(':' + s['name']if 'name'in s else ': ')
    line+='\n'
    if marker.get('comment'):line+='\tcomment: '+marker['comment']+'\n'
    line+='\tbbox = ('+bbox[0]+', '+bbox[1]+') - ('+bbox[2]+', '+bbox[3]+') on Layer '+marker.get('layer','-')+'\n'
    return line.encode()

def classify_sources(sources,inventory):
    resolved=[];unresolved=[]
    for s in sources:
        if s['type']!='net':
            unresolved.append(dict(source=s,reason='Non-net source has no proven net ownership in this saved text'))
        elif s['name']not in inventory:
            unresolved.append(dict(source=s,reason='Net absent from complete restored NETS inventory'))
        else:
            row=inventory[s['name']]
            if row['selected_clock_fixed']:role='clock'
            elif row['use']=='SIGNAL':role='signal'
            else:
                unresolved.append(dict(source=s,reason='Unselected net USE is not explicitly SIGNAL',use=row['use']));continue
            resolved.append(dict(name=s['name'],role=role,use=row['use']))
    clocks=sorted({r['name']for r in resolved if r['role']=='clock'})
    signals=sorted({r['name']for r in resolved if r['role']=='signal'})
    pairs=[]
    if len(clocks)>=2:pairs.append('clock-clock')
    if clocks and signals:pairs.append('clock-signal')
    if len(signals)>=2:pairs.append('signal-signal')
    if unresolved or not sources:group='missing-or-unresolved-source'
    elif len(clocks)>=2 and signals:group='mixed-clock-clock-and-signal'
    elif clocks and signals:group='clock-signal'
    elif len(clocks)>=2:group='clock-clock'
    elif len(signals)>=2:group='signal-signal'
    elif clocks:group='single-clock-net'
    elif signals:group='single-signal-net'
    else:group='missing-or-unresolved-source'
    return dict(group=group,known_pair_classes=pairs,clock_names=clocks,signal_names=signals,
        resolved_source_entries=resolved,unresolved_source_entries=unresolved,
        duplicate_source_entries=len(sources)-len({c.canonical(s)for s in sources}),
        missing_sources=not sources)

def analyze(raw,report,measurement,inventory,selected):
    assert set(selected)=={n for n,r in inventory.items()if r['selected_clock_fixed']},'Selected membership differs'
    rows=markers(raw,measurement);expected=[];result=[];counts=collections.Counter();by_category={}
    for ordinal,(path,index,m)in enumerate(rows):
        sources,bbox=marker_body(m);tr=expected_tr(path,m);expected.append(tr)
        ownership=classify_sources(sources,inventory)
        entry=dict(ordinal=ordinal,category_path=path,category_local_index=index,
            marker=m,marker_canonical_sha256=c.digest(c.canonical(m)),TR_record_sha256=c.digest(tr),
            bbox_microns=bbox,ownership=ownership)
        result.append(entry);counts[ownership['group']]+=1
        key=json.dumps(path,separators=(',',':'));by_category.setdefault(key,collections.Counter())[ownership['group']]+=1
    assert b''.join(expected)==report,'Complete JSON/TR category/source/shape/comment sequence differs'
    assert sum(counts.values())==len(result)==measurement['marker_count']
    clock_pairs=[r['ordinal']for r in result if 'clock-clock'in r['ownership']['known_pair_classes']]
    unresolved=[r['ordinal']for r in result if r['ownership']['group']=='missing-or-unresolved-source']
    return dict(status='COMPLETE_SAVED_MARKER_SOURCE_CLASSIFICATION_NOT_ROUTE_OR_TIMING_ACCEPTANCE',
        marker_count=len(result),exclusive_group_counts=dict(counts),
        category_group_counts={k:dict(v)for k,v in by_category.items()},
        known_clock_clock_marker_ordinals=clock_pairs,unresolved_marker_ordinals=unresolved,
        potential_preserved_clock_conflict=bool(clock_pairs),records=result,
        exact_complete_JSON_TR_reconstruction=True,selected_clock_fixed_count=len(selected),
        net_inventory_count=len(inventory),selected_names_sha256=c.digest(c.canonical(sorted(selected))),
        selected_role_meaning='clock means exact original selected CLOCK/fixed/clock-pin/clkbuf set; it is not a new semantic clock inference.',
        same_net_open_or_self_geometry_not_pairwise_proof=True,
        geometric_source_ownership_not_independently_recomputed=True,
        routing_feasibility_proven=False,accepted=False,full_phy_accepted=False,final_timing_complete=False)
