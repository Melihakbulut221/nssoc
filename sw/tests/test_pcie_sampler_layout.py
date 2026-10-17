# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fixed native circuit mapping, separate rails and strict physical-result guards."""

import copy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import make_pcie_sampler_cell as sampler
import check_pcie_sampler_cell as sampler_check
import make_pcie_analog_bank_v2 as bank
import check_pcie_analog_bank_v2 as bank_check
import make_pcie_rx_cell_v2 as rx

SOURCE = (ROOT / sampler.CIRCUIT).read_text()


def tx_reference():
    # Exact native device dimensions used by the frozen TX generator, not an
    # invented model of a full serializer or PHY.
    return "\n".join([".subckt nssoc_tx_cml_layout " + " ".join(bank.CELL_PORTS["TX"]),
        "QREF IREF IREF AVSS BULK npn13G2 Nx=1 we=0.07u le=0.9u m=1",
        "QTAIL TAIL IREF AVSS BULK npn13G2 Nx=8 we=0.07u le=0.9u m=1",
        "QP OUTN INP TAIL BULK npn13G2 Nx=8 we=0.07u le=0.9u m=1",
        "QN OUTP INN TAIL BULK npn13G2 Nx=8 we=0.07u le=0.9u m=1",
        "RP AVDD OUTP BULK rsil w=10u l=70.215u m=1",
        "RN AVDD OUTN BULK rsil w=10u l=70.215u m=1",
        *[f"RTAP{i} SUB BULK ptap1 A=4p P=8u" for i in range(8)], ".ends nssoc_tx_cml_layout", ""])


@pytest.fixture
def circuits():
    return {"TX": tx_reference(),
            "RX": rx.physical_reference((ROOT / "hw/soc/analog/pcie/rx_hbt_rsil_v2.spice").read_text()),
            "SAMPLER": sampler.physical_reference(SOURCE)}


def test_sampler_fixed_devices_and_literal_hierarchy_polarity():
    rows = sampler.devices(SOURCE)
    hbts = [r for r in rows if r["kind"] == "hbt"]
    resistors = [r for r in rows if r["kind"] == "resistor"]
    assert len(rows) == len({r["name"] for r in rows}) == 27
    assert sorted(r["nx"] for r in hbts) == [1] + [2]*8 + [4]*6
    assert sorted((r["width_um"],r["length_um"]) for r in resistors) == [(1,3.6)]*4+[(1,38.4)]*4+[(8,2.12)]*4
    d = {r["name"]:r for r in rows}
    assert d["M_CS"]["nets"] == ["M_SE","CLKN","M_TE","SUB"]
    assert d["M_CH"]["nets"] == ["M_HE","CLKP","M_TE","SUB"]
    assert d["S_CS"]["nets"] == ["S_SE","CLKP","S_TE","SUB"]
    assert d["S_CH"]["nets"] == ["S_HE","CLKN","S_TE","SUB"]
    assert d["S_DP"]["nets"] == ["QN","MP","S_SE","SUB"]
    assert d["S_DN"]["nets"] == ["QP","MN","S_SE","SUB"]
    physical = sampler.physical_reference(SOURCE)
    assert len([v for v in physical.splitlines() if v.startswith("RTAP")]) == 8
    assert "RTAP0 SUB BULK ptap1 A=4p P=8u" in physical
    assert "QREF IREF IREF AVSS BULK" in physical
    assert ".subckt " + sampler.TOP + " " + " ".join(sampler.PORTS) in physical
    assert "sw_et" not in physical and "b=0" in physical


@pytest.mark.parametrize("old,new", [("2.12u","2.04u"),("Nx=4","Nx=3"),("clkn clkp","clkp clkn"),
                                     ("sub ref","avss ref"),("sw_et=1","sw_et=0"),("XLP qn qp","XLP qp qp")])
def test_sampler_source_drift_rejected(old, new):
    assert old in SOURCE
    with pytest.raises(ValueError, match="frozen v2"):
        sampler.physical_reference(SOURCE.replace(old,new,1))


def test_bank_four_exact_receive_paths_and_rail_separation(circuits):
    text = bank.reference(circuits)
    assert len(bank.PORTS) == len(set(bank.PORTS)) == 60
    rows = [v.split() for v in text.splitlines() if v.startswith(("Q","R"))]
    assert len(rows) == len({r[0] for r in rows}) == 260
    assert sum(r[0].startswith("Q") for r in rows) == 92
    assert sum("ptap1" in r for r in rows) == 96
    for lane in range(4):
        for polarity, local in (("P","LP"),("N","LN")):
            assert f"R{lane}SAMPLER_I{polarity} L{lane}_RX_OUT{polarity} L{lane}_SAMPLER_{local}" in text
            assert f"R{lane}SAMPLER_B{polarity} AVDD2V5 L{lane}_SAMPLER_{local}" in text
            assert f"R{lane}RX_R{polarity} AVDD1V8 L{lane}_RX_OUT{polarity}" in text
        assert not any(name in bank.PORTS for name in (f"L{lane}_RX_OUTP", f"L{lane}_SAMPLER_DP"))
    assert " AVDD " not in text
    assert bank.mapped_net(0,"TX","AVDD") != bank.mapped_net(0,"SAMPLER","AVDD")
    assert bank.mapped_net(0,"RX","BULK") == bank.mapped_net(3,"SAMPLER","BULK") == "BULK"


