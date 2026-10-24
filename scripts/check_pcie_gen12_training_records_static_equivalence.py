#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted-only all-index write equivalence; complete record proof stays separate."""
import argparse,ast,hashlib,json,os,random
from pathlib import Path
import cloud_pcie_gen12_training_records_telemetry as guard
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pcie-gen12-training-records-static-equivalence'
METHOD=ROOT/'scripts/pcie-gen12-training-records-static-derivation.json'
BASE_RTL='hw/soc/rtl/pcie/soc_pcie_gen12_training_records.v'
NEW_RTL='hw/soc/rtl/pcie/soc_pcie_gen12_training_records_static.v'
BASE_CHECK='scripts/check_pcie_gen12_training_records.py'
NEW_CHECK='scripts/check_pcie_gen12_training_records_static.py'
MASK=(1<<192)-1

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def source_contract():
    m=json.loads(METHOD.read_text())
    for p,h in m['protected'].items():assert sha(ROOT/p)==h,p
    original=json.loads((ROOT/'scripts/pcie-gen12-training-records-methods.json').read_text())
    assert len(original['protected'])==44
    for p,h in original['protected'].items():assert sha(ROOT/p)==h,p
    for old,new,key in ((BASE_RTL,NEW_RTL,'rtl_edits'),(BASE_CHECK,NEW_CHECK,'checker_edits')):
        text=(ROOT/old).read_text()
        for edit in m[key]:
            assert text.count(edit['before'])==edit['count'],edit
            text=text.replace(edit['before'],edit['after'])
        assert text==(ROOT/new).read_text(),new
        for edit in reversed(m[key]):
            assert text.count(edit['after'])==edit['count'],edit
            text=text.replace(edit['after'],edit['before'])
        assert text==(ROOT/old).read_text()
    a=ast.parse((ROOT/BASE_CHECK).read_text());b=ast.parse((ROOT/NEW_CHECK).read_text())
    af={n.name:ast.dump(n,include_attributes=False)for n in a.body if isinstance(n,ast.FunctionDef)}
    bf={n.name:ast.dump(n,include_attributes=False)for n in b.body if isinstance(n,ast.FunctionDef)}
    assert set(af)==set(bf)
    assert all(af[n]==bf[n]for n in af if n not in ('prerequisites','mutations'))
    # Only the declared path changes and six equivalent mutation anchors differ.
    return m

def write_bits(part,count,slot,data,k,ce,de,com):
    bits=[(part>>i)&1 for i in range(192)]
    byte=(data>>(8*slot))&255
    for j in range(8):
        dest=8*count+j
        if 0<=dest<192:bits[dest]=(byte>>j)&1
    for offset,flags in ((128,k),(144,ce),(160,de),(176,com)):
        dest=offset+count
        if 0<=dest<192:bits[dest]=(flags>>slot)&1
    return sum(v<<i for i,v in enumerate(bits))

def full_reference(active,overflow,count,part,batch,data,k,ce,de,com):
    complete=0;valid=0
    if active and not overflow:
        for slot in range(4):
            if slot<batch:
                start=((com>>slot)&1)and((k>>slot)&1)and not((ce>>slot)&1)and((data>>(slot*8))&255)==0xbc
                if count or start:
                    part=write_bits(part,count,slot,data,k,ce,de,com)
                    if count==15:complete=part;valid=1;count=0;part=0
                    else:count=(count+1)&31
    return part|(count<<192)|(complete<<197)|(valid<<389)

