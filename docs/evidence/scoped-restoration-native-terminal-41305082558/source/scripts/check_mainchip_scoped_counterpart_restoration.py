"""Actual scoped-restoration core with original full scope counts and mutations."""
import copy,json,traceback
from pathlib import Path
import mainchip_scoped_counterpart_restoration as core
import mainchip_targeted_counterpart_routing as scope_core
def fixture():
    antenna=['a'+str(i)for i in range(608)]
    extra=['x'+str(i)for i in range(220)]
    protected=['clk'+str(i)for i in range(1691)]
    names=antenna+extra+protected+['untouched','unwired']
    attachments={'diode'+str(i):antenna[i%608]for i in range(1351)}
    p=dict(mutable_nets=antenna,protected_nets=protected,attachments=attachments)
    s=dict(schema='mainchip-separate-counterpart-routing-scope-v1',antenna_nets=antenna,
        counterpart_nets=extra,routing_nets=sorted(antenna+extra),protected_nets=protected,
        antenna_plan_sha256=scope_core.digest(p),attachment_count=1351,native_execution_authorized=False,**core.FLAGS)
    classes={n:(None if n=='unwired'else'FIXED'if n=='clk0'else'ROUTED')for n in names if n not in antenna}
    def rec(n,k,x=10):
        lead='- '+n+' ( '+n+'_inst A )'
        return (lead+' ;\n'if k is None else lead+'\n  + '+k+' Metal2 ( '+str(x)+' 20 ) ( 30 20 ) ;\n').encode()
    fixed={n:rec(n,None if n=='unwired'else'ROUTED'if n in antenna else'FIXED')for n in names}
    post={n:(rec(n,'ROUTED',11)if n in antenna+extra else fixed[n])for n in names}
    def render(rows):
        return b'VERSION 5.8 ;\nNETS '+str(len(rows)).encode()+b' ;\n'+b''.join(rows.values())+b'END NETS\nEND DESIGN\n'
    return p,s,classes,fixed,post,render,rec
def main():
    p,s,classes,fixed,post,render,rec=fixture()
    a,b=render(fixed),render(post)
    result,proof=core.plan(a,b,classes,p,s)
    assert proof['total_nets']==2521 and proof['routing_records_preserved']==828 and proof['diodes']==1351 and proof['protected_owners']==1691
    parsed=core.old.parse_def(result)['records']
    for n in s['routing_nets']:assert parsed[n]==post[n]
    assert core.old.classes(parsed['clk0'])=='FIXED'and core.old.classes(parsed['clk1'])=='ROUTED'and parsed['unwired']==post['unwired']
    assert all(proof[k]is False for k in core.FLAGS)and proof['native_import_executed']is False
    controls=['full608plus220ownership_restored_with_original_function','all828new_route_records_byte_exact','original_FIXED_and_ROUTED_classes_retained','unwired_record_unchanged','all_acceptance_flags_false']
    def reject(label,fn):
        try:fn()
        except (AssertionError,KeyError,ValueError):controls.append(label);return
        raise AssertionError('failed to reject '+label)
    def run(c=None,q=None,t=None,x=None,y=None):
        return core.plan(a if x is None else render(x),b if y is None else render(y),classes if c is None else c,p if q is None else q,s if t is None else t)
    def changed(base,key,value):
        d=copy.deepcopy(base);d[key]=value;return d
    reject('missing_original_class',lambda:run(c={k:v for k,v in classes.items()if k!='clk1'}))
    reject('extra_original_class',lambda:run(c=changed(classes,'a0','ROUTED')))
    reject('wrong_counterpart_original_class',lambda:run(c=changed(classes,'x0','FIXED')))
    reject('invalid_original_class',lambda:run(c=changed(classes,'clk1','INVALID')))
    reject('counterpart_still_FIXED',lambda:run(y=changed(post,'x0',rec('x0','FIXED',11))))
    reject('counterpart_COVER',lambda:run(y=changed(post,'x0',rec('x0','COVER',11))))
    reject('counterpart_unwired',lambda:run(y=changed(post,'x0',rec('x0',None))))
    reject('antenna_fixed',lambda:run(y=changed(post,'a0',rec('a0','FIXED',11))))
    reject('clock_class_changed',lambda:run(y=changed(post,'clk1',rec('clk1','ROUTED'))))
    reject('clock_geometry_changed',lambda:run(y=changed(post,'clk1',rec('clk1','FIXED',12))))
    reject('unowned_geometry_changed',lambda:run(y=changed(post,'untouched',rec('untouched','FIXED',12))))
    reject('counterpart_connection_changed',lambda:run(y=changed(post,'x0',post['x0'].replace(b'x0_inst',b'wrong_inst'))))
    reject('antenna_connection_changed',lambda:run(y=changed(post,'a0',post['a0'].replace(b'a0_inst',b'wrong_inst'))))
    reject('clock_connection_changed',lambda:run(y=changed(post,'clk0',post['clk0'].replace(b'clk0_inst',b'wrong_inst'))))
    reject('unwired_gained_wire',lambda:run(y=changed(post,'unwired',rec('unwired','ROUTED'))))
    reject('lost_net',lambda:run(y={k:v for k,v in post.items()if k!='untouched'}))
    reject('extra_net',lambda:run(y=changed(post,'unknown',rec('unknown','ROUTED'))))
    reject('changed_net_order',lambda:run(y=dict(reversed(list(post.items())))))
    reject('outside_nets_changed',lambda:core.plan(a,b.replace(b'VERSION 5.8',b'VERSION 5.7'),classes,p,s))
    reject('mixed_wire_clause',lambda:run(y=changed(post,'x0',post['x0'].replace(b' ;',b'\n + FIXED Metal3 ( 1 2 ) ( 3 4 ) ;'))))
    reject('plan_digest_changed',lambda:run(q=changed(p,'unauthorized','value')))
    reject('counterpart_dropped',lambda:run(t=changed(s,'counterpart_nets',s['counterpart_nets'][:-1])))
    reject('protected_scope_dropped',lambda:run(t=changed(s,'protected_nets',s['protected_nets'][:-1])))
    reject('routing_union_changed',lambda:run(t=changed(s,'routing_nets',s['routing_nets'][:-1])))
    reject('native_scope_authority_changed',lambda:run(t=changed(s,'native_execution_authorized',True)))
    for k in core.FLAGS:reject('scope_acceptance_'+k,lambda k=k:run(t=changed(s,k,True)))
    immutable=(json.dumps(classes,sort_keys=True),json.dumps(p,sort_keys=True),json.dumps(s,sort_keys=True),a,b)
    core.plan(a,b,classes,p,s)
    assert immutable==(json.dumps(classes,sort_keys=True),json.dumps(p,sort_keys=True),json.dumps(s,sort_keys=True),a,b)
    controls.append('all_callers_and_input_bytes_unchanged')
    out=Path('scoped-restoration-controls');out.mkdir(exist_ok=False)
    (out/'controls.json').write_text(json.dumps(dict(status='PASS_SCOPED_CLASS_RESTORATION_SOURCE_CONTROLS',count=len(controls),checks=controls,native_executed=False),indent=2)+'\n')
    print(json.dumps(dict(count=len(controls),status='PASS_SCOPED_CLASS_RESTORATION_SOURCE_CONTROLS')))
if __name__=='__main__':
    try:main()
    except BaseException as exc:
        out=Path('scoped-restoration-controls');out.mkdir(exist_ok=True)
        (out/'failure.json').write_text(json.dumps(dict(error=repr(exc),traceback=traceback.format_exc()),indent=2)+'\n')
        raise
