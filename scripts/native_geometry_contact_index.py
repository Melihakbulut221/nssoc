#!/usr/bin/env python3
"""Exact rectangle contacts using an x sweep and conservative integer y bins."""
import heapq
from collections import defaultdict

def inter_net_contacts(rows,bin_width):
 assert isinstance(bin_width,int)and not isinstance(bin_width,bool)and bin_width>0
 buckets=defaultdict(set);expires=[];spans={}
 for i in sorted(range(len(rows)),key=lambda i:rows[i]):
  row=rows[i];x0,y0,x1,y1=row[:4];assert x0<x1 and y0<y1
  while expires and expires[0][0]<x0:
   _,j=heapq.heappop(expires);lo,hi=spans.pop(j)
   for k in range(lo,hi+1):
    buckets[k].remove(j)
    if not buckets[k]:del buckets[k]
  lo,hi=y0//bin_width,y1//bin_width;candidates=set()
  for k in range(lo,hi+1):candidates.update(buckets.get(k,()))
  for j in sorted(candidates):
   prev=rows[j]
   if prev[4]!=row[4]and prev[0]<=x1 and x0<=prev[2]and prev[1]<=y1 and y0<=prev[3]:yield(min(i,j),max(i,j))
  for k in range(lo,hi+1):buckets[k].add(i)
  spans[i]=(lo,hi);heapq.heappush(expires,(x1,i))

def qualify():
 import random
 def reference(rows):
  return {(i,j)for i,a in enumerate(rows)for j,b in enumerate(rows)if i<j and a[4]!=b[4]and not(a[2]<b[0]or b[2]<a[0]or a[3]<b[1]or b[3]<a[1])}
 fixtures=[[(0,0,10,10,'a'),(10,10,20,20,'b')],[(0,0,10,10,'a'),(11,0,20,10,'b')],[(0,0,10,10,'a'),(0,0,10,10,'a')],[(0,0,10,10,'a'),(0,0,10,10,'b'),(0,0,10,10,'c')],[(-10,-10,0,0,'a'),(0,0,10,10,'b')],[(-100,-1,100,1,'a'),(-1,-100,1,100,'b')]]
 assert reference(fixtures[0])=={(0,1)}and not reference(fixtures[1])and not reference(fixtures[2])and len(reference(fixtures[3]))==3
 rng=random.Random(20261118)
 for case in range(400):
  rows=[]
  for _ in range(rng.randrange(2,81)):
   x,y=rng.randrange(-200,201),rng.randrange(-200,201);rows.append((x,y,x+rng.randrange(1,101),y+rng.randrange(1,101),str(rng.randrange(5))))
  fixtures.append(rows)
 checks=0
 for rows in fixtures:
  wanted=reference(rows)
  for width in [1,7,32,257]:
   got=list(inter_net_contacts(rows,width));assert len(got)==len(set(got))and set(got)==wanted;checks+=1
 return dict(exhaustive_reference_cases=len(fixtures),bin_width_variants=4,comparisons=checks,integer_edge_and_corner_contacts=True,negative_coordinates=True,duplicate_geometry_pairs=True,same_net_exclusion=True,passed=True)
if __name__=='__main__':
 import json
 print(json.dumps(qualify(),indent=2))
