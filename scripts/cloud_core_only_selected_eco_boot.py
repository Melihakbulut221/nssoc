#!/usr/bin/env python3
"""Boot the authenticated selected global-route ECO netlist, without modifying producer inputs.

Cloud only. Functional, zero-delay native models; not equivalence or SDF signoff.
"""
import base64
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
from cloud_core_only_postgrt import (ROOT, api, sha, completed, restore_mapping,
    restore_cts, qualify_sources, current_path, archive)
from cloud_core_only_clock_probe import restore_cts8
from cloud_core_only_clock_refine import restore_clock_split, restore_previous
from cloud_core_only_detailed_route import restore_refinement
from cloud_core_only_posteco_extraction import restore_stage
RUN=44328874040
HEAD="733cb000518b8bd6d95470fde5e6e3c3e32bafa6"

OUT = ROOT / "hw/soc/out/core-only-selected-eco-boot"
BOOT_HEAD = "31cb1846a8cf0eb683344e24c27a25438c22a75c"
QUAL_HEAD = "603c4d763128a3c238363c7d15e153eccff565e4"
HARNESS = {
    "flow/sim_logic_boot_gl.py": "d66bd9fbe6aa0e1ce66370b10cf40e94bcc5d5550819b2f1094c2c942bcd0613",
    "tb/tb_soc_logic_boot_gl.v": "42b97d8dd4d8434c87ba11d8e4dc2d16892f7cfb6d57672695d915d068b271ae",
    "tb/mapped_system_mbist_boot_monitor.v": "b1f67afb5b86a75f2fd195a4d756d638793af776939c109aaf59d4d7c6f2802e",
}

def source(path, head):
    obj = api("contents/" + path + "?ref=" + head)
    assert obj["encoding"] == "base64"
    return base64.b64decode(obj["content"])

def restore_route():
    eco,em,eroot=restore_stage(44327965276,'0fbac4d6617c72f3d00a0b759cfc4677bae1b732',
        'core-only-pin-aware-electrical-eco-44327965276',14438605718,
        'sha256:36fcd030bd23666169d392b84668f5bf0cd727d1b4b5f351d75c8a20fd876bb1',
        'hw/soc/out/core-only-pin-aware-electrical-eco')
    assert eco['audit']['new_buffers']==6 and eco['audit']['resized_cells']==4
    report,meta,root=restore_stage(RUN,HEAD,f'core-only-pin-aware-electrical-globalroute-{RUN}',
        14438862280,'sha256:e47da3fe91a279ad2102ee2d84420b226afddd73646b26dceb5ab42c37e05fa8',
        'hw/soc/out/core-only-pin-aware-electrical-globalroute')
    assert report['returncode']==0 and report['source_binding']['eco_run']==44327965276
    initial=root/report['output_state'];state=json.loads(initial.read_text())
    assert sha(current_path(state['odb']))=='4dc086112f1b650df6bd4789aadb8c5de94bebba913055d5fd9a0de827ffc7f8'
    for key in ['nl','odb']:
        p=current_path(state[key]);assert root in p.parents
        assert sha(p)==report['outputs'][str(p.relative_to(root))]
    return report,[em,meta],initial

