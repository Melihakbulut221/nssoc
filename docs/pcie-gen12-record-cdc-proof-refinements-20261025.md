# Source review refinements before any CDC execution

The approved 50708f2c source remains immutable and its independent review receipt
remains bound to that exact source. These are explicit pre-execution refinements,
not results from a simulator. The parent approved both narrow changes.

The unmask_stale_fields mutation now removes masking only after synchronized
rd_fault and runs exact_capacity_overflow_sticky_epoch. The positive case fills
the FIFO with known records and holds output before capacity fault. Its mutation
must fail the explicit epoch barrier assertion on known held payload. Startup X/Z
conversion, compile, resource and setup failures remain errors, not behavioral
mutation detection. All other17 mutation definitions and their semantics remain.

The existing partial/reset test always changed polarity during reset. That
independent collector flush could mask a missing coordinated collector reset.
The same named test now also covers both initial polarities, both reset requests
and15 raw-word prefix lengths with unchanged polarity, a60ns settling gap for
pending/held records, then fresh records with different payload seed/offset.
Every original scenario is retained. The named test count remains six direct
plus five composed, to execute in both simulators at depths4/8/32:66 positives.

The old proposal document is a historical interface proposal. The current
implementation contract is docs/pcie-gen12-record-cdc-implementation-20261025.md;
the one-edge public polarity arming stage is now implemented. The frozen design,
collector/codec/CDC/vendor, positive serial/table oracle and field assertions are
unchanged. The additional reset stimuli and one fault definition are the complete
engineering delta. No simulation, synthesis or physical CDC result is claimed.
