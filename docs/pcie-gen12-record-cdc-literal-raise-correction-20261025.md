# Exact explicit assertion classification correction

The first source-controls run 40191223737 at af3efe229f75860f71f407cae33908ee3dc6f253 failed before RTL simulation or synthesis. Its complete 11,460-byte result is preserved with SHA256 69e5415121c88131f77831175e5018fede9b01f47b6fe5baa39f92048d2c54d2. The classifier admitted only Python assert statements, while the unchanged public-port harness until() raises AssertionError('bounded public-port scenario timeout') explicitly. This left hide_loss without an admitted source site.

The correction preserves existing ast.Assert admission and additionally recognizes only an ast.Raise with no cause, calling the literal Name AssertionError with exactly one literal string argument equal to the existing bounded public-port timeout message. The mutation's existing allowed-message table must also contain that message. The actual final traceback source path and line remain mandatory. Dynamic messages, exception aliases, arbitrary exceptions, chained causes, keyword or extra arguments, and bare re-raises are not admitted.

Thirteen additional classifier controls cover the actual pinned raise site, wrong runtime exception/message/file/line, and eight non-admitted source forms. The original 36 controls remain; the hosted required count is 49. Original RTL, public-port oracle, scenarios, mutation definitions, positive 66-test plan, mapped 33-test plan and 18 compiled mutations are unchanged. Source controls do not execute these engineering tests.

This is a source-only correction pending independent review and one explicitly authorized hosted controls retry. Native execution remains disabled. The preserved failure does not imply an RTL defect or any functional acceptance.
