# Current target resistor ancestry — actual cloud result

Run 40988946484 at source 2adbc74a348c6f04227a9507a9ccc556d4eda430 succeeded in all four jobs. New hosted controls passed 6 positive/18 refusal/3 lifecycle; all inherited controls also passed. The complete 329890-record sidecar and 949094893-byte native capsule remain on release 428576457.

R2997 (T003_D to T065_E.n53) and R12299 (T032_D to T119_E.n53), each 32.5083 ohm, have matching five-constructor, four-series histories: Via2, Metal3 access, Via1, short Metal1 landing and long Metal1 drain access. The full selected constructor/transition records are in diagnosis.json; both complete target graphs and event streams are preserved under assets/.

This makes the drain-side Metal1 access and single-cut Via1/Via2 landing a concrete next geometric investigation. It does not choose a width/cut count or assign the entire resistor to a surviving tile. Raw coordinates must still be joined to current GDS and clearance/enclosure rules. R2966 is a useful counterexample: 13 roots include triangle reductions, so exclusive footprint ownership remains unproved.

The original resistor/rnode file is byte-exact. The existing strict ordered comparison remains explicitly false; the unchanged qualified component comparison accepts only the established exact capacitor identity/order bijection. No geometry, device values, electrical gates or acceptance flags changed. No local native payload, computation, test or build was used.