def vector_files():
    rng=random.Random(0x321904)
    seen_slot=set();seen_count=set();nslot=0
    slot_path=OUT/'slot.vec'
    with slot_path.open('w')as f:
        for count in range(32):
            for slot in range(4):
                cases=[(0,0,0,0,0,0),(MASK,0xffffffff,15,15,15,15)]
                # Every original192 bit both retained and overwritten; every
                # input symbol/flag bit, plus complements, across all32x4 indices.
                for bit in range(192):cases.extend([(1<<bit,0,0,0,0,0),(MASK^(1<<bit),0xffffffff,15,15,15,15)])
                for bit in range(48):
                    fields=1<<bit
                    values=(fields&0xffffffff,(fields>>32)&15,(fields>>36)&15,(fields>>40)&15,(fields>>44)&15)
                    cases.append((0,*values))
                    inv=((1<<48)-1)^fields
                    cases.append((MASK,inv&0xffffffff,(inv>>32)&15,(inv>>36)&15,(inv>>40)&15,(inv>>44)&15))
                for _ in range(8):cases.append((rng.getrandbits(192),rng.getrandbits(32),*[rng.randrange(16)for _ in range(4)]))
                for part,data,k,ce,de,com in cases:
                    expected=write_bits(part,count,slot,data,k,ce,de,com)
                    f.write(' '.join(format(x,'x')for x in (count,slot,part,data,k,ce,de,com,expected))+'\n');nslot+=1
                seen_slot.add(slot);seen_count.add(count)
    assert seen_slot==set(range(4))and seen_count==set(range(32))
    nfull=0;combos=set()
    full_path=OUT/'full.vec'
    with full_path.open('w')as f:
        for count in range(32):
            for batch in range(8):
                for active in range(2):
                    for overflow in range(2):
                        cases=[(0,0,0,0,0,0),(MASK,0xffffffff,15,15,15,15),(MASK,0xbcbcbcbc,15,0,15,15)]
                        for slot in range(4):
                            cases.extend([(rng.getrandbits(192),0xbc<<(8*slot),1<<slot,0,0,1<<slot),
                                          (rng.getrandbits(192),0xbcbcbcbc,15,1<<slot,15,15)])
                        for _ in range(4):cases.append((rng.getrandbits(192),rng.getrandbits(32),*[rng.randrange(16)for _ in range(4)]))
                        for part,data,k,ce,de,com in cases:
                            values=(active,overflow,count,part,batch,data,k,ce,de,com)
                            expected=full_reference(*values)
                            f.write(' '.join(format(x,'x')for x in (*values,expected))+'\n');nfull+=1
                        combos.add((count,batch,active,overflow))
    assert len(combos)==32*8*2*2
    assert nslot==62720 and nfull==15360
    return {'slot_cases':nslot,'full_serial_block_cases':nfull,'all_counts':sorted(seen_count),'all_batch_slots':sorted(seen_slot),
            'full_control_combinations':len(combos),'slot_vector_sha256':sha(slot_path),'full_vector_sha256':sha(full_path),
            'proof_scope':'All32 indices/all4 slot selection, exhaustive bit bases and complements plus directed/random four-stage control cases; not an assertion of exhaustive2^inputs or transistor acceptance.'}

def slot_module(name,write):
    return ('module '+name+'(input [4:0]rx_next_count,input [1:0]s,input [191:0]initial_bits,'
      'input [31:0]rx_batch_data,input [3:0]rx_batch_k,rx_batch_ce,rx_batch_de,rx_batch_comma,'
      'output reg [191:0]rx_next_partial);\ninteger lane;\nalways @*begin\nrx_next_partial=initial_bits;\n'
      +write+'\nend\nendmodule\n')

def full_module(name,text):
    start=text.index(' always @* begin\n  rx_next_count=rx_partial_count;')
    stop=text.index(' assign rx_record_valid_o=',start)
    body=text[start:stop]
    return ('module '+name+'(input rx_active,rx_overflow_o,input [4:0]rx_partial_count,input [191:0]rx_partial,'
      'input [2:0]rx_batch_count,input [31:0]rx_batch_data,input [3:0]rx_batch_k,rx_batch_ce,rx_batch_de,rx_batch_comma,'
      'output reg [4:0]rx_next_count,output reg [191:0]rx_next_partial,rx_complete,output reg rx_complete_valid);\n'
      'integer s,lane;\n'+body+'endmodule\n')

def tb(mode,rows):
    if mode=='slot':
        decl='reg[4:0]count;reg[1:0]slot;reg[191:0]partial,expected;reg[31:0]data;reg[3:0]k,ce,de,com;wire[191:0]old_value,new_value;'
        modules='old_slot a(count,slot,partial,data,k,ce,de,com,old_value);new_slot b(count,slot,partial,data,k,ce,de,com,new_value);'
        scan='count,slot,partial,data,k,ce,de,com,expected';fields=9
    else:
        decl=('reg active,overflow;reg[4:0]count;reg[191:0]partial;reg[2:0]batch;reg[31:0]data;reg[3:0]k,ce,de,com;'
          'reg[389:0]expected;wire[4:0]oc,nc;wire[191:0]op,np,ofin,nfin;wire ov,nv;wire[389:0]old_value={ov,ofin,oc,op},new_value={nv,nfin,nc,np};')
        modules=('old_full a(active,overflow,count,partial,batch,data,k,ce,de,com,oc,op,ofin,ov);'
          'new_full b(active,overflow,count,partial,batch,data,k,ce,de,com,nc,np,nfin,nv);')
        scan='active,overflow,count,partial,batch,data,k,ce,de,com,expected';fields=11
    return ('module tb;\n'+decl+'\n'+modules+'\ninteger f,n,row;initial begin\nrow=0;'
      +'f=$fopen("'+str(OUT/(mode+'.vec'))+'","r");if(!f)$fatal(1,"missing vectors");\n'
      +'while(!$feof(f))begin n=$fscanf(f,"'+' '.join(['%h']*fields)+'\\n",'+scan+');'
      +'if(n=='+str(fields)+')begin #1;if(old_value!==expected || new_value!==expected || old_value!==new_value)'
      +'$fatal(1,"equivalence '+mode+' row%0d count%0d",row,count);row=row+1;end else if(n!=-1)$fatal(1,"malformed vector");end\n'
      +'if(row!='+str(rows)+')$fatal(1,"truncated vectors");$display("PASS_STATIC_'+mode.upper()+'_EQUIVALENCE %0d",row);$finish;end\nendmodule\n')

