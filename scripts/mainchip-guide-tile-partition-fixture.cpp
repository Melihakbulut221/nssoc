// SPDX-License-Identifier: BSD-3-Clause
#include <algorithm>
#include <cassert>
#include <climits>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
#include "MainchipGuideTilePartition.h"
struct Rect {
  int x0,y0,x1,y1;
  Rect(int a,int b,int c,int d):x0(a),y0(b),x1(c),y1(d){}
  int xMin()const{return x0;} int xMax()const{return x1;}
  int yMin()const{return y0;} int yMax()const{return y1;}
};
// Independent coverage oracle: sample every boundary and every open slab in
// doubled integer coordinates. Coverage is constant within each such slab.
bool covered(const Rect& r,const std::vector<Rect>& pieces,int64_t mx,int64_t my) {
  if(pieces.empty())return false;
  std::vector<int64_t> xs{2LL*r.x0,2LL*r.x1},ys{2LL*r.y0,2LL*r.y1};
  for(const auto&p:pieces) {
    if(p.x0<r.x0||p.x1>r.x1||p.y0<r.y0||p.y1>r.y1||p.x0>p.x1||p.y0>p.y1
      ||int64_t(p.x1)-p.x0>mx||int64_t(p.y1)-p.y0>my)return false;
    xs.push_back(2LL*p.x0);xs.push_back(2LL*p.x1);
    ys.push_back(2LL*p.y0);ys.push_back(2LL*p.y1);
  }
  auto samples=[](std::vector<int64_t> v){
    std::sort(v.begin(),v.end());v.erase(std::unique(v.begin(),v.end()),v.end());
    auto out=v;for(size_t i=1;i<v.size();++i)out.push_back((v[i-1]+v[i])/2);
    return out;
  };
  for(auto x:samples(xs))for(auto y:samples(ys)){
    bool found=false;
    for(const auto&p:pieces)if(2LL*p.x0<=x&&x<=2LL*p.x1&&2LL*p.y0<=y&&y<=2LL*p.y1){found=true;break;}
    if(!found)return false;
  }
  return true;
}
int main(){
  int cases=0;
  for(int w:{0,1,6,7,8,13,14,19,30})for(int h:{0,1,6,7,8,13,20})
    for(int overlap:{0,1,3,6}) {
      Rect r(-11,-9,-11+w,-9+h);
      auto tiles=drt::nssoc::partitionGuideTile(r,7,7,overlap,overlap);
      assert(covered(r,tiles,7,7));++cases;
    }
  for(const auto&r:std::vector<Rect>{
      Rect(INT_MAX-32,INT_MAX-42,INT_MAX,INT_MAX),
      Rect(INT_MIN,INT_MIN,INT_MIN+32,INT_MIN+42),
      Rect(INT_MIN,-1,INT_MAX,1)}) {
    auto tiles=drt::nssoc::partitionGuideTile(r,1000000000LL,1000000000LL,1,1);
    assert(covered(r,tiles,1000000000LL,1000000000LL));++cases;
  }
  Rect r(0,0,30,20);
  auto good=drt::nssoc::partitionGuideTile(r,7,7,1,1);
  auto missing=good;missing.erase(missing.begin());assert(!covered(r,missing,7,7));
  missing=good;missing.pop_back();assert(!covered(r,missing,7,7));
  auto oversized=good;oversized.emplace_back(0,0,30,20);assert(!covered(r,oversized,7,7));
  auto outside=good;outside.emplace_back(-1,0,1,1);assert(!covered(r,outside,7,7));
  int refused=0;
  for(const auto&bounds:std::vector<std::vector<int64_t>>{
      {0,7,0,0},{7,0,0,0},{7,7,-1,0},{7,7,0,-1},{7,7,7,0},{7,7,0,7}}){
    try{drt::nssoc::partitionGuideTile(r,bounds[0],bounds[1],bounds[2],bounds[3]);}
    catch(const std::invalid_argument&){++refused;}
  }
  assert(refused==6);
  std::cout<<"PASS_GUIDE_PARTITION cases="<<cases<<" invalid_bounds="<<refused<<" coverage_faults=4\n";
}
