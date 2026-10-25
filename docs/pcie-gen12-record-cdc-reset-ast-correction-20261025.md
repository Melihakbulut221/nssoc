# Reset predicate classifier correction — 2026-10-25

Actual run 40196820337 at f028f7f0524cbe8f504fca6b4c21108f6a18cca5 passed all 66 named RTL executions, 33 mapped executions and six complete synthesis/check jobs. Nine compiled mutants were classified as detected. The tenth, ignore_read_reset, compiled successfully and reached the real reset barrier assertion at pcie_gen12_record_cdc_harness.py:206 at 1756.30 ns. The strict classifier rejected that unqualified site; the run remains failed.

The predicate was already declared in EXPRESSIONS for both reset mutants. ast.unparse inserts parentheses around the second not expression, so string equality failed even though the predicate AST is identical. Only those two reset mutants now compare existing declared predicate ASTs without source-location attributes. Existing message-based sites, the other expression lists, final traceback file/line binding, XML AssertionError requirements, compile admission and all resource/error gates are unchanged.

No harness, RTL, input, timing, queue oracle, source mutation or simulator behavior changes. The 14 added classifier cases exercise the actual two pinned reset assertion sites for both mutations, equivalent parentheses, changed operator/ports/negations/output width, a non-assert node, wrong XML exception/source/line and a zero return code. This adds to all 49 prior controls, requiring 63 total.

The exact failed result and complete 4,095-byte stdout are preserved in the failure receipt. No retroactive tenth-mutant detection or complete transport qualification is claimed. The remaining eight mutations were not reached. Current native authorization is false; this source-only correction needs independent review and hosted controls before any separately approved complete proof.