def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    OUT.mkdir(parents=True, exist_ok=False)
    result = dict(source_head=os.environ["GITHUB_SHA"], status="PREPARING",
        accepted=False, final_timing_complete=False, equivalence_proven=False,
        eco_boot_passed=False, sdf_applied=False)
    def save():
        (OUT/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    try:
        qualify_sources()
        mapping, mapmeta = restore_mapping()
        cts, ctsmeta, config, initial = restore_cts()
        assert cts["source_binding"]["netlist_sha256"] == mapping["outputs"]["synthesis/soc_top.netlist.v"]
        cts8, cts8meta, config, initial = restore_cts8(config)
        split, splitmeta, initial = restore_clock_split()
        previous, prevmeta, initial = restore_previous()
        refined, refmeta, initial = restore_refinement()
        routed, routemeta, initial = restore_route()
        state = json.loads(initial.read_text())
        netlist = current_path(state["nl"])
        result["source_binding"] = dict(route_run=RUN, route_head=HEAD,
            route_state=str(initial), selected_eco_netlist=str(netlist),
            selected_eco_netlist_sha256=sha(netlist),
            original_netlist_sha256=mapping["outputs"]["synthesis/soc_top.netlist.v"],
            artifacts=mapmeta+ctsmeta+[cts8meta, splitmeta, prevmeta]+refmeta+routemeta)
        completed(44239505985, QUAL_HEAD)
        completed(44239816779, BOOT_HEAD)
        sandbox = OUT/"harness/soc"
        for relative, digest in HARNESS.items():
            path = "hw/soc/"+relative
            data = source(path, BOOT_HEAD)
            assert hashlib.sha256(data).hexdigest() == digest, path
            assert data == source(path, QUAL_HEAD), path
            dest = sandbox/relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        # Translate only two diagnostic observers using the authenticated original map.
        canonical_run=completed(44308129454,'78432b99eb354dcb2a7a2d3266ecbb445a31c9cc')
        cz,cm=archive(canonical_run,'core-only-canonical-extracted-timing-native-44308129454')
        assert cm['id']==14429028836 and cm['digest']=='sha256:de85c0ced40577188dcb7af6786736f4f6159025fc41ae9bcdbbd6ec8e57168a'
        sz,sm=archive(canonical_run,'core-only-canonical-extracted-timing-summary-44308129454')
        assert sm['id']==14428669560 and sm['digest']=='sha256:036458784784f5f8e044fef2499f4556c346ff75316df930fc1737e07fff25cf'
        assert cz.read('result.json')==sz.read('result.json')
        cr=json.loads(cz.read('result.json'));assert cr['sources_unchanged']and cr['canonicalization']['binary_readback_verified']
        for name,digest in cr['outputs'].items():assert hashlib.sha256(cz.read(name)).hexdigest()==digest,name
        mapping_raw=cz.read('canonical-name-map.json');name_map=json.loads(mapping_raw)['nets']
        tb=sandbox/'tb/tb_soc_logic_boot_gl.v';original_tb=tb.read_text();adapted=original_tb;translations={}
        assert sha(tb)==HARNESS['tb/tb_soc_logic_boot_gl.v']
        nl_text=netlist.read_text()
        assert hashlib.sha256(mapping_raw).hexdigest()=='a19e410fab8a15fb0337b4d0ccfd50704f08eba76828d5d5b59c5c28826c5187'
        declared={tuple(line.strip()[:-1].split())for line in nl_text.splitlines()if line.strip().endswith(';')}
        for old in ['u_scrub.cnt[0]','u_scrub.cnt[2]']:
            bits={}
            for db_name,new in name_map.items():
                normalized=db_name.replace(chr(92),'')
                if normalized.startswith(old+'[')and normalized.endswith(']'):
                    index=normalized[len(old)+1:-1];assert index.isdigit(),db_name
                    bit=int(index);assert bit not in bits,('ambiguous observer bit',old,bit)
                    assert re.fullmatch(r'nssoc_sta_n_[0-9]+',new)and ('wire',new)in declared,new
                    bits[bit]=dict(original_db_net=db_name,canonical_net=new)
            assert set(bits)==set(range(16)),('incomplete observer bus',old,sorted(bits))
            expression='{'+', '.join('dut.'+bits[bit]['canonical_net']for bit in range(15,-1,-1))+'}'
            token='dut.'+chr(92)+old+' ';assert adapted.count(token)==1,(old,adapted.count(token))
            adapted=adapted.replace(token,expression+' ')
            translations[old]=dict(width=16,order='15 downto 0',bits=bits,expression=expression)
        restored=adapted
        for old,item in translations.items():restored=restored.replace(item['expression']+' ','dut.'+chr(92)+old+' ')
        assert restored==original_tb,'Unexpected harness edits'
        tb.write_text(adapted)
        result['observer_name_adapter']=dict(original_harness_sha256=HARNESS['tb/tb_soc_logic_boot_gl.v'],adapted_harness_sha256=sha(tb),map_sha256=hashlib.sha256(mapping_raw).hexdigest(),translations=translations,only_two_diagnostic_references_changed=True,source_artifacts=[cm,sm])
        (OUT/'observer-name-adapter.json').write_text(json.dumps(result['observer_name_adapter'],indent=2)+chr(10))
        flash = ROOT/"hw/soc/tb/flash_w25q128jv.v"
        assert flash.read_bytes() == source("hw/soc/tb/flash_w25q128jv.v", BOOT_HEAD)
        shutil.copy2(flash, sandbox/"tb/flash_w25q128jv.v")
        original = ROOT/"hw/soc/out/core-only-mainchip"
        synthesis = OUT/"simulation-input/synthesis"
        synthesis.mkdir(parents=True)
        shutil.copytree(original/"synthesis/boot-rom", synthesis/"boot-rom")
        shutil.copy2(netlist, synthesis/"soc_top.netlist.v")
        assert sha(synthesis/"soc_top.netlist.v") == sha(netlist)
        firmware = original/"rtl"
        inputs = [netlist, synthesis/"soc_top.netlist.v", flash, Path(__file__)]
        inputs += [p for p in sandbox.rglob("*") if p.is_file()]
        inputs += [p for p in (synthesis/"boot-rom").rglob("*") if p.is_file()]
        inputs += [p for p in firmware.rglob("*") if p.is_file()]
        protected = {str(p):sha(p) for p in inputs}
        result["protected_inputs"] = protected
        result["qualified_harness"] = dict(head=BOOT_HEAD, qualification_head=QUAL_HEAD, hashes=HARNESS)
        subprocess.run(["python3", "hw/soc/flow/prepare_ihp_native_boot.py"], check=True)
        command = ["python3", str(sandbox/"flow/sim_logic_boot_gl.py"),
            "--simulator", "iverilog", "--cycles", "4000000", "--timeout", "14400",
            "--pcie-profile", "off", "--mbist-profile", "system-only",
            "--nm", "/usr/bin/riscv64-linux-gnu-nm", "--synthesis", str(synthesis),
            "--firmware", str(firmware), "--pdk",
            str(ROOT/"hw/soc/tools/ihp-native-boot-c4b8b4e/ihp-sg13g2"),
            "--output", str(OUT/"simulation")]
        result.update(status="SIMULATING_SELECTED_ECO_NETLIST", command=command);save()
        with (OUT/"native.log").open("w") as log:
            result["returncode"] = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        boot = json.loads((OUT/"simulation/result.json").read_text())
        result["boot_result"] = boot
        assert result["returncode"] == 0 and boot["passed"] and boot["sources_unchanged"]
        assert all(sha(p)==h for p,h in protected.items())
        # Recheck original source binding too; no qualified harness is copied over RTL/flow sources.
        assert all(sha(ROOT/p)==h for p,h in mapping["source_binding"]["before"].items())
        result.update(status="PASS_SELECTED_ECO_NATIVE_FUNCTIONAL_BOOT_REQUIRES_ROUTED_IDENTITY_AND_PHYSICAL_SIGNOFF",
            eco_boot_passed=True, sources_unchanged=True)
    except BaseException as error:
        result.update(status="FAIL_OR_INCOMPLETE", error=repr(error));raise
    finally:
        result["outputs"] = {str(p.relative_to(OUT)):sha(p) for p in OUT.rglob("*")
            if p.is_file() and p!=OUT/"result.json" and p.suffix in (".json", ".log", ".v")}
        save()

if __name__ == "__main__":
    main()
