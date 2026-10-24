# Timing-priority TX physical result and source-contact CDR rejection

TX physical run39304550527 passed native560categoryDRC, deep/flat1674deviceLVS and original fault controls. Final-stage maximum route fell2268.8to1090.8um; global maximum remains2374um.24upstream legs became longer and total wire length increased to90615.2um. All1674devices and child drawings are unchanged. This candidate requires fresh native RC and unchanged full loaded gates; no electrical or fullPHY acceptance.

CDR source-contact run39302582087 used the verified484device17258R12445C model. Both nominal cases completed with native exit0 and no diagnostics but failed original sampling and device gates. Clock-stopped and VI-bias-off faults were detected; this does not validate nominal operation.

| Case | A/B/C/D wrong-sign samples | Minimum HBT VCE (V) | HBTs below0.4V | Phase (V) | VI signed current (uA) |
|---|---|---:|---:|---:|---:|
| nominal_early | 69/129/186/339 | 0.386162076 | 6 | 0.020466800 | 38.231639 |
| nominal_late | 89/0/188/319 | 0.386461451 | 2 | 0.042298638 | 88.954819 |

The original parent-AVDD nominal device gates passed; the source-contact addition therefore introduced a device-headroom regression despite reducing some data errors. It is retained as a rejected candidate, not promoted as an electrical fix. The worst new HBT is xpd.xd0129, with minimumVCE about0.386V. Original100mV,37.5ps,phase/current and device limits remain unchanged. Physical/RC PASS does not override loaded rejection.

All raw captures and CAD artifacts remain in cloud releases.
