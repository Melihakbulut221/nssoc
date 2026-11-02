#!/usr/bin/env python3
"""Verify transport of prior LVS correspondences through complete native identities."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='docs/evidence/cdr-current-domain-parent-map.json'
CURRENT='docs/evidence/cdr-clock-access-domain-parent-map.json'
OLD='docs/evidence/clock-access16-old-native-identity.json'
NEW='docs/evidence/clock-access16-new-native-identity.json'
def need(ok,msg):
    if not ok:raise AssertionError(msg)
def verify(old,new,original,current):
    def devices(identity):
        rows=identity['locations']['devices']
        result={r['native_id']:r for r in rows}
        need(len(result)==len(rows)==500,'all500 unique native devices')
        return result
    a,b=devices(old),devices(new)
    need(set(a)==set(b),'complete identity set')
    oldpaths={r['native_device']:r['stable_path']for r in old['paths']}
    newpaths={r['native_device']:r['stable_path']for r in new['paths']}
    need(len(oldpaths)==500 and oldpaths==newpaths,'all physical hierarchy transforms and ordinals')
    original_pairs={r['layout']['id']:r for r in original['pairs']}
    current_pairs={r['layout']['id']:r for r in current['pairs']}
    need(len(original_pairs)==len(current_pairs)==500 and set(a)==set(original_pairs)==set(current_pairs),'all LVS pairs')
    forward={};reverse={};changed=[];terminals=0
    def bind(x,y):
        need(forward.setdefault(x,y)==y and reverse.setdefault(y,x)==x,'bijective complete net ownership')
    for did in sorted(a):
        x,y=a[did],b[did];p,q=original_pairs[did],current_pairs[did]
        need(x['model']==y['model'] and {'npn13G2':'npn13g2'}.get(x['model'],x['model'])==p['layout']['model']==q['layout']['model'],'unchanged primitive model')
        need(x['parameters']==y['parameters']==p['layout']['parameters']==q['layout']['parameters'],'unchanged physical parameters')
        for key in ('schematic','loaded_instance','loaded_parameters','status'):
            need(p[key]==q[key],'unchanged actual LVS correspondence '+key)
        need(p['status']=='Match','original matched LVS pair')
        for key in p['layout']:
            if key!='terminals':need(p['layout'][key]==q['layout'][key],'unchanged layout device identity')
        xt={t['name']:t for t in x['terminals']};yt={t['name']:t for t in y['terminals']}
        need(len(xt)==len(x['terminals'])and len(yt)==len(y['terminals'])and set(xt)==set(yt)==set(p['layout']['terminals'])==set(q['layout']['terminals']),'unique complete terminals')
        for name in xt:
            u,v=xt[name],yt[name];op=p['layout']['terminals'][name];np=q['layout']['terminals'][name]
            need(u['native_layers']==v['native_layers'],'unchanged transistor terminal geometry')
            need((op['cluster'],op['name'])==(u['native_cluster'],u['net']),'old LVS owner matches independent old native observation')
            need((np['cluster'],np['name'])==(v['native_cluster'],v['net'])and np['expanded_name']==np['name'],'current owner matches independent new native observation')
            bind((u['native_cluster'],u['net']),(v['native_cluster'],v['net']))
            terminals+=1
            if op!=np:changed.append(dict(device=did,terminal=name,old=op,new=np))
    pa={p['name']:p for p in old['native_pins']};pb={p['name']:p for p in new['native_pins']}
    need(len(pa)==len(pb)==25 and set(pa)==set(pb),'all25 unique public ports')
    for name in pa:
        need(pa[name]['full_partition']==pb[name]['full_partition'],'complete named public terminal partition')
    need(terminals==1446,'all1446 terminal identities')
    for key,pair in current['critical'].items():need(pair==current_pairs[int(key)],'critical map matches full map')
    return dict(status='PASS_TRANSPORTED_LVS_CORRESPONDENCE_ALL500_NATIVE_IDENTITIES',
        devices=500,terminals=terminals,ports=25,changed_terminal_labels=changed,
        net_bijection=[dict(old=list(k),new=list(v))for k,v in sorted(forward.items())],
        new_native_lvs_pairing_generated=False,physical650_accepted=False,full_phy_accepted=False)
def check(root=ROOT,with_faults=False):
    root=Path(root)
    old,new,original,current=[json.loads((root/p).read_bytes())for p in (OLD,NEW,BASE,CURRENT)]
    report=verify(old,new,original,current)
    if with_faults:
        rejected=[]
        for label in ('physical-width','physical-transform','wrong-current-owner','wrong-schematic-pair','public-port-partition','merged-net'):
            a,b,p,q=copy.deepcopy((old,new,original,current))
            if label=='physical-width':b['locations']['devices'][0]['parameters']['W']+=1
            elif label=='physical-transform':b['paths'][0]['stable_path']['full_transform_um']='r0 *1 0,0'
            elif label=='wrong-current-owner':q['pairs'][0]['layout']['terminals'][next(iter(q['pairs'][0]['layout']['terminals']))]['cluster']+=1000
            elif label=='wrong-schematic-pair':q['pairs'][0]['schematic']=copy.deepcopy(q['pairs'][1]['schematic'])
            elif label=='public-port-partition':b['native_pins'][0]['full_partition']['public_ports']=['wrong']
            else:
                device=b['locations']['devices'][0];u,v=device['terminals'][:2]
                u['native_cluster'],u['net']=v['native_cluster'],v['net']
                pair=next(r for r in q['pairs']if r['layout']['id']==device['native_id'])
                pair['layout']['terminals'][u['name']].update(cluster=u['native_cluster'],name=u['net'],expanded_name=u['net'])
            try:verify(a,b,p,q)
            except (AssertionError,KeyError):rejected.append(label)
            else:raise AssertionError('accepted invalid identity '+label)
        report['rejected']=rejected
    return report
