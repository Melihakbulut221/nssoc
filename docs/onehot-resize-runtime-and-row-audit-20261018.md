# Measured buffer resizing: runtime and placement audit

Runs 39158947092 and 39159593744 failed before sizing due to nested AppImage invocation and a pathlib argument error. These are retained failures, not accepted physical work. Run 39159839767 reached native resizing and passed native detailed placement/check_placement but failed an overly restrictive target-orientation equality check. It produced no accepted candidate.

Only selected resized targets may relocate. A neighboring placement row can require a different orientation. The revised audit records each target before/after and requires its complete new bounding box to fit a native row with the same site and orientation. Unselected instances must still retain every master, pin, location and orientation; PG geometry and all nets/ports/NDRs remain unchanged. Native check_placement must still pass. The JSON topology signature now uses lists consistently across serialization.

API basis: [OpenDB dbRow getBBox/getOrient/getSite](https://openroad.readthedocs.io/en/latest/doxygen_output/html/classodb_1_1dbRow.html). This is a placement preparation, not routing, transistor LVS or timing closure. All signal routes are discarded and must be regenerated with fresh RC/STA before timing claims.
