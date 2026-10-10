# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Keep every declared570 vector, within ngspice47's1000argument command limit."""
BATCH=128

def verify(lines,expected):
 assert len(expected)==1133 and len(set(expected))==1133,'Exact1133 unique observations'
 tokens=[line.split()for line in lines]
 assert all(t[0]=='save'and 1<=len(t)-1<=BATCH for t in tokens),'Bounded save command arity'
 flat=[v for t in tokens for v in t[1:]]
 assert flat==expected,'Exact ordered observation list without missing duplicates or reordering'
 return flat

def commands(expected):
 assert all(v and not any(c.isspace()for c in v)for v in expected),'Single-token observations'
 lines=['save '+' '.join(expected[i:i+BATCH])for i in range(0,len(expected),BATCH)]
 verify(lines,expected)
 return lines

def replace_save(deck,expected):
 old='save '+' '.join(expected)+'\n'
 assert deck.count(old)==1,'Exactly one original complete save statement'
 return deck.replace(old,'\n'.join(commands(expected))+'\n')
