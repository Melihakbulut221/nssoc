"""Cloud-only network controls with independent analytic expectations."""
import copy,json,math
from pathlib import Path
from cdr_selector_resistance import number,parse_model,solve

def main():
    cases=[]
    fixtures=[
        ("series",[("r1","a","m",2.),("r2","m","b",3.)],5.),
        ("parallel",[("r1","a","b",2.),("r2","a","b",3.)],1.2),
        ("balanced_bridge",[("r1","a","x",1.),("r2","x","b",1.),("r3","a","y",1.),("r4","y","b",1.),("r5","x","y",7.)],1.),
        ("floating_spur",[("r1","a","m",2.),("r2","m","b",3.),("r3","m","x",100.)],5.),
        ("separate_component",[("r1","a","b",2.),("r2","c","d",100.)],2.)]
    for label,edges,expected in fixtures:
        result=solve(edges,"a","b")
        assert math.isclose(result["effective_resistance_ohm"],expected,rel_tol=1e-12)
        reverse=solve(edges,"b","a")
        assert math.isclose(reverse["effective_resistance_ohm"],expected,rel_tol=1e-12)
        scaled=solve([(n,a,b,r*7)for n,a,b,r in edges],"a","b")
        assert math.isclose(scaled["effective_resistance_ohm"],expected*7,rel_tol=1e-12)
        cases.append(label+" analytic resistance, reciprocity, scaling")
    edge=[("r1","a","m",2.),("r2","m","b",3.)]
    for label,e,a,b in [
        ("disconnected",[("r1","a","x",2.),("r2","b","y",3.)],"a","b"),
        ("absent",edge,"a","z"),("selfpair",edge,"a","a"),
        ("duplicate",[("r1","a","m",2.),("r1","m","b",3.)],"a","b"),
        ("zero",[("r1","a","b",0.)],"a","b"),
        ("negative",[("r1","a","b",-1.)],"a","b"),
        ("nonfinite",[("r1","a","b",float("nan"))],"a","b"),
        ("selfedge",[("r1","a","a",1.)],"a","b")]:
        try:solve(e,a,b)
        except ValueError:cases.append("refuse "+label)
        else:raise AssertionError(label)
    c=dict(interface=["a","b"],device_records=[],counts=dict(devices=0,R=1,C=1))
    text=".subckt test a b\nR1 a b 2k\nC1 a b 3p\n.ends test\n"
    e,_=parse_model(text,c);assert e==[("r1","a","b",2000.)];cases.append("strict passive parse and capacitance exclusion")
    for label,t,contract in [
        ("port_order",text.replace("test a b","test b a"),c),
        ("census",text,dict(c,counts=dict(devices=0,R=2,C=1))),
        ("duplicate_model_element",text.replace("C1","R1"),c),
        ("zero_model_resistance",text.replace("2k","0"),c),
        ("negative_capacitance",text.replace("3p","-3p"),c),
        ("hidden_voltage_source",text.replace("C1 a b 3p","V1 a b 3"),c),
        ("bad_suffix",text.replace("2k","2ohm"),c),
        ("extra_directive",text.replace(".ends",".param x=1\n.ends"),c)]:
        try:parse_model(t,contract)
        except (ValueError,KeyError):cases.append("refuse "+label)
        else:raise AssertionError(label)
    assert number("1m")==.001 and number("1meg")==1e6 and number("1E-3")==.001;cases.append("SPICE m versus meg versus exponent")
    # The full constructor must preserve actual active-device terminals and parameters.
    dev=dict(instance="X1",model="npn13g2",parameters={"nx":"2"},terminals=[dict(node=x)for x in("a","b","s","sub")])
    contract=dict(interface=["a","b"],device_records=[dev],counts=dict(devices=1,R=1,C=1))
    model=text.replace("R1","X1 a b s sub npn13g2 nx=2\nR1")
    parse_model(model,contract);cases.append("complete active-device binding")
    for label,t in [("changed_device",model.replace("nx=2","nx=4")),("changed_terminal",model.replace("X1 a b","X1 b a"))]:
        try:parse_model(t,contract)
        except ValueError:cases.append("refuse "+label)
        else:raise AssertionError(label)
    assert len(cases)==26
    out=Path("wire-selector-resistance");out.mkdir(exist_ok=True)
    (out/"network-controls.json").write_text(json.dumps(dict(count=len(cases),cases=cases,native_model_read=False,new_transient_executed=False,physical_acceptance=False,full_phy_accepted=False),indent=2)+"\n")
if __name__=="__main__":main()
