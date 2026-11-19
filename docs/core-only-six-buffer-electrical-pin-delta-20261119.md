# Six-buffer electrical pin comparison — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44553301571 succeeded at cefd62838ad0cb00e176200d48ca1426cb792144.
Artifact 14544545780 SHA256 `e2596f5ad7528f37a0ee5396fd4d58875a853cf73dff6bf4dcd5eb9e7cf71c22` verified, including the three corner pin-report hashes. Complete parser counts match native metrics, including blank printed fanout slack.

No added slew, fanout or capacitance violating pins in any corner. Sixteen slow-corner slew pins removed; nssoc_sta_i_61007/Y fanout violation removed in all three corners. Capacitance violating-pin sets unchanged.

Next measured targets: nssoc_sta_i_8564/Y slew 3.255274 ns (wire1734/A 3.257586 ns), nssoc_sta_i_52754/Y 3.228742 ns against 2.5074 ns; nssoc_sta_i_63235/Y fanout 24 against 8 and capacitance up to 0.344029 against 0.3; fanout4366/X and fanout5013/X each 20 loads against 8; fanout5181/X capacitance up to 0.373955 against 0.3. Extract native connectivity, cell strengths and load locations before choosing the next ECO. These candidate targets are not yet modified.
