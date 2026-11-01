# Mixed20 original-gate comparison

Native candidate41282867236/source8c7b5cdd86447fe374ae06064f2fef735a7c9b91 changes exactly20 resistor lengths versus the original500-device circuit. A/B output loads191/194/202/205 use1.5um/W32; C/D175/176/212/214 remain original2.6um/W32. Original master loads and every other non-target parameter remain unchanged.

Comparator source012413d60813e041336e3864ba521509d29094c5, branchcodex/cdr-mixed20-comparison, is derived from actual A/C comparatoracd818570761e1b715b951d4aba5978c654af1e9. The original gates() AST is identical. Complete binding equality permits only the20 declared length tokens; candidate metadata must explicitly name the four restored C/D loads.

Controls run41283355867 passed18 corruption refusals. In addition to the retained16 checks, they reject an altered retained A/B load and a false restored-C/D declaration. The old175 length/width corruptions now explicitly check that restored C/D devices remain original. Full10-file proof3c3500b813a432b34582416f1071d13f16fdc1e1, docs/evidence/cdr-sampler-load-comparison-controls-41283355867.

At the initial prepared-source revision the candidate report pin was deliberately absent. After native completion, the full453667-byte report SHA256096476d0dc446b3e16ad5e2263b5d73f5b4be43c8ccc031bbdd9cfda6d20b643 was bound with its exact native context. Source qualification is not electrical acceptance. Preserve all124 HBTs,50MOS,7MIM, complete tail groups, six stages1530 delays, stimulus, phase and VI predicates and every failing result.

## Actual comparison

Run41284059156/source93458f9d15f762a194bb02d9314a8d211a9c1d80 succeeded after repeating all18 controls. Full15-file proofafd1a4f68e882c3124867e6eca2f34600b951875, docs/evidence/cdr-sampler-load-comparison-41284059156. All original screen gates remain false overall; onlyB sampler passes, devices and VI pass, phase and A/C/D/X/Y fail. All124 HBT changes and all1530 original/candidate delay arrays are preserved. A successful comparison job confirms evidence integrity, not circuit acceptance.
