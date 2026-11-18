#!/usr/bin/env python3
"""Generate real native Tcl adapters without claiming a circuit was analyzed."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'hw/soc/pnr'))
from librelane.common import get_script_dir
from core_only_detailed_route_flow import CoreDetailedRouting, CoreOnlyDetailedRoute
from core_only_routed_extraction_flow import CoreExtractedSTA, CoreOnlyRoutedExtraction
from core_only_routed_guards import CLOCK_GUARD

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    out = ROOT / 'hw/soc/out/core-only-extracted-guards/native-adapters'
    out.mkdir(parents=True, exist_ok=False)
    results = {}
    # Script generation uses no database or environment/config fields. Bypass
    # Step initialization only for this generation test; never run these objects.
    for name, cls in [('route', CoreDetailedRouting), ('extracted_sta', CoreExtractedSTA)]:
        step = object.__new__(cls)
        directory = out / name
        directory.mkdir()
        step.step_dir = str(directory)
        script = Path(step.get_script_path())
        assert directory in script.parents and script.is_file()
        text = script.read_text()
        if name == 'extracted_sta':
            assert text.count(CLOCK_GUARD) == 1
            assert 'namespace exists ::ord' in text
            assert text.index('read_spefs\n') < text.index(CLOCK_GUARD)
            assert 'set_propagated_clock' not in text
            assert 'pcie_clk_i' not in text and 'eth_rx_clk_i' not in text
        else:
            assert 'prune_orphan_guides' in text
            assert 'Core-only requires exactly one clock' in text
            assert 'Core-only requires clk_i at 20 ns' in text
            assert 'TIME_DERATING_CONSTRAINT loses precision' in text
        results[name] = dict(script=str(script.relative_to(out)), sha256=sha(script))
    native = Path(get_script_dir()) / 'openroad/sta/corner.tcl'
    assert native.is_file()
    report = dict(status='PASS_NATIVE_SCRIPT_GENERATION_NOT_PHYSICAL_SIGNOFF',
        native_sta_source=str(native), native_sta_sha256=sha(native),
        adapters=results, detailed_route_steps=[c.id for c in CoreOnlyDetailedRoute.Steps],
        extraction_steps=[c.id for c in CoreOnlyRoutedExtraction.Steps],
        actual_database_spef_execution=False, accepted=False)
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))

if __name__ == '__main__':
    main()
