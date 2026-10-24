# CDR source-contact headroom diagnosis

The source-midpoint contact candidate passed physical checks but its original full loaded nominal early/late simulations remain rejected. Six early and two late HBTs violate the unchanged minimum active VCE of0.4V. The prior parent-AVDD candidate had no such device-bound failures. No source-contact adoption is justified.

The cloud review restores only the immutable original native waveforms, exact composition and native primitive locations. It reproduces all116HBT device checks on every original sample and maps each primitive to exactly one of the16physical parent macros. It reports actual C/B/E voltages, collector current, supply voltage and time at the worst active VCE, plus the count and first/last time of below-limit samples. There is no interpolation, resimulation, new stimulus or acceptance change. It rejects missing/ambiguous physical owners and tests current-per-emitter and active-window handling with a known vector.

The large source captures remain in their original releases; the new release contains only this diagnostic, exact source checksums and report. Local CAD data is neither needed nor retained. These observations locate the failure but do not establish a causal repair or a recovered-clock PHY result.
