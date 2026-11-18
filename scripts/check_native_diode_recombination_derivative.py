#!/usr/bin/env python3
"""Independent analytic/complex-step check; no simulator or PDK modifications."""
import math,cmath,json
from pathlib import Path

def main():
 out=Path('hw/soc/out/diode-derivative-math');out.mkdir(parents=True,exist_ok=False)
 rows=[]
 for potential in [.4,.696,.9]:
  for grading in [.01923,.3036,.5]:
   for voltage in [-.09,-.03,0,.05,.15,.3]:
    thermal=2*8.617333262145e-5*398.15
    def current(v):return (cmath.exp(v/thermal)-1)*(((1-v/potential)**2+.005)**(grading/2))
    t=(1-voltage/potential)**2+.005;g=t**(grading/2)
    raw=math.expm1(voltage/thermal);raw_derivative=math.exp(voltage/thermal)/thermal
    dg=-grading*(1-voltage/potential)*t**(grading/2-1)/potential
    analytic=raw_derivative*g+raw*dg
    numeric=current(complex(voltage,1e-20)).imag/1e-20
    # Transcription of the inspected upstream forward recombination sequence.
    published=raw_derivative*g+(raw*g)*(-grading*(1-voltage/potential)*t**(grading/2-1))
    scale=max(abs(numeric),1e-15)
    assert abs(analytic-numeric)/scale<1e-11
    rows.append(dict(v=voltage,potential=potential,grading=grading,analytic=analytic,complex_step=numeric,published_sequence=published,published_relative_difference=abs(published-numeric)/scale))
 assert any(r['published_relative_difference']>.01 for r in rows)
 result=dict(status='ANALYTIC_DERIVATIVE_CONFIRMED_PUBLISHED_SEQUENCE_DIFFERS',simulator_patch_applied=False,model_parameters_changed=False,proves_transient_root_cause=False,points=len(rows),maximum_published_relative_difference=max(r['published_relative_difference']for r in rows),rows=rows)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(result['status'],len(rows),result['maximum_published_relative_difference'])
if __name__=='__main__':main()
