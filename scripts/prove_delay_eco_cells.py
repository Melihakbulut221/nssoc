import subprocess,json,base64,hashlib,pathlib
out=pathlib.Path('eco-cell-proof');out.mkdir()
api='repos/IHP-GmbH/IHP-Open-PDK/contents/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v?ref=c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
raw=base64.b64decode(json.loads(subprocess.check_output(['gh','api',api]))['content'])
assert hashlib.sha256(raw).hexdigest()=='28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4'
text=raw.decode();modules=[]
for name in ['sg13g2_dlygate4sd3_1','sg13g2_buf_1','sg13g2_buf_4','sg13g2_buf_2','sg13g2_buf_8','sg13g2_nor4_1','sg13g2_nor4_2']:
 start=text.index('module '+name+' ');end=text.index('endmodule',start)+len('endmodule');modules.append(text[start:end])
library='\n'.join(modules);(out/'cells.v').write_text(library)
tb=r"""module tb;
reg a,b,c,d;wire oldbuf,newbuf,oldnor,newnor,q1,q2,q3,taper,old8,new8;
sg13g2_buf_2 t0(taper,a);sg13g2_buf_8 t1(old8,a),t2(new8,taper);
sg13g2_buf_1 u0(oldbuf,a);sg13g2_buf_4 u1(newbuf,a);
sg13g2_nor4_1 n0(oldnor,a,b,c,d);sg13g2_nor4_2 n1(newnor,a,b,c,d);
sg13g2_dlygate4sd3_1 d0(q1,a),d1(q2,q1),d2(q3,q2);
function state;input integer v;begin case(v)0:state=0;1:state=1;2:state=1'bx;3:state=1'bz;endcase end endfunction
integer i,j,k,l,total;initial begin total=0;
for(i=0;i<4;i=i+1)for(j=0;j<4;j=j+1)for(k=0;k<4;k=k+1)for(l=0;l<4;l=l+1)begin
 a=state(i);b=state(j);c=state(k);d=state(l);#1;
 if(oldbuf!==taper || old8!==new8 || oldbuf!==newbuf || oldnor!==newnor || q1!==oldbuf || q2!==oldbuf || q3!==oldbuf)$fatal(1,"ECO_CELL_MISMATCH");
 if(i<2 && (q1!==a || q2!==a || q3!==a))$fatal(1,"BINARY_DELAY_MISMATCH");
 total=total+1;
end
$display("ECO_CELL_PASS vectors=%0d",total);$finish;end
endmodule
"""
(out/'tb.v').write_text(tb);rows=[]
for mutant in [False,True,"taper"]:
 name='inverted-taper'if mutant=='taper'else'inverted-delay'if mutant else'positive';cells=library
 if mutant=='taper':
  start=cells.index('module sg13g2_buf_2 ');end=cells.index('endmodule',start);part=cells[start:end];assert 'buf (X, A);'in part
  cells=cells[:start]+part.replace('buf (X, A);','not (X, A);')+cells[end:]
 elif mutant:
  prefix,end=cells.split('endmodule',1);assert 'buf (X, A);'in prefix;cells=prefix.replace('buf (X, A);','not (X, A);')+'endmodule'+end
 (out/(name+'.v')).write_text(cells)
 subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/(name+'.vvp')),str(out/(name+'.v')),str(out/'tb.v')],check=True)
 r=subprocess.run(['vvp',str(out/(name+'.vvp'))],capture_output=True,text=True);log=r.stdout+r.stderr;(out/(name+'.log')).write_text(log)
 passed=(r.returncode!=0 and 'ECO_CELL_MISMATCH'in log)if mutant else(r.returncode==0 and 'ECO_CELL_PASS vectors=256'in log)
 rows.append(dict(mutation=mutant,returncode=r.returncode,passed=passed));assert passed,log
(out/'result.json').write_text(json.dumps(dict(library_sha256='28343754a828972d614c15b7db27892e92a8c16e49fc06ed69d858a659942ed4',cases=rows,scope='Exact pinned PDK Verilog cell-function tests. buf1/buf2/buf4, native buf8 vs buf2-to-buf8 taper, and nor4_1/nor4_2 agree for 256 four-state combinations. One/two/three positive delay stages agree with native buf for four-state inputs, and with direct input for binary inputs only. Z is NOT proven equivalent to bare wire. Actual inverted-delay and inverted-buf2 controls must fail. Not timed/SDF simulation, physical netlist equivalence, routing or production acceptance.',outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.iterdir()if p.is_file()and p.suffix!='.vvp'}),indent=2))
