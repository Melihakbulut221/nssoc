# Current AVSS18 first p-high transient: complete electrical rejection

The sole run [40323469809](https://github.com/Melihakbulut221/nssoc/actions/runs/40323469809) completed the original 34 ns capture at source `5a712e76807579a7736c24f602a204c481c001b7`. The native engine returned zero with no numerical diagnostics; all 114,525 rows and 4,727 columns were captured. The workflow then rejected the original electrical gates. All publication steps succeeded. There is no saved process to resume.

The original 17 HBT failures decreased to four, all in xdut: XD75 (0.399897 V), XD83 (0.398132 V), XD98 (0.395908 V), and XD105 (0.395448 V), against the unchanged 0.4 V lower limit. Both child macros pass the HBT screen. This is a measured extrema comparison; it does not establish the same-time cause.

Signal margins and phase still fail. xdut first-fall delays are 150.934 ps and 163.306 ps, above the unchanged **62.5 ps** gate. The 100 mV signal margin and prescribed sampling phases remain unchanged. No other case, transient retry, geometry change, or continuation is authorized.

The full summary, current restoration and actual 18 source/32 path refusal outcomes, four complete source-control records, full source/native logs, release and tag metadata, complete archive manifest, and a bounded original/current comparison are preserved beside the [terminal receipt](evidence/tx-phase-reset334-avss18-p-high-native-rejection-20261026.json). The native log independently reconstructs the complete summary from 515 numbered chunks. Four archive parts remain in the exact-source cloud prerelease; no raw/archive was downloaded locally.
