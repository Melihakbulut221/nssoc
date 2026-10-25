#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Render measured TX waveforms with gnuplot; no synthetic eye generation."""
import argparse
from bisect import bisect_left
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

from characterize_pcie_tx import ROOT, START, UI


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='Fresh plot directory')
    parser.add_argument('--gnuplot', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Use a fresh output directory')
    result = json.loads((args.run/'result.json').read_text())
    for source, expected in result['sources'].items():
        if hashlib.sha256((ROOT/source).read_bytes()).hexdigest() != expected:
            raise ValueError('Characterization source changed; use its recorded revision')
    candidates = [c for c in result['cases'] if c['fault'] is None and
                  c['lanes'] == 1 and c['name'].startswith('hbt_')]
    nominal = next(c for c in candidates if c['name'] == 'hbt_typ_27_1.8')
    worst = min(candidates, key=lambda c: c['measurements']['lanes'][0]['min_signed_margin_v'])
    args.out.mkdir(parents=True)
    for name, case in [('nominal', nominal), ('worst', worst)]:
        raw = gzip.decompress((args.run/case['name']/'wave.dat.gz').read_bytes())
        if hashlib.sha256(raw).hexdigest() != case['wave_sha256']:
            raise ValueError('Waveform identity changed')
        rows = [list(map(float, line.split())) for line in raw.decode().splitlines()[1:] if line.strip()]
        times = [r[0] for r in rows]
        with (args.out/(name+'.dat')).open('w') as output:
            # First PRBS period after settling. The measured adaptive samples
            # are retained; this renderer performs no smoothing/interpolation.
            for bit in range(16, 143):
                t0 = START+bit*UI
                for row in rows[bisect_left(times, t0):bisect_left(times, t0+2*UI)]:
                    output.write(f'{(row[0]-t0)*1e12:.6f} {row[3]-row[4]:.9f}\n')
                output.write('\n')
    script = '''set terminal pngcairo noenhanced size 1500,650 font "Sans,15"
set output "tx-eye.png"
set multiplot layout 1,2 title "SG13G2 experimental TX, 8 GT/s | pre-layout, ideal R, no channel or jitter"
set xlabel "Time (ps); UI = 125 ps"
set ylabel "OUTP - OUTN (V)"
set xrange [0:250]
set yrange [-0.65:0.65]
set grid xtics ytics
unset key
set title "Typical, 27 C, 1.8 V"
plot "nominal.dat" using 1:2 with lines lc rgb "#3b80b3" lw 0.6
set title "Worst sampled PVT margin: WORST\\nRecovered solver warning; review required"
plot "worst.dat" using 1:2 with lines lc rgb "#b76837" lw 0.6
unset multiplot
'''.replace('WORST', worst['name'])
    (args.out/'plot.gp').write_text(script)
    subprocess.run([str(args.gnuplot.resolve()), 'plot.gp'], cwd=args.out, check=True)
    (args.out/'plot.json').write_text(json.dumps(dict(
        nominal=nominal['name'], worst=worst['name'],
        result_sha256=hashlib.sha256((args.run/'result.json').read_bytes()).hexdigest(),
        image_sha256=hashlib.sha256((args.out/'tx-eye.png').read_bytes()).hexdigest(),
        tool_version=subprocess.check_output([str(args.gnuplot.resolve()), '--version'], text=True),
        tool_sha256=hashlib.sha256(args.gnuplot.read_bytes()).hexdigest(),
    ), indent=2)+'\n')


if __name__ == '__main__':
    main()
