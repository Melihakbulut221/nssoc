#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Lossless bounded-command OP transport; full transient remains binary."""
import copy,json,math,os,subprocess
from decimal import Decimal
from pathlib import Path
from cloud_tx_stream import streaming_deck,digest
def save_commands(vectors):
    assert vectors and len(vectors)==len(set(vectors)) and len(vectors)<30000
    size=len(vectors)if len(vectors)<=1000 else 128
    result=['save '+' '.join(vectors[i:i+size])for i in range(0,len(vectors),size)]
    assert [n for row in result for n in row.split()[1:]]==vectors
    return result
def commands(vectors,size=512):
    assert vectors and len(vectors)==len(set(vectors)) and 1<=size<=512
    parts=[dict(file='op-part%04d.dat'%i,vectors=vectors[j:j+size])for i,j in enumerate(range(0,len(vectors),size))]
    assert [n for part in parts for n in part['vectors']]==vectors
    return ['wrdata '+p['file']+' '+' '.join(p['vectors'])for p in parts],dict(vectors=vectors,parts=parts)
def chunked_stream(deck,contract):
    original=streaming_deck(deck,contract)
    line='wrdata op.dat '+' '.join(contract['vectors'])
    assert original.splitlines().count(line)==1
    rows,spec=commands(contract['vectors'])
    candidate=original.replace(line,'\n'.join(rows))
    assert candidate.replace('\n'.join(rows),line)==original
    assert all(len(row.split())<=514 for row in rows)
    return candidate,spec
def parse_parts(texts,spec):
    assert len(texts)==len(spec['parts'])
    names=[];values=[];scale=None
    for text,part in zip(texts,spec['parts'],strict=True):
        lines=[line.split()for line in text.splitlines()if line.strip()]
        assert len(lines)==2,'OP must contain exactly one native data row'
        header,data=lines
        assert len(header)==len(data)==len(part['vectors'])+1
        assert header[1:]==part['vectors'],'Missing, renamed, duplicated or reordered native OP vector'
        numbers=[Decimal(v)for v in data]
        assert all(v.is_finite()for v in numbers)
        if scale is None:scale=data[0]
        assert Decimal(data[0])==Decimal(scale),'OP chunk scale differs'
        names.extend(header[1:]);values.extend(data[1:])
    assert names==spec['vectors']and len(names)==len(set(names))
    return scale,values
def assemble_op(root,spec):
    paths=[root/p['file']for p in spec['parts']]
    scale,values=parse_parts([p.read_text()for p in paths],spec)
    output=root/'op.dat';assert not output.exists()
    output.write_text('scale '+' '.join(spec['vectors'])+'\n'+' '.join([scale,*values])+'\n')
    return dict(status='PASS_ALL_NATIVE_OP_COLUMNS_EXACT_TEXT_REASSEMBLY',vectors=len(values),chunks=len(paths),
        inputs={p.name:digest(p)for p in paths},output_sha256=digest(output),
        numeric_values_reformatted=False,omitted_vectors=False)
def native_pilot(engine,out):
    assert os.environ.get('GITHUB_ACTIONS')=='true'
    out.mkdir(exist_ok=False)
    count=10032
    vectors=['v(n%05d)'%i for i in range(count)]
    expected=[format((i+1)/count,'.17g')for i in range(count)]
    writes,spec=commands(vectors)
    lines=['* Native OP transport test above the single wrdata command limit']
    lines+=['V%05d n%05d 0 DC %s'%(i,i,value)for i,value in enumerate(expected)]
    lines+=['.control','set wr_singlescale','set wr_vecnames','set numdgt=16',*save_commands(vectors),'op',*writes,
        'wrdata reference.dat '+' '.join(vectors[:256]),'quit','.endc','.end']
    deck=out/'pilot.cir';deck.write_text('\n'.join(lines)+'\n')
    env={k:v for k,v in os.environ.items()if k not in ('LD_PRELOAD','PYTHONPATH','PYTHONHOME','GH_TOKEN','GITHUB_TOKEN')}
    (out/'spinit').write_text('set num_threads=1\n')
    env.update(SPICE_SCRIPTS=str(out),OMP_NUM_THREADS='1',RAYON_NUM_THREADS='1')
    with (out/'native.log').open('w')as log:
        code=subprocess.call([str(engine),'-n','-b',deck.name],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT)
    assert code==0,'Native OP pilot failed'
    text=(out/'native.log').read_text(errors='replace')
    assert not any(word in text.lower()for word in ('warning','error','singular','too small'))
    texts=[(out/p['file']).read_text()for p in spec['parts']]
    scale,values=parse_parts(texts,spec)
    assert all(abs(Decimal(a)-Decimal(b))<=Decimal('2e-14')for a,b in zip(values,expected,strict=True))
    # Exact printed decimals against one legal original aggregate command.
    small=dict(vectors=vectors[:256],parts=[dict(file='reference.dat',vectors=vectors[:256])])
    refscale,reference=parse_parts([(out/'reference.dat').read_text()],small)
    assert Decimal(scale)==Decimal(refscale)
    assert [Decimal(v)for v in values[:256]]==[Decimal(v)for v in reference]
    controls=[]
    for fault in ['missing_chunk','swapped_column_header','truncated_data_row','extra_data_row','nonfinite_value']:
        bad=list(texts)
        if fault=='missing_chunk':bad.pop()
        else:
            rows=[line.split()for line in bad[0].splitlines()if line.strip()]
            if fault=='swapped_column_header':rows[0][1],rows[0][2]=rows[0][2],rows[0][1]
            elif fault=='truncated_data_row':rows[1].pop()
            elif fault=='extra_data_row':rows.append(list(rows[1]))
            else:rows[1][1]='nan'
            bad[0]='\n'.join(' '.join(r)for r in rows)+'\n'
        try:parse_parts(bad,spec)
        except AssertionError:controls.append(dict(fault=fault,rejected=True))
        else:raise AssertionError('Native OP corruption accepted: '+fault)
    result=dict(status='PASS_NATIVE10032_DISTINCT_OP_VALUES_AND_FIVE_TRANSPORT_FAULTS',
        native_vectors=count,native_chunks=len(spec['parts']),original_aggregate_reference_columns=256,
        all10032_analytical_voltages_checked=True,analytical_decimal_atol='2e-14',
        original_aggregate_decimal_values_exact=True,controls=controls,assembly=assemble_op(out,spec),
        full_phy_accepted=False,scope='Native transport only; no DUT voltage or acceptance limit changed.')
    result['outputs']={p.name:digest(p)for p in out.iterdir()if p.is_file()}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
