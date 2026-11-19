# Preserved-route admission parser correction

Run 44429086292, head 34548906d954e404237f263e1685a91fbc22e41f failed closed before candidate admission. Artifact 14484769685 SHA256 a9ff7c786aa5ae114679cc282cf05f2742f00fc762e3b16e22b1dce5197daf00 and all 11 manifest outputs were verified. The native DEF writer indents NETS entries by four spaces, so the audit parser read zero entries and the minimum coverage assertion rejected the result.

Accept horizontal whitespace before the entry marker and require exact agreement between parsed unique entries, total entries and the DEF section's declared count. Compare all unchanged non-supply net records. New buffer supply terminals legitimately change the supply terminal lists; the existing original-terminal identity, special-wire geometry and separate native power-contact guards remain mandatory. No routed timing or production acceptance is claimed by this preparation.