@pytest.mark.parametrize("kind,old,new", [("SAMPLER","DP DN","DN DP"),("RX","RTAP0 SUB BULK ptap1 A=4p P=8u\n",""),
                                         ("TX","RP AVDD","XP AVDD")])
def test_incomplete_bank_primitive_rejected(circuits,kind,old,new):
    circuits[kind] = circuits[kind].replace(old,new,1)
    with pytest.raises(ValueError):
        bank.reference(circuits)


@pytest.mark.parametrize("lane,kind", [(-1,"RX"),(4,"TX"),(0,"CDR")])
def test_invalid_lane_kind(lane,kind):
    with pytest.raises(ValueError):
        bank.mapped_net(lane,kind,"AVDD")


@pytest.mark.parametrize("module,fault", [(sampler_check,f) for f in sampler_check.REFERENCE_FAULTS] +
                         [(bank_check,f) for f in bank_check.REFERENCE_FAULTS])
def test_real_reference_faults_bind_exactly_one(circuits,module,fault):
    text = bank.reference(circuits) if module == bank_check else circuits["SAMPLER"]
    wrong = module.fault_reference(text,fault)
    assert wrong != text
    assert wrong.splitlines()[2] == text.splitlines()[2]
    for bad in ("",text+text,wrong):
        with pytest.raises(ValueError):
            module.fault_reference(bad,fault)


def good_step(count):
    return dict(name="lvs", audit_execution={"returncode":0},audit={
        "status":"PASS within comparison scope", "circuit_status_counts":{"Match":1},
        "circuits":[{"layout_devices_recursive":count,"schematic_devices_recursive":count}]})


@pytest.mark.parametrize("module,count", [(sampler_check,28),(bank_check,165)])
def test_positive_lvs_requires_actual_verdict_all_ports_and_devices(module,count):
    header = ".subckt " + module.TOP + " " + " ".join(module.PORTS) + "\n.ends " + module.TOP
    step = good_step(count)
    module.validate_lvs(step,header,True)
    for path,value in [(('audit_execution','returncode'),1),(('audit','status'),'FAIL'),
                       (('audit','circuits'),[]),(('audit','circuits'),[{"layout_devices_recursive":count-1,"schematic_devices_recursive":count}])]:
        wrong = copy.deepcopy(step)
        target = wrong
        for key in path[:-1]:
            target=target[key]
        target[path[-1]]=value
        with pytest.raises(ValueError):
            module.validate_lvs(wrong,header,True)
    for bad in (header.replace(module.PORTS[0]+" ","",1), header.replace(module.PORTS[0],"UNUSED"),
                header.replace(module.PORTS[0],module.PORTS[1],1)):
        with pytest.raises(ValueError):
            module.validate_lvs(step,bad,True)


@pytest.mark.parametrize("module,clock", [(sampler_check,"CLKP"),(bank_check,"L2_SAMPLER_CLKP")])
def test_clock_open_requires_exact_port_loss(module,clock):
    step = dict(name="clock_open",audit_execution={"returncode":1},audit={"status":"FAIL"})
    header = ".subckt " + module.TOP + " " + " ".join(p for p in module.PORTS if p!=clock)
    module.validate_lvs(step,header,False)
    with pytest.raises(ValueError):
        module.validate_lvs(step,header+" "+clock,False)
    step["audit_execution"]["returncode"] = 0
    with pytest.raises(ValueError):
        module.validate_lvs(step,header,False)


@pytest.mark.parametrize("module", [sampler_check,bank_check])
def test_negative_tool_failure_is_not_a_rejected_fault(module):
    step = dict(name="wrong_load",audit_execution={"returncode":1},audit={"status":"FAIL","circuit_status_counts":{}})
    with pytest.raises(ValueError):
        module.validate_lvs(step,"",False)
    step["audit"]["circuit_status_counts"]={"NoMatch":1}
    module.validate_lvs(step,"",False)


def test_bank_rx_open_bound_to_one_actual_interconnect():
    data={"routes":[dict(net="L2_RX_OUTP",layer="TopMetal2",rect_um=[938,100,942,300])]}
    source=bank_check.mutation_source(Path('/a'),Path('/b'),data,"rx_path_open")
    compile(source,"native_fault","exec")
    assert "l.layer(134,0)" in source and "199.0" in source and "201.0" in source
    for bad in ({"routes":[]},{"routes":data["routes"]*2}):
        with pytest.raises(ValueError):
            bank_check.mutation_source(Path('/a'),Path('/b'),bad,"rx_path_open")


def test_explicit_clock_and_supply_port_types():
    for name in ("CLKP","CLKN","IREF"):
        assert sampler.use_direction(name)==("SIGNAL","INPUT")
    for name in ("QP","QN"):
        assert sampler.use_direction(name)==("SIGNAL","OUTPUT")
    for name in ("AVDD1V8","AVDD2V5"):
        assert bank.use_direction(name)==("POWER","INOUT")
    assert bank.use_direction("L2_SAMPLER_QP")==("SIGNAL","OUTPUT")
    assert bank.use_direction("L2_SAMPLER_CLKP")==("SIGNAL","INPUT")
