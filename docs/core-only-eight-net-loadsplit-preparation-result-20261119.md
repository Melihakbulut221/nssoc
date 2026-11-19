# Eight-net load split preparation result — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44555127293 passed at bb26e933787c729110c6fa16167bfa44a393e2dc.
Artifact 14544652590 SHA256 2d0eebbd815fa2411933ddddadc8c5a8eeeed8c15793d7424f6ea74be5d65daf: all 17 outputs independently verified.
Candidate ODB 3c55f2e88aff518b5483e10760b2d75042856d2b77616526bc731cb2083fd7c3; source ODB bd28f784aa3cad49b72197de70c394727ab0e72608610febd4c4e16dfc4a28bc.

21 added sg13g2_buf_8 cells; 106693 total instances. All original placement geometry preserved. Collapsing the inserted identity buffers recovers every original terminal connection, including 44 explicitly moved diode signal pins. All original diodes preserved. All 42 new power terminals contact correct supply rails; synthetic controls and actual rail-removal control passed. 103086 unaffected nonpower net records, 2113 clocks and NDR assignments preserved.

Next: route the eight changed source nets and 21 new output nets. All other routes are encoded FIXED during DRT and restored to ROUTED afterward; verify identities, exact unaffected routes, native geometry and antennas. Fresh RC/STA required before claiming electrical improvement.

Superseded run 44555002964 was cancelled after source review found two numeric assertions damaged by an overly broad text substitution. The count correction was committed before this successful run; no assertion or physical requirement was relaxed.
