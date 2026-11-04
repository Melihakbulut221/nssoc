# N1 actual650 phase-detector trace

Source: preserved native waveform of run41733225660 (artifact13283214752, raw SHA17ee3df91074c5c3612dbc878455ec39db102b4c49cc735ba19814c0d5c974d3, 113490 points, 1751 vectors). Run41774032757 sampled every vector at 16 phases per unit interval inside the hosted job. Nominal_late case: external 8 GHz clock, data 0.15 UI late, unchanged 150 fF sampler and 50 fF XOR loads. This is a diagnosis of a rejected candidate, not an acceptance.

## Device gate census

Of 124 HBTs, two fail: xd0211 and xd0212 (nx2) with minimum active Vce 0.384 V and 0.382 V against the 0.4 V gate. All 200 MOS pass their terminal-voltage gates, all 16 physical stage tails stay above 0.5 mA (minimum 1.50 mA), and no MIM exceeds 1.6 V. `devices_passed=false` comes only from these two devices; the data and phase failures are separate.

## Where the data is lost

Each signal is the differential of its schematic net, averaged over the device terminals the composition contract maps to that net. Lag is the delay after the start of bit k at which the sign best agrees with bit k; agreement is the fraction of bits 8-249 with matching sign at that lag.

| Net | Stage | Lag (UI) | Agreement | Median abs (V) |
|---|---|---:|---:|---:|
| aqp-aqn | sampler A output | 0.875 | 1.00 | 0.115 |
| uap-uan | A divider output (buffer input) | 1.812 | 0.94 | 0.108 |
| adp-adn | A data buffer output (XOR input) | 2.562 | 0.83 | 0.162 |
| cqp-cqn | sampler C output | 1.875 | 1.00 | 0.115 |
| ucp-ucn | C divider output | 2.938 | 0.89 | 0.075 |
| cdp-cdn | C data buffer output | 2.875 | 0.72 | 0.132 |
| dqp-dqn | sampler D output | 1.875 | 1.00 | 0.092 |
| usp-usn | select divider output | 2.812 | 0.83 | 0.037 |
| s0p-s0n | select buffer output (XOR input) | 2.938 | 0.76 | 0.074 |

All four samplers resolve every bit. The loss happens after them. Each sampler-to-buffer rppd divider adds about one unit interval (0.94-1.06 UI) and attenuates; the select divider leaves only 37 mV. A transfer-function fit of divider output against sampler output gives a single pole of 108 ps (A), 80 ps (C) and 44 ps (select) with near-zero high-frequency gain: the MIM bypass is far too small for the capacitance at the buffer input. From the A pole and R1||R2 of about 0.8 kOhm, that node carries about 135 fF in total, of which the 3.6 x 3.6 um MIM is about 19 fF. A compensated divider needs C1 = C2 * R2/R1, about six times C2 here.

## Why the XOR comparisons fail

XOR-X output follows -(A * S0) of its own inputs in 77% of bits at every evaluation phase. The cell multiplies; its inputs are wrong for the oracle. Buffered A arrives at 2.56 UI and S0 at 2.94 UI, so they are 0.4-0.56 UI apart and both later than the frozen evaluation window (bit start + 1.1-1.4 UI). With random data, X then agrees with its expected transition flag only at chance (388/765 wrong sign). Y appears better (44 wrong) only because its nominal_late expectation is constantly zero. The phase average (x-y, 14 mV against the 30 mV gate) is low for the same reason: skewed, attenuated XOR inputs.

The frozen gate requires the XOR output valid 0.25-0.45 UI (31-56 ps) after its sampler inputs settle. Divider plus buffer currently take about 1.7 UI (210 ps). Meeting the gate needs a delay-free (compensated or DC-coupled) level shift and a buffer/XOR pair of a few CML stage delays; reducing divider resistance alone cannot remove the buffer delay.

## What-if reruns

Runs41775302761 and41786313115 rerun the same N1 bench. Every extracted wire R/C, device, source, load and solver option is unchanged; only the listed instance values (and, for fastbuf, four bench bias sources) are rewritten. The frozen `measure_wave` judges each case with unchanged thresholds.

| Variant | Change | Phase avg (gate >= 30 mV) | VI current / output (>= 50 uA / 5 mV) | X wrong / below 100 mV | Y wrong | Sampler c / d wrong | Failing HBT |
|---|---|---:|---:|---:|---:|---:|---|
| control | none | 14.0 mV | 42.1 uA / 11.8 mV | 388 / 727 | 44 | 1 / 34 | xd0211, xd0212 |
| lowz4 | 12 divider rppd 1 -> 4 um, divider MIM area x4 | **38.3 mV** | **104 uA / 30.3 mV** | 432 / 705 | 0 | 0 / 20 | xd0211, xd0212 |
| compensated | A/C MIM 21.6 um, select MIM 9.6 um | **42.6 mV** | **125 uA / 37.0 mV** | 389 / 725 | 1 | 8 / 38 | xd0211, xd0212 |
| fastbuf | lowz4 + buffer bias x2, buffer loads R/2 | **36.6 mV** | **108 uA / 31.8 mV** | 413 / 723 | 0 | 0 / 21 | xd0211/0212 + 8 XOR tail-pair HBTs |

`control` reproduces N1 exactly (phase, comparisons, VI and failing devices), so the harness is faithful. lowz4 is the cleanest change: phase and VI pass, Y becomes clean, sampler C/D improve, and no new device fails. The buffered A input arrives 0.31 UI after the sampler instead of 0.94 UI. compensated shortens the divider further but its large MIMs load the samplers (C 8, D 38 wrong). fastbuf trims the buffer delay from 0.75 to 0.56 UI, but it moves XOR tail-pair headroom below the 0.4 V gate.

What still fails in every variant:

- The XOR per-bit comparison gate. XOR inputs now align with each other, but they arrive about 1 UI after the frozen window (valid by 0.6 UI after the clock edge). The window requires sampler-to-XOR-output latency of 0.25-0.45 UI. The measured latency with the lowz4 divider is about 0.3 UI of divider, 0.56-0.75 UI of buffer and the XOR delay. Meeting that window in this topology needs a different interface (for example DC-coupled emitter-follower level shifting into a smaller XOR input stage), not only resizing. Since the window, unlike the phase average, is latency-sensitive, whether a pipelined evaluation would serve the loop equally is a gate decision that is not taken here.
- Sampler amplitude: about 129 of 765 sampler samples are below 100 mV, at the 0.3 UI phase of transition bits (clock-to-valid up to 46.7 ps against the 37.5 ps gate).
- Sampler D: 20 wrong-sign samples.
- xd0211/xd0212, the clock-steering pair of the D master latch, with minimum Vce 0.38 V against 0.4 V. Their collector node follows the retimed-B input common mode set by the B-to-D divider.

Recommended next candidate: lowz4 in layout (twelve divider resistors at 4 um width, six divider MIMs at twice the side length), followed by fresh DRC, LVS and extraction and the same full650 bench. The XOR window and sampler timing remain open design work.
