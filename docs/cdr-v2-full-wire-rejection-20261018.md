# CDR v2 full-wire loaded rejection

Run [39081843889](https://github.com/Melihakbulut221/nssoc/actions/runs/39081843889), source `34cc19546680b2662983355e0241a324cc66adb4`, completed. Both nominal jobs failed their original data and device gates. Stopped-clock and VI-bias-off controls completed successfully as fault detections. No PHY acceptance is claimed.

The unchanged physical model includes 394 devices, 8956 resistors and 7079 capacitors. The simulator returned zero with no diagnostics, verified all 122 HBT OFF flags and zero-source operating point, and retained source hashes. This is an electrical rejection, not a simulator startup failure.

| Nominal case | A wrong / 765 | B wrong / 765 | C wrong / 765 | D wrong / 765 | Mean phase difference |
|---|---:|---:|---:|---:|---:|
| Early | 100 | 277 | 345 | 365 | +0.02500842 V |
| Late | 133 | 84 | 347 | 349 | +0.02378805 V |

Early polarity is wrong; late magnitude is below the unchanged 0.03 V phase gate. Neither nominal case passes sampling. Seven native HBTs in each case violate the 0.4 V active VCE minimum: xd0053, xd0075, xd0083, xd0091, xd0106, xd0114, xd0122. The two worst tail devices are approximately 0.245 and 0.251 V. These are device IDs in the v2 extraction and must not be mapped using v1 numbering.

The late select0/select1 differential ranges are approximately -0.027 to +0.066 V, compared with the expected switching function. This localizes a weak interface but does not establish its physical root cause. Inspect the actual source devices and distributed metal/RC before proposing repair. The wider supply feed and reordered macros did not close the full electrical gates.

`evidence/cdr-v2-full-wire-rejection-20261018.json` pins all four summary hashes, archive manifests and selected report fields. Complete captures remain in their GitHub Releases. Only summary/manifest bytes were read for this checkpoint; this receipt does not claim independent download or revalidation of the large waveform archives. No local artifact or checkout was created.
