#!/usr/bin/env python3
"""Strict fanout rows; retain blank printed slack without omitting violations."""
import re

def parse_rows(section):
 rows=[];seen=set()
 for line in section.splitlines():
  if '(VIOLATED)'not in line:continue
  m=re.fullmatch(r'(\S+)\s+(\d+)\s+(\d+)(?:\s+(-?\d+))?\s+\(VIOLATED\)\s*',line)
  assert m,('Malformed fanout violation',line)
  pin,limit,fanout,printed=m.groups();limit=int(limit);fanout=int(fanout)
  assert fanout>limit and pin not in seen,(pin,limit,fanout)
  if printed is not None:assert int(printed)==limit-fanout,('Wrong printed slack',line)
  seen.add(pin);rows.append((pin,limit,fanout,printed))
 return rows

def controls():
 assert parse_rows('buf/X 8 22 -14 (VIOLATED)')==[('buf/X',8,22,'-14')]
 assert parse_rows('buf/X 8 9     (VIOLATED)')==[('buf/X',8,9,None)]
 bad=['buf/X 8 9 -2 (VIOLATED)','buf/X 8 8 0 (VIOLATED)','buf/X x 9 (VIOLATED)','buf/X 8 9 NaN (VIOLATED)','buf/X 8 9 (VIOLATED) garbage','buf/X 8 9 (VIOLATED)\nbuf/X 8 9 (VIOLATED)']
 for line in bad:
  try:parse_rows(line)
  except AssertionError:pass
  else:raise AssertionError(('Accepted malformed report',line))
 return dict(positive=2,negative=len(bad))
if __name__=='__main__':print(controls())
