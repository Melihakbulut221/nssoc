#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compose the real C9 PLL from native pump and parent RC, with exact graph proof."""
import copy,json,os,subprocess,sys,time
from pathlib import Path
from collections import Counter
from run_cloud_tx_layout_repair import sha
import run_cloud_pll_filter_parent_rc as restore_module
from build_pcie_local_vco_hybrid_v6 import statements,number
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-pll-filter-parent-compose'
def verify_graph(candidate,reference_text,physical,result,save):
    import networkx as nx
    from collections import Counter
    from build_pcie_local_vco_hybrid_v6 import statements,number
    def require(ok,why):
        if not ok:raise ValueError(why)
    model_arity={'npn13g2':4,'sg13_hv_nmos':4,'sg13_hv_pmos':4,'sg13_lv_nmos':4,'sg13_lv_pmos':4,'rppd':3,'rhigh':3,'cap_cmim':2,'ntap1':2,'ptap1':2}
    def parse(text,top):
        definitions={};active=None
        for raw in statements(text):
            w=[v.lower()for v in raw];op=w[0]
            if op=='.subckt':
                require(active is None and w[1] not in definitions,'Duplicate/nested subckt')
                require(len(w[2:])==len(set(w[2:])),'Duplicate formal pin')
                active=w[1];definitions[active]=(w[2:],[]);continue
            if op=='.ends':
                require(active is not None and (len(w)==1 or w[1]==active),'Mismatched ends')
                active=None;continue
            require(active is not None and op[0] in 'xmrcq','Unknown reference statement '+str(w))
            definitions[active][1].append(w)
        require(active is None and top in definitions,'Unclosed/missing top')
        devices=[];wires=[]
        def expand(name,path,actual,stack):
            require(name not in stack,'Recursive hierarchy')
            formal,items=definitions[name];require(len(formal)==len(actual),'Instance arity '+name)
            mapping=dict(zip(formal,actual))
            node=lambda n:mapping[n]if n in mapping else path+'.'+n if path else n
            seen=set()
            for w in items:
                require(w[0] not in seen,'Duplicate instance '+path+'.'+w[0]);seen.add(w[0])
                instance=path+'.'+w[0] if path else w[0]
                if w[0][0] in 'rc' and len(w)==4 and '='not in w[3]:
                    # Primitive numerical R/C records are measured wire
                    # components; modeled intrinsic R/C are kept devices.
                    try:value=number(w[3])
                    except (ValueError,ArithmeticError):value=None
                    if value is not None:
                        require(value>0,'Nonpositive measured RC')
                        wires.append(dict(path=instance,kind=w[0][0],nets=[node(n)for n in w[1:3]],value=w[3]));continue
                at=next((i for i,v in enumerate(w)if '='in v),len(w))-1
                require(at>=2,'Missing model')
                model=w[at];nets=[node(n)for n in w[1:at]]
                params={}
                for p in w[at+1:]:
                    require(p.count('=')==1,'Malformed parameter')
                    k,v=p.split('=');require(k not in params,'Duplicate parameter');number(v);params[k]=v
                if model in definitions:
                    require(not params,'Unexpected hierarchical override')
                    expand(model,instance,nets,stack+[name])
                else:
                    require(model in model_arity and len(nets)==model_arity[model],'Unknown model/arity '+str(w))
                    devices.append(dict(path=instance,model=model,nets=nets,params=params))
        public=definitions[top][0];expand(top,'',public,[])
        require(len({d['path']for d in devices})==len(devices),'Duplicate expanded devices')
        require(len({w['path']for w in wires})==len(wires),'Duplicate expanded wire IDs')
        return public,devices,wires
    public,actual,wires=parse(candidate,'nssoc_parent845_wire_v1')
    reference_ports,expected,no_wires=parse(reference_text,physical['top'])
    require(len(actual)==len(expected)==845 and not no_wires,'845intrinsic census')
    require(set(public)==set(reference_ports)|{'wire_cref'} and len(reference_ports)==17,'Physical public ports')
    def geometry(d):
        p=d['params'];model=d['model']
        if model in ('ptap1','ntap1'):
            a=number(p['a'])if 'a'in p else number(p['w'])*number(p['l'])
            perimeter=number(p['p'])if 'p'in p else 2*(number(p['w'])+number(p['l']))
            return (('a',str(a.normalize())),('p',str(perimeter.normalize())))
        keys=['nx','we','le']if model=='npn13g2'else['w','l']
        return tuple((k,str(number(p[k]).normalize()))for k in keys)
    def collapsed(devices,wire_rows):
        graph=nx.Graph()
        for w in wire_rows:
            if w['kind']=='r':
                require(number(w['value'])>0,'Invalid wire R');graph.add_edge(*w['nets'])
        rename={}
        for component in nx.connected_components(graph):
            fixed=component&set(reference_ports)
            require(len(fixed)<=1,'Shorted public ports '+str(fixed))
            target=next(iter(fixed))if fixed else min(component)
            rename.update({n:target for n in component})
        rows=copy.deepcopy(devices)
        for d in rows:d['nets']=[rename.get(n,n)for n in d['nets']]
        return rows
    macro_names={i['name']for i in physical['instances']};require(len(macro_names)==10,'Actual macro census')
    def macro_owner(d):
        path=d['path']
        owner=path[3:].split('_',1)[0] if path.startswith('x_x') else path.split('.',1)[0][1:]
        require(owner in macro_names,'Device has no physical macro owner '+path)
        return owner
    require(Counter(macro_owner(d)for d in actual)==Counter(macro_owner(d)for d in expected),'Macro census')
    def graph(rows):
        g=nx.Graph()
        for d in rows:
            dn='d:'+d['path'];g.add_node(dn,label=('device',macro_owner(d),d['model'],geometry(d)))
            for i,n in enumerate(d['nets']):
                role='ds'if d['model'].startswith('sg13_') and i in (0,2)else 'ends'if d['model'] in ('rppd','rhigh') and i in (0,1)else i
                tn=dn+':'+str(i);nn='n:'+n
                g.add_node(tn,label=('terminal',role));g.add_node(nn,label=('net',n if n in reference_ports else 'internal'))
                g.add_edge(dn,tn);g.add_edge(tn,nn)
        return g
    want=graph(expected)
    def check_graph(devices,wire_rows):
        require(Counter((d['model'],geometry(d))for d in devices)==Counter((d['model'],geometry(d))for d in expected),'Intrinsic geometry census differs')
        graphs=[want,graph(collapsed(devices,wire_rows))]
        require(len(graphs[0])==len(graphs[1]),'Intrinsic graph node count differs')
        pool={};colors=[]
        for g in graphs:
            c={}
            for n in g:
                key=g.nodes[n]['label'];pool.setdefault(key,len(pool));c[n]=pool[key]
            colors.append(c)
        prior=0
        for i in range(64):
            new=[];pool={}
            for g,c in zip(graphs,colors):
                nc={}
                for n in g:
                    key=(c[n],tuple(sorted(c[v]for v in g[n])));pool.setdefault(key,len(pool));nc[n]=pool[key]
                new.append(nc)
            require(Counter(new[0].values())==Counter(new[1].values()),'Intrinsic connectivity color mismatch round '+str(i))
            colors=new
            if len(pool)==prior:break
            prior=len(pool)
        for g,c in zip(graphs,colors):nx.set_node_attributes(g,c,'refined')
        print('EXACT_GRAPH_SEARCH',len(graphs[0]),len(pool),'classes',flush=True)
        import igraph as ig
        require(ig.__version__=='0.11.9','Unexpected graph solver version')
        if 'bliss_adapter_controls' not in result:
            cycle=ig.Graph.Ring(6);triangles=ig.Graph(n=6,edges=[(0,1),(1,2),(2,0),(3,4),(4,5),(5,3)])
            require(not cycle.isomorphic_bliss(triangles),'Accepted equal-degree nonisomorphic graphs')
            star=ig.Graph.Star(129,mode='undirected',center=0)
            perm=list(range(128,-1,-1));renamed=star.permute_vertices(perm)
            ok,forward,reverse=star.isomorphic_bliss(renamed,return_mapping_12=True,return_mapping_21=True)
            require(ok and set(forward)==set(range(129)) and all(reverse[forward[i]]==i for i in range(129)),'Symmetric graph mapping is not bijective')
            require(all(renamed.are_adjacent(forward[a],forward[b])for a,b in star.get_edgelist()),'Symmetric graph mapping changes edges')
            require(not cycle.isomorphic_bliss(cycle,color1=[1,0,0,0,0,0],color2=[0]*6),'Solver ignored vertex colors')
            result['bliss_adapter_controls']=dict(symmetric_relabelled_positive_vertices=129,
                equal_degree_nonisomorphic_rejected=True,wrong_vertex_color_rejected=True,
                version=ig.__version__,core_version=ig.__igraph_version__,
                extension_sha256=sha(Path(ig._igraph.__file__)),
                reference='https://python.igraph.org/en/0.11.9/api/igraph.GraphBase.html#isomorphic_bliss')
            save()
        node_lists=[list(g)for g in graphs];native=[]
        for g,nodes in zip(graphs,node_lists):
            ids={n:i for i,n in enumerate(nodes)}
            converted=ig.Graph(n=len(nodes),edges=[(ids[a],ids[b])for a,b in g.edges],directed=False)
            require(converted.is_simple() and converted.vcount()==len(g) and converted.ecount()==len(g.edges),'Graph adapter changes input')
            native.append(converted)
        started=time.monotonic()
        ok,forward,reverse=native[0].isomorphic_bliss(native[1],return_mapping_12=True,return_mapping_21=True,
            color1=[graphs[0].nodes[n]['refined']for n in node_lists[0]],
            color2=[graphs[1].nodes[n]['refined']for n in node_lists[1]])
        elapsed=time.monotonic()-started
        result.setdefault('exact_solver_calls',[]).append(dict(method='BLISS',seconds=elapsed,isomorphic=ok,
            vertices=len(graphs[0]),edges=len(graphs[0].edges),colors=len(pool)))
        save()
        require(ok and forward is not None and reverse is not None,'No exact intrinsic graph bijection')
        require(set(forward)==set(range(len(graphs[1]))) and all(reverse[forward[i]]==i for i in range(len(graphs[0]))),'Invalid forward/reverse graph mapping')
        mapping={node_lists[0][i]:node_lists[1][j]for i,j in enumerate(forward)}
        require(mapping is not None and set(mapping)==set(graphs[0]) and set(mapping.values())==set(graphs[1]),'No exact intrinsic graph bijection')
        require(all(graphs[0].nodes[a]['label']==graphs[1].nodes[b]['label']for a,b in mapping.items()),'Bijection changes labels')
        require(len(graphs[0].edges)==len(graphs[1].edges) and all(graphs[1].has_edge(mapping[a],mapping[b])for a,b in graphs[0].edges),'Bijection changes edges')
        return mapping
    mapping=check_graph(actual,wires)
    result['exact_graph']=dict(nodes=len(mapping),devices=845,public_ports=17,mapping=mapping)
    result['macro_census']=dict(Counter(macro_owner(d)for d in actual));save()
    faults=[]
    for name in ('missing_pump_device','wrong_pump_cap_width','pump_up_down_swapped','private_pump_bulk','short_vctrl_avss','wrong_other_width'):
        ds=copy.deepcopy(actual);ws=copy.deepcopy(wires)
        if name=='missing_pump_device':ds.remove(next(d for d in ds if macro_owner(d)=='pump'))
        elif name=='wrong_pump_cap_width':next(d for d in ds if macro_owner(d)=='pump'and d['model']=='cap_cmim')['params']['w']='10u'
        elif name=='wrong_other_width':next(d for d in ds if macro_owner(d)!='pump'and d['model'].startswith('sg13_'))['params']['w']='123u'
        elif name=='private_pump_bulk':
            for d in ds:
                idx={'sg13_hv_nmos':3,'rppd':2,'ptap1':1}.get(d['model'])
                if macro_owner(d)=='pump'and idx is not None:d['nets'][idx]='private_pump_body_fault'
        elif name=='pump_up_down_swapped':
            swap=result['pump_public_mapping'];up=swap['up'];down=swap['down'];require(up!=down,'Fault aliases')
            for d in ds:
                if macro_owner(d)=='pump':d['nets']=[{up:down,down:up}.get(n,n)for n in d['nets']]
            for w in ws:
                if w['path'].startswith(('r_xpump_','c_xpump_')):w['nets']=[{up:down,down:up}.get(n,n)for n in w['nets']]
        else:
            require('vctrl'in reference_ports and 'avss'in reference_ports,'Fault must use actual public pins')
            ws.append(dict(path='r_actual_short_fault',kind='r',nets=['vctrl','avss'],value='1e-6'))
        try:check_graph(ds,ws)
        except ValueError as error:faults.append(dict(name=name,rejection=str(error)))
        else:raise ValueError('Accepted graph fault '+name)
    result['graph_faults']=faults
    diagnostic=dict(actual=actual,collapsed=collapsed(actual,wires),expected=expected,wires=wires)
    (OUT/'graph-diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    return dict(devices=len(actual),wires=len(wires),public_ports=len(reference_ports))

def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,electrical_acquisition_passed=False,full_phy_accepted=False,main_chip_integrated=False,
        scope='Actual C9 PLL845 model: all30native pump devices and84R155C plus fresh98R242C parent wires,815other devices and all other macro RC unchanged; exact intrinsic graph against845device native-LVS-passed physical reference. Substrate remains idealized. No transient/PVT/RF/PHY or mainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def require(ok,why):
        if not ok:raise ValueError(why)
    save()
    try:
        restore_module.OUT=OUT
        restore_module.restore('cloud-results-38856750838-1-pll-filter-parent-rc-9/pll-filter-parent-rc-9-38856750838-1.tar.gz.part0000','046360442a48a5180caecd8f7cdf781c1b338422494dabdee82a1364878916ac',24996230,'cloud-pll-filter-parent-rc/',OUT/'source-rc')
        S=OUT/'source-rc';require(sha(S/'result.json')=='f4fa2c8db83ec2157b30ec7118be9807553b5c80d2edd5e356d82ec43abe2a90','Parent RC summary hash')
        source=json.loads((S/'result.json').read_text());require(source['status']=='PASS_C9_ACTUAL845_PARENT_PLANES_FRESH_WIRE_RC_AND_FAULTS_NOT_ELECTRICAL_ACCEPTANCE','Parent RC gate')
        require(all(sha(S/n)==v for n,v in source['outputs'].items()),'Parent capsule files changed')
        restore_module.restore('cloud-results-38855219697-1-pll-filter-compose-9/pll-filter-compose-9-38855219697-1.tar.gz.part0000','8d6de28ba5081c04f3b476f06590c1a9beb25248d8d269aacdb2ef861b0e82ef',99800,'cloud-pll-filter-compose/',OUT/'source-pump')
        P=OUT/'source-pump';require(sha(P/'result.json')=='1a0f49cda2ed993128e20eaa299f68cd31eaba33db4e52aa98a0a7325b9f11e3','Pump summary hash')
        pump=json.loads((P/'result.json').read_text());require(pump['status']=='PASS_ACTUAL_C9_PUMP_PHYSICAL_MODEL_AND_FAULTS_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE','Pump model gate')
        require(all(sha(P/n)==v for n,v in pump['outputs'].items()),'Pump capsule files changed')
        require(sha(P/'pump30-wire01.spice')=='99b64ceade493f98b9c562b3fd05eb947178002ffd37c16314eb44de8eadc20c','Pump model hash')
        require(sha(P/'anchors03.json')==sha(S/'pump-rc/anchors03.json'),'Different child RC reference planes')
        require(sha(P/'devices01.json')==sha(S/'pump-rc/devices01.json'),'Different native child devices')
        prior=json.loads((S/'prior845/result.json').read_text());original=(S/'prior845/parent845.spice').read_text()
        require(sha(S/'prior845/parent845.spice')=='91364a351fad4d376e6d168d85af6f63ff4076bfecd5af83192492bc514073fc','Original actual845model hash')
        aliases=prior['original_native_alias_proof']['changed_names']
        rows=statements(original);childrows=statements((P/'pump30-wire01.spice').read_text());wire_rows=statements((S/'parent-rc/wires.spice').read_text())
        require(rows[0][0].lower()=='.subckt' and rows[-1][0].lower()=='.ends','Flat original')
        def belongs(w,group):return any(w[0].lower().startswith(k+'_'+group+'_')for k in 'xrc')
        removed_pump=[w for w in rows[1:-1]if belongs(w,'xpump')]
        removed_parent=[w for w in rows[1:-1]if belongs(w,'xparent')]
        kept=[w for w in rows[1:-1]if not belongs(w,'xpump')and not belongs(w,'xparent')]
        require(Counter(w[0][0].lower()for w in removed_pump)==Counter(x=30,r=84,c=155),'Original pump census')
        require(Counter(w[0][0].lower()for w in removed_parent)==Counter(r=98,c=242),'Original parent wire census')
        require(sum(w[0][0].lower()=='x'for w in kept)==815,'815 unchanged devices')
        ports=childrows[0][2:];require(set(ports)=={'sub','vctrl','div_avdd','vco_avdd','up','avss','down','wire_cref'},'Pump ports')
        at=lambda w:next(i for i,v in enumerate(w)if '='in v)-1
        body_index={'sg13_hv_nmos':4,'rppd':3,'ptap1':2}
        old_bulk={w[body_index[w[at(w)].lower()]].lower() for w in removed_pump if w[0][0].lower()=='x'and w[at(w)].lower()in body_index}
        new_bulk={w[body_index[w[at(w)].lower()]].lower() for w in childrows[1:-1]if w[0][0].lower()=='x'and w[at(w)].lower()in body_index}
        require(len(old_bulk)==len(new_bulk)==1 and not new_bulk&set(ports),'Native intrinsic body reference')
        old_body=next(iter(old_bulk));new_body=next(iter(new_bulk))
        require(old_body==aliases.get('a_count_vss','a_count_vss'),'Physical common substrate reference')
        public_map={p:('wire_cref'if p=='wire_cref'else aliases.get('a_pump_'+p,'a_pump_'+p))for p in ports}
        def rename(n):
            n=n.lower()
            if n==new_body:return old_body
            if n in public_map:return public_map[n]
            return 'xpump.'+n
        added_pump=[]
        for w in childrows[1:-1]:
            kind=w[0][0].lower();require(kind in 'xrc','Unexpected pump row')
            index=at(w)if kind=='x'else 3
            require(index>=3 if kind=='x'else len(w)==4,'Pump row syntax')
            added_pump.append([kind.upper()+'_xpump_'+w[0].lower(),*[rename(n)for n in w[1:index]],*w[index:]])
        require(Counter(w[0][0].lower()for w in added_pump)==Counter(x=30,r=84,c=155),'Fresh pump census')
        def intrinsic_signature(w):
            index=at(w);params=[]
            for p in w[index+1:]:
                key,value=p.lower().split('=');params.append((key,str(number(value).normalize())))
            return w[index].lower(),tuple(sorted(params))
        expected=copy.deepcopy([w for w in removed_pump if w[0][0].lower()=='x']);caps=[w for w in expected if w[at(w)].lower()=='cap_cmim'];require(len(caps)==1,'Original capacitor count')
        cap=caps[0];require(number(next(v[2:]for v in cap if v.lower().startswith('w=')))==number('10u'),'Original capacitor width')
        require(number(next(v[2:]for v in cap if v.lower().startswith('l=')))==number('10u'),'Original capacitor length')
        cap[:]=['w=9u'if v.lower().startswith('w=')else'l=9u'if v.lower().startswith('l=')else v for v in cap]
        require(Counter(map(intrinsic_signature,expected))==Counter(intrinsic_signature(w)for w in added_pump if w[0][0].lower()=='x'),'Unexpected intrinsic change beyond capacitor')
        def parent_node(n):
            canonical='wire_cref'if n.lower()=='sub'else n[2:].lower()if n.startswith('P_')else n.lower()
            return aliases.get(canonical,canonical)
        added_parent=[]
        for w in wire_rows[1:-1]:
            require(w[0][0].upper()in'RC'and len(w)==4,'Raw parent wire syntax')
            added_parent.append([w[0][0].upper()+'_xparent_'+w[0].lower(),parent_node(w[1]),parent_node(w[2]),w[3]])
        require(Counter(w[0][0].lower()for w in added_parent)==Counter(r=98,c=242),'Fresh parent census')
        expected_rows=[rows[0],*kept,*added_pump,*added_parent,rows[-1]]
        candidate='\n'.join(' '.join(w)for w in expected_rows)+'\n'
        def preservation(text):
            got=statements(text);require(got==expected_rows,'Changed source component or raw wire value/attachment')
            require(len({w[0].lower()for w in got[1:-1]})==len(got)-2,'Colliding component IDs')
            require([w for w in got[1:-1]if not belongs(w,'xpump')and not belongs(w,'xparent')]==kept,'Changed other macro')
            return True
        preservation(candidate)
        result['pump_public_mapping']=public_map
        result['intrinsic_body_binding']=dict(child=new_body,parent=old_body,substrate_spreading_modeled=False)
        result['component_preservation']=dict(unchanged_devices=815,unchanged_rows=len(kept),unchanged_rows_sha256=__import__('hashlib').sha256(('\n'.join(' '.join(w)for w in kept)+'\n').encode()).hexdigest(),new_pump_devices=30,new_pump_R=84,new_pump_C=155,new_parent_R=98,new_parent_C=242,only_intrinsic_change='cap_cmim w10 l10 to w9 l9 micrometers')
        net=OUT/'parent845.spice';net.write_text(candidate);result['candidate_sha256']=sha(net);save()
        physical=json.loads((S/'current-parent/integrated/result.json').read_text());reference=(S/'current-parent/integrated/schematic.cir').read_text()
        result['counts']=verify_graph(candidate,reference,physical,result,save)
        require(result['counts']==dict(devices=845,wires=8648,public_ports=17),'Full candidate census')
        faults=[]
        for name in ('drop_parent_R','change_parent_R','change_parent_C','move_pump_C','change_pump_R','change_other_device','change_other_wire'):
            w=copy.deepcopy(expected_rows)
            if name=='change_other_device':i=next(i for i,v in enumerate(w)if v[0].lower().startswith('x_')and not belongs(v,'xpump'));w[i].append('m=2')
            else:
                kind='c'if name in ('change_parent_C','move_pump_C')else'r';group='xparent'if 'parent'in name else'xpump'
                if name=='change_other_wire':i=next(i for i,v in enumerate(w)if v[0].lower().startswith('r_')and not belongs(v,'xpump')and not belongs(v,'xparent'))
                else:i=next(i for i,v in enumerate(w)if v[0].lower().startswith(kind+'_'+group+'_'))
                if name.startswith('drop'):w.pop(i)
                elif name.startswith('move'):w[i][1]='wrong_cap_point_fault'
                else:w[i][3]='12345'
            try:preservation('\n'.join(' '.join(row)for row in w)+'\n')
            except ValueError as error:faults.append(dict(name=name,rejection=str(error)))
            else:raise ValueError('Accepted component fault '+name)
        result['component_faults']=faults
        require(sha(net)==result['candidate_sha256'],'Positive model mutated')
        require(all(sha(S/n)==v for n,v in source['outputs'].items())and all(sha(P/n)==v for n,v in pump['outputs'].items()),'Inputs changed')
        result['status']='PASS_C9_ACTUAL845_MODEL_EXACT_GRAPH_AND_COMPONENT_FAULTS_NOT_ELECTRICAL_ACCEPTANCE'
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
