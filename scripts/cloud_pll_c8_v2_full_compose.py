#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Compose actual new full845 PLL geometry and freshly extracted parent wires; exact graph proof."""
import copy,json,os,re,time
from decimal import Decimal
from pathlib import Path
from collections import Counter
import compare_cloud_routed_endpoints as reports
from build_pcie_local_vco_hybrid_v6 import statements,number
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/cloud-pll-c8-v2-full-compose'
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
        return tuple((k,str((number(p[k])if k=='nx'else number(p[k]).quantize(Decimal('1e-12'))).normalize()))for k in keys)
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
    assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
    result=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],accepted=False,qualified_pex=False,full_phy_accepted=False,mainchip_integrated=False,electrical_acquisition_passed=False,scope='Actual C8new845PLL layout: actual30device84R155C pump with8um cap plus fresh98R242C parent wires; both native91/382R649C dividers and815other devices retained from verified latest845model. Exact whole845graph against nativeLVS-passed new physical reference. Finite tap electrical values remain unchanged; their geometry evidence comes from same-GDS native extraction. One-picometer comparison grid for serialized linear dimensions,1000x finer than GDS. No qualified substrate/RF PEX, transient, x4 or mainchip acceptance.')
    def save():(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def require(ok,why):
        if not ok:raise ValueError(why)
    save()
    try:
        selected=('parent-rc/wires.spice','parent-wires/result.json','prior845/result.json','current-parent/integrated/result.json','current-parent/integrated/schematic.cir','current-parent/physical/lvs_flat/audit.json','pump-rc/anchors03.json','pump-rc/devices01.json')
        rc,receipt=reports.restore_report('pll-c8-v2-parent-rc',39006326123,'eea8dc6473bc3156f95b012eb2e6bbd9bf6f281c01a922239110a86f996f8c50','ed9426eb944fa8047664d8d50588d6d8a570564f4e8d75a75339f43876775fa0',OUT/'fresh-rc',selected)
        result['fresh_rc_source']=receipt
        require(rc['status']=='PASS_C8_DIVIDER_V2_ACTUAL845_PARENT_PLANES_FRESH_WIRE_RC_AND_FAULTS_NOT_ELECTRICAL_ACCEPTANCE','Actual new-layout RC did not pass')
        require(rc['audit']['actual_exported_resistors']==98 and rc['audit']['actual_exported_capacitors']==242,'Native parent RC census')
        require(len(rc['controls']['negative_controls'])==8 and rc['controls']['status']=='PASS_PARENT_RC_EIGHT_ACTUAL_CORRUPTION_CONTROLS','Actual raw fault controls')
        require(rc['wire_binding']['reference_plane_proof']['divider_plane_fault']['rejected']and len(rc['wire_binding']['reference_plane_proof']['divider_child_model_matches'])==14,'New divider planes')
        old,receipt=reports.restore_report('pll-divider-v2-full-compose',38981800336,'a17fde2bd57f2710327bd84156ee8c9354187ae997f27ff93dd332d84f6a62a3','9b861472d9c80e4c6c7e43bb5c22a5eafd8e82a0202e51c770c2a2052f72c861',OUT/'prior-model',('parent845.spice',))
        require(old['source_unchanged']and len(old['component_faults'])==7 and len(old['graph_faults'])==6 and all(c['rejected']for c in old['component_faults']),'Prior two-divider model gates')
        require(sha(OUT/'prior-model/parent845.spice')==old['candidate_sha256']=='d86f4716070f22b36f3fafb9b5d789f2dd029552aefafbedbab8aebdfb0cb85b','Two-divider model hash');result['prior_model_source']=receipt
        child,receipt=reports.restore_report('pll-divider-load3p2v2-compose',38978426268,'6bcb802e6e63b8120e298ef34eb17b27cf1928932fbc28d99c17eb0f82e67baa','f8d5e0a0d4d5f7f681757b732f5a3de81ce2f803e7b5295ad6b12037e7820f40',OUT/'divider',('native.json','divider91-wire.spice'))
        require(child['source_unchanged']and child['gds_sha256']=='265d5245f5b406aa20c20647afbe9d87ad9e8f1493cfe3cae3fed9d64885a71b','Exact native child geometry');result['divider_source']=receipt
        require(len(child['intrinsic_controls'])==11 and len(child['composition_controls'])==17 and all(c['rejected']for c in child['intrinsic_controls']+child['composition_controls']),'All28child model controls')
        prior=json.loads((OUT/'fresh-rc/prior845/result.json').read_text());aliases=prior['original_native_alias_proof']['changed_names']
        c9url='https://github.com/Melihakbulut221/nssoc/releases/download/cloud-results-38857275591-1-pll-filter-parent-compose-9/pll-filter-parent-compose-9-38857275591-1.summary.json'
        fetch(c9url,'05211617b84f8545bbaec4acfff8a6bc5fde01d795f00f96dd33256ca136a432',OUT/'c9-source.json')
        result['pump_public_mapping']=json.loads((OUT/'c9-source.json').read_text())['pump_public_mapping']
        pump,receipt=reports.restore_report('pll-filter-compose-8',39005678827,'7fc3b8c05a051059703b562e762af24f713d05dc47d9a3264ebce048e760c17e','96f0a830bf51989dce7592ef56e2425a446df9a8a9ca00522684fbbe4cb87072',OUT/'pump',('pump30-wire01.spice','anchors03.json','devices01.json'))
        require(pump['status']=='PASS_ACTUAL_C8_PUMP_PHYSICAL_MODEL_AND_FAULTS_NOT_PARENT_OR_ELECTRICAL_ACCEPTANCE','C8 native child model gate')
        P=OUT/'pump';result['pump_source']=receipt
        require(sha(P/'pump30-wire01.spice')=='33fa7b1eb4fe3cd3017a3ce6ffc0a411d364e19100d696351970a021317c0df5','Actual C8 child model')
        for n in ('anchors03.json','devices01.json'):require(sha(P/n)==sha(OUT/'fresh-rc/pump-rc'/n),'Child plane/device source differs')
        rows=statements((OUT/'prior-model/parent845.spice').read_text());raw=statements((OUT/'fresh-rc/parent-rc/wires.spice').read_text())
        childrows=statements((P/'pump30-wire01.spice').read_text())
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
        cap=caps[0];require(number(next(v[2:]for v in cap if v.lower().startswith('w=')))==number('9u'),'Original capacitor width')
        require(number(next(v[2:]for v in cap if v.lower().startswith('l=')))==number('9u'),'Original capacitor length')
        cap[:]=['w=8u'if v.lower().startswith('w=')else'l=8u'if v.lower().startswith('l=')else v for v in cap]
        require(Counter(map(intrinsic_signature,expected))==Counter(intrinsic_signature(w)for w in added_pump if w[0][0].lower()=='x'),'Unexpected intrinsic change beyond capacitor')
        require(public_map==result['pump_public_mapping'],'Retained pump reference planes differ')
        result['pump_change']=dict(unchanged_other_devices=815,old_cap_um=9,new_cap_um=8,native_devices=30,fresh_R=84,fresh_C=155,body_reference=old_body)
        rows=[rows[0],*kept,*added_pump,*removed_parent,rows[-1]]

        belongs=lambda r:r[0].lower().startswith(('r_xparent_','c_xparent_'))
        removed=[r for r in rows[1:-1]if belongs(r)];kept=[r for r in rows[1:-1]if not belongs(r)]
        require(Counter(r[0][0].upper()for r in removed)==dict(R=98,C=242),'Old parent wire census')
        def parent_node(n):
            canonical='wire_cref'if n.lower()=='sub'else n[2:].lower()if n.startswith('P_')else n.lower()
            return aliases.get(canonical,canonical)
        added=[]
        for row in raw[1:-1]:
            require(len(row)==4 and row[0][0].upper()in 'RC'and number(row[3])>0,'Native wire record')
            added.append([row[0][0].upper()+'_xparent_'+row[0].lower(),parent_node(row[1]),parent_node(row[2]),row[3]])
        require(Counter(r[0][0].upper()for r in added)==dict(R=98,C=242),'Fresh parent wire census')
        expected=[rows[0],*kept,*added,rows[-1]];text='\n'.join(' '.join(r)for r in expected)+'\n'
        def preserve(candidate):
            actual=statements(candidate);require(actual==expected,'Changed component, wire value, boundary or attachment')
            require(len({r[0].lower()for r in actual[1:-1]})==len(actual)-2,'Duplicate instance')
            require(sum(r[0].upper().startswith('X')for r in actual[1:-1])==845,'Native device census')
            require(sum(r[0][0].upper()in 'RC'for r in actual[1:-1])==8660,'Total measured wire census')
            require([r for r in actual[1:-1]if not belongs(r)]==kept,'Changed non-parent record')
        preserve(text);target=OUT/'parent845.spice';target.write_text(text)
        result['candidate_sha256']=sha(target);result['component_preservation']=dict(unchanged_other_devices=815,replaced_native_pump_devices=30,unchanged_records=len(kept),fresh_parent_R=98,fresh_parent_C=242,total_wires=8660,parent_wires_byte_equal_to_old=sorted(removed)==sorted(added));save()
        # Only the graph-comparison copy receives native tap area/perimeter.
        # The actual simulator deck remains exactly the finite-R composition.
        native=json.loads((OUT/'divider/native.json').read_text());native_rows={r['id']:r for r in native['modes']['lvs_flat']['devices']}
        bindings={r['native_id']:r for r in child['intrinsic_bindings']}
        shadow=copy.deepcopy(expected);tap_proof=[]
        for row in shadow[1:-1]:
            match=re.fullmatch(r'X_(xdiv[12])_xd(\d+)',row[0])
            if not match or 'ptap1'not in row:continue
            ident=int(match[2]);n=native_rows[ident];binding=bindings[ident];require(n['model']==binding['model']=='ptap1','Actual native tap identity')
            require(binding['native_parameters']==n['parameters'],'Tap extraction provenance differs')
            params={w.split('=',1)[0].lower():number(w.split('=',1)[1])for w in row if '='in w}
            require(set(params)=={'r'}and params['r']==number(binding['compact_parameters']['R']),'Finite tap resistance changed')
            area=Decimal(str(n['parameters']['A']))*Decimal('1e-12');perimeter=Decimal(str(n['parameters']['P']))*Decimal('1e-6')
            require(area>0 and perimeter>0,'Native tap geometry missing')
            row.extend(['a='+str(area),'p='+str(perimeter)])
            tap_proof.append(dict(instance=row[0],native_id=ident,area_m2=str(area),perimeter_m=str(perimeter),finite_R=str(params['r'])))
        require(len(tap_proof)==36,'Both18contact divider macros must bind')
        result['tap_geometry_evidence']=tap_proof;result['linear_dimension_comparison_grid_m']='1e-12';save()
        physical=json.loads((OUT/'fresh-rc/current-parent/integrated/result.json').read_text());reference=(OUT/'fresh-rc/current-parent/integrated/schematic.cir').read_text()
        require(physical['top']=='nssoc_pll845_divider3p2_c8_v2_development','Actual new physical reference')
        require(physical['prior_integration_proof']['child_geometry_exact']and physical['prior_integration_proof']['all14_instance_ports_unchanged']and physical['integration_proof']['all7ports_unchanged']and physical['integration_proof']['other_cell_shapes_and_instances_unchanged'],'Placed child boundary')
        audit=json.loads((OUT/'fresh-rc/current-parent/physical/lvs_flat/audit.json').read_text());require(audit['status']=='PASS within comparison scope','Actual full845nativeLVS')
        comparison='\n'.join(' '.join(r)for r in shadow)+'\n';(OUT/'graph-comparison-only.spice').write_text(comparison)
        result['counts']=verify_graph(comparison,reference,physical,result,save)
        require(result['counts']==dict(devices=845,wires=8660,public_ports=17),'Full graph census')
        faults=[]
        for name in ['drop_parent_R','change_parent_R','change_parent_C','move_parent_C','change_divider_R','change_divider_tap_R','revert_divider_load','change_pump_R','change_pump_C']:
            bad=copy.deepcopy(expected)
            if name=='change_divider_tap_R':
                i=next(i for i,r in enumerate(bad)if r[0].startswith('X_xdiv1_')and 'ptap1'in r);bad[i][-1]='R=999'
            elif name=='revert_divider_load':
                i=next(i for i,r in enumerate(bad)if r[0].startswith('X_xdiv1_')and 'rppd'in r and any(v.startswith('l=')and number(v[2:]).quantize(Decimal('1e-12'))==Decimal('3.2e-6')for v in r));bad[i]=['l=2.12u'if v.startswith('l=')else v for v in bad[i]]
            else:
                prefix='R_xpump_'if name=='change_pump_R'else'C_xpump_'if name=='change_pump_C'else'R_xdiv1_'if name=='change_divider_R'else'C_xparent_'if name in ['change_parent_C','move_parent_C']else'R_xparent_'
                i=next(i for i,r in enumerate(bad)if r[0].startswith(prefix))
                if name=='drop_parent_R':bad.pop(i)
                elif name=='move_parent_C':bad[i][1]='wrong_parent_attachment'
                else:bad[i][3]='999'
            altered='\n'.join(' '.join(r)for r in bad)+'\n';require(altered!=text,'Ineffective corruption');(OUT/(name+'.spice')).write_text(altered)
            try:preserve(altered)
            except ValueError as error:faults.append(dict(name=name,rejected=True,reason=str(error)))
            else:raise ValueError('Accepted actual composition corruption '+name)
        result['component_faults']=faults
        require(sha(target)==result['candidate_sha256'],'Simulator model changed during comparison')
        require(all(sha(OUT/'fresh-rc'/n)==rc['outputs'][n]for n in selected),'Fresh source changed')
        require(sha(OUT/'prior-model/parent845.spice')==old['candidate_sha256']and sha(OUT/'divider/native.json')==child['native_sha256'],'Native source changed')
        require(all(sha(P/n)==pump['outputs'][n]for n in ('pump30-wire01.spice','anchors03.json','devices01.json')),'C8 source changed')
        result.update(status='PASS_C8_PHYSICAL845_DIVIDER_PARENT_MODEL_EXACT_GRAPH_AND_COMPONENT_FAULTS_NOT_ELECTRICAL_ACCEPTANCE',source_unchanged=True)
    except BaseException as error:result.update(status='FAIL_OR_ERROR',error=repr(error));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
