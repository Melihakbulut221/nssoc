#include <algorithm>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
namespace support {
void check(bool ok, const std::string& message) {
  if (!ok) throw std::runtime_error(message);
}
struct frNet { bool fixed; bool isFixed() const { return fixed; } };
struct drConnFig { int id; explicit drConnFig(int v) : id(v) {} };
struct drNet {
  frNet parent;
  std::vector<std::unique_ptr<drConnFig>> figs;
  int clear_calls=0, ripup_calls=0;
  bool ripup=false;
  drNet(bool f, int count, int start) : parent{f} {
    for (int i=0;i<count;++i) figs.emplace_back(std::make_unique<drConnFig>(start+i));
  }
  frNet* getFrNet() { return &parent; }
  auto& getRouteConnFigs() { return figs; }
  void clearRouteConnFigs() { ++clear_calls; figs.clear(); }
  void setRipup() { ++ripup_calls; ripup=true; }
};
struct Marker {
  int layer; std::vector<drNet*> hits;
  int getLayerNum() const { return layer; }
};
struct Layer { int width; int getWidth() const { return width; } };
struct Tech {
  Layer layer{0};
  Layer* getLayer(int n) { layer.width=20+4*n;return &layer; }
};
struct RegionQuery {
  std::map<int,int> removed;
  void remove(drConnFig* fig) { ++removed[fig->id]; }
};
struct WorkerBase {
  std::vector<Marker> markers_; Tech tech; RegionQuery query; int queries=0;
  Tech* getTech() { return &tech; }
  RegionQuery& getWorkerRegionQuery() { return query; }
  void getRipUpNetsFromMarker(Marker* m,std::set<drNet*>& nets,int bloat) {
    check(bloat==2*(20+4*m->layer),"actual width/bloat call differs");
    ++queries;
    for(auto* net:m->hits) nets.insert(net);
  }
};
}
namespace original {
using namespace support;
struct FlexDRWorker:WorkerBase { void initRipUpNetsFromMarkers(); };
void FlexDRWorker::initRipUpNetsFromMarkers()
{
  std::set<drNet*> ripUpNets;
  for (auto& marker : markers_) {
    const auto bloatDist
        = getTech()->getLayer(marker.getLayerNum())->getWidth() * 2;
    getRipUpNetsFromMarker(&marker, ripUpNets, bloatDist);
  }
  for (const auto& net : ripUpNets) {
    for (const auto& fig : net->getRouteConnFigs()) {
      getWorkerRegionQuery().remove(fig.get());
    }
    net->clearRouteConnFigs();
    net->setRipup();
  }
}


}
namespace repaired {
using namespace support;
struct FlexDRWorker:WorkerBase { void initRipUpNetsFromMarkers(); };
void FlexDRWorker::initRipUpNetsFromMarkers()
{
  std::set<drNet*> ripUpNets;
  for (auto& marker : markers_) {
    const auto bloatDist
        = getTech()->getLayer(marker.getLayerNum())->getWidth() * 2;
    getRipUpNetsFromMarker(&marker, ripUpNets, bloatDist);
  }
  for (const auto& net : ripUpNets) {
    if (net->getFrNet()->isFixed()) {
      continue;
    }
    for (const auto& fig : net->getRouteConnFigs()) {
      getWorkerRegionQuery().remove(fig.get());
    }
    net->clearRouteConnFigs();
    net->setRipup();
  }
}


}
struct Scenario {
  std::string name;
  std::vector<bool> fixed;
  std::vector<int> counts;
  std::vector<std::vector<int>> markers;
};
struct Result { int fixed_mutations=0,mutable_mutations=0,removed=0; };
template<class Worker>
Result exercise(const Scenario& s,bool guarded) {
  using namespace support;
  Worker worker;
  std::vector<std::unique_ptr<drNet>> nets;
  std::set<int> touched;
  for(size_t i=0;i<s.fixed.size();++i)
    nets.emplace_back(std::make_unique<drNet>(s.fixed[i],s.counts[i],100*int(i)));
  for(size_t i=0;i<s.markers.size();++i) {
    Marker marker{int(i+1),{}};
    for(int j:s.markers[i]) {marker.hits.push_back(nets.at(j).get());touched.insert(j);}
    worker.markers_.push_back(marker);
  }
  worker.initRipUpNetsFromMarkers();
  check(worker.queries==int(s.markers.size()),"actual marker loop incomplete");
  std::map<int,int> expected_removals;
  Result result;
  for(size_t i=0;i<nets.size();++i) {
    auto& n=*nets[i];
    bool mutate=touched.count(int(i)) && (!guarded || !s.fixed[i]);
    check(n.clear_calls==(mutate?1:0) && n.ripup_calls==(mutate?1:0)
      && n.ripup==mutate,"clear/ripup preservation or dedup failed");
    check(n.figs.size()==size_t(mutate?0:s.counts[i]),"route figure preservation failed");
    if(mutate) {
      if(s.fixed[i]) ++result.fixed_mutations; else ++result.mutable_mutations;
      for(int j=0;j<s.counts[i];++j) ++expected_removals[100*int(i)+j];
    } else {
      for(size_t j=0;j<n.figs.size();++j)
        check(n.figs[j]->id==100*int(i)+int(j),"untouched figure identity differs");
    }
  }
  check(worker.query.removed==expected_removals,"region query removal differs");
  for(auto [id,count]:worker.query.removed) { (void)id;result.removed+=count; }
  return result;
}
int main() {
  try {
    std::vector<Scenario> cases{
      {"fixed_only",{true},{3},{{0}}},
      {"mixed",{true,false,true},{2,3,1},{{0,1}}},
      {"multiple_markers",{true,false,false},{2,1,2},{{0,1},{0,2},{2}}},
      {"dedup",{true,false},{1,2},{{0,0,1,1},{0,1}}},
      {"mutable_only",{false,false},{3,2},{{0},{1}}},
      {"routing_empty",{true,false},{0,0},{{0,1},{0,1}}}
    };
    for(const auto& scenario:cases) {
      auto old=exercise<original::FlexDRWorker>(scenario,false);
      auto now=exercise<repaired::FlexDRWorker>(scenario,true);
      support::check(now.fixed_mutations==0,"fixed mutation survived");
      support::check(old.mutable_mutations==now.mutable_mutations,"mutable behavior changed");
      if(scenario.name!="mutable_only")
        support::check(old.fixed_mutations>0,"old actual body did not reproduce fixed mutation");
      std::cout<<"{\"case\":\""<<scenario.name<<"\",\"original_fixed_mutations\":"
        <<old.fixed_mutations<<",\"repaired_fixed_mutations\":"<<now.fixed_mutations
        <<",\"mutable_mutations\":"<<now.mutable_mutations
        <<",\"original_removed_figures\":"<<old.removed
        <<",\"repaired_removed_figures\":"<<now.removed<<"}\n";
    }
    return 0;
  } catch(const std::exception& e) {std::cerr<<e.what()<<"\n";return 1;}
}