def run_case(modules,testbench,label,good):
    design=OUT/(label+'.v');design.write_text(modules+testbench);exe=OUT/(label+'.vvp')
    guard.supervised(['iverilog','-g2012','-s','tb','-o',exe,design],label+'-compile',cwd=OUT)
    p=guard.supervised(['vvp',exe],label,False,cwd=OUT)
    if good:assert p.returncode==0 and 'PASS_STATIC_'in p.stdout,(label,p.stdout,p.stderr)
    else:assert p.returncode!=0 and 'FATAL'in p.stdout+p.stderr,(label,p.stdout,p.stderr)
    return {'label':label,'returncode':p.returncode,'design_sha256':sha(design),'log_sha256':sha(OUT/(label+'.log'))}

def faults(new):
    data='if(lane<24)rx_next_partial[lane*8+:8]=rx_batch_data[s*8+:8];'
    kval='rx_next_partial[128+lane]=rx_batch_k[s];'
    pairs={
      'truncate_to16':('lane<32','lane<16'),
      'discard_count23_byte':('if(lane<24)','if(lane<23)'),
      'shift_K_destination':('[128+lane]','[129+lane]'),
      'discard_high_count_DE':('rx_next_partial[160+lane]=rx_batch_de[s];','if(lane<16)rx_next_partial[160+lane]=rx_batch_de[s];'),
      'discard_count15_COM':('if(lane<16)','if(lane<15)'),
      'wrong_source_slot':('rx_batch_data[s*8+:8]','rx_batch_data[(3-s)*8+:8]'),
      'reverse_overlapping_write_order':(data+'\n        '+kval,kval+'\n        '+data),
      'discard_byte':('rx_batch_data[s*8+:8]','8\'h00')}
    result={}
    for label,(before,after)in pairs.items():
        assert new.count(before)==1,label;result[label]=new.replace(before,after)
    assert len(result)==8
    return result

def main():
    guard.host();m=source_contract();OUT.mkdir(parents=True,exist_ok=False)
    guard.TRACE=OUT/'telemetry';guard.TRACE.mkdir()
    result={'status':'RUNNING','run':os.environ['GITHUB_RUN_ID'],'source':os.environ['GITHUB_SHA'],
      'original_full_record_proof_completed':False,'synthesis_improvement_measured':False,'full_PHY_accepted':False,
      'protected_source_hashes':m['protected'],'derivation_sha256':sha(METHOD)}
    try:
        result['coverage']=vector_files()
        old=m['rtl_edits'][1]['before'];new=m['rtl_edits'][1]['after']
        assert old in (ROOT/BASE_RTL).read_text()and new in (ROOT/NEW_RTL).read_text()
        slot_tb=tb('slot',result['coverage']['slot_cases'])
        result['slot_positive']=run_case(slot_module('old_slot',old)+slot_module('new_slot',new),slot_tb,'slot-positive',True)
        full_tb=tb('full',result['coverage']['full_serial_block_cases'])
        result['four_stage_positive']=run_case(full_module('old_full',(ROOT/BASE_RTL).read_text())+full_module('new_full',(ROOT/NEW_RTL).read_text()),full_tb,'full-positive',True)
        result['negative_controls']=[run_case(slot_module('old_slot',old)+slot_module('new_slot',changed),slot_tb,label,False)for label,changed in faults(new).items()]
        assert len(result['negative_controls'])==8 and source_contract()==m
        result['status']='PASS_STATIC32_WRITE_EQUIVALENCE_AND8_COMPILED_FAULTS'
    except BaseException as e:result.update(status='FAIL_OR_ERROR',error=repr(e));raise
    finally:
        result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
        (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items()if k!='outputs'}),flush=True)

if __name__=='__main__':main()
