"""Source-only exact descriptor and order-diagnosis controls."""
import copy,json
from pathlib import Path
import mainchip_master_diagnosis as d
def main():
    m={'lib/cell':dict(width=10,height=20,type='CORE',pins={'A':dict(io='INPUT',sigtype='SIGNAL',boxes=[[['Metal1',1,2,3,4]],[['Metal2',5,6,7,8]]])})}
    labels=[]
    def trial(label,b,expected_order=False):
        r,details=d.compare(m,b)
        assert r['all_differences_only_mpin_order']is expected_order
        assert all(r[k]is False for k in d.FLAGS)
        if label=='identical':assert r['exact_equal']and not details
        else:assert not r['exact_equal']and details
        labels.append(label)
    trial('identical',copy.deepcopy(m))
    b=copy.deepcopy(m);b['lib/cell']['pins']['A']['boxes'].reverse();trial('MPin order only',b,True)
    for field,value in [('width',11),('height',21),('type','PAD')]:
        b=copy.deepcopy(m);b['lib/cell'][field]=value;trial(field,b)
    for field,value in [('io','OUTPUT'),('sigtype','CLOCK')]:
        b=copy.deepcopy(m);b['lib/cell']['pins']['A'][field]=value;trial(field,b)
    b=copy.deepcopy(m);b['lib/cell']['pins']['A']['boxes'][0][0]=['Metal1',2,1,4,3];trial('coordinate order matters',b)
    b=copy.deepcopy(m);b['lib/cell']['pins']['A']['boxes'][0][0][0]='Metal3';trial('layer matters',b)
    b=copy.deepcopy(m);b['lib/cell']['pins']['A']['boxes'].append(copy.deepcopy(b['lib/cell']['pins']['A']['boxes'][0]));trial('multiplicity matters',b)
    b=copy.deepcopy(m);b['lib/cell']['pins']['A']['boxes'][0][0][3]=9;trial('geometry matters',b)
    b=copy.deepcopy(m);b['lib/cell']['pins']['B']=b['lib/cell']['pins'].pop('A');trial('pin name matters',b)
    b=copy.deepcopy(m);b['lib/new']=b.pop('lib/cell');trial('master census matters',b)
    rejected=[]
    def reject(label,b):
        try:d.compare(m,b)
        except (AssertionError,KeyError,TypeError):rejected.append(label);return
        raise AssertionError('accepted malformed '+label)
    for label,fn in [
        ('missing width',lambda b:b['lib/cell'].pop('width')),
        ('extra field',lambda b:b['lib/cell'].update(extra=True)),
        ('boolean coordinate',lambda b:b['lib/cell']['pins']['A']['boxes'][0][0].__setitem__(1,True)),
        ('inverted box',lambda b:b['lib/cell']['pins']['A']['boxes'][0][0].__setitem__(3,0)),
        ('missing pin field',lambda b:b['lib/cell']['pins']['A'].pop('io')),
        ('string coordinate',lambda b:b['lib/cell']['pins']['A']['boxes'][0][0].__setitem__(2,'2'))]:
        b=copy.deepcopy(m);fn(b);reject(label,b)
    before=copy.deepcopy(m);d.compare(m,copy.deepcopy(m));assert m==before;labels.append('inputs unchanged')
    out=Path('cloud-master-controls');out.mkdir(exist_ok=False)
    result=dict(status='PASS_MASTER_DIAGNOSIS_SOURCE_CONTROLS',checks=labels,rejections=rejected,count=len(labels)+len(rejected),**d.FLAGS)
    assert result['count']==20
    (out/'controls.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
