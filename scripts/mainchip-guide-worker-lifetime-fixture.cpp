#include <algorithm>
#include <cassert>
#include <cstddef>
#include <map>
#include <memory>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
namespace utl { constexpr int DRT=1; }
struct Rect { int id; bool operator<(const Rect& r) const { return id<r.id; } };
struct SearchRepairArgs { int cookie=37; };
struct IterationProgress { int total_num_workers=0; };
struct Config { int MAX_THREADS=2; };
struct Logger {
  template<class... T> void report(const char*, T...) {}
  template<class... T> [[noreturn]] void error(int,int,const char*,T...) { throw std::runtime_error("native refusal"); }
};
void omp_set_num_threads(int n) { assert(n==2); }
struct Design { std::vector<int> ended; };
struct FlexDRWorker {
  static int alive,peak,created,destroyed;
  int id=-1; bool processed=false;
  FlexDRWorker(){++alive;++created;peak=std::max(peak,alive);}
  ~FlexDRWorker(){--alive;++destroyed;}
  void setWorkerId(int v){id=v;}
  int getWorkerId()const{return id;}
  int getBestNumMarkers()const{return 0;}
  int getInitNumMarkers()const{return 1;}
  bool end(Design* d){assert(processed);d->ended.push_back(id);return true;}
};
int FlexDRWorker::alive=0;int FlexDRWorker::peak=0;int FlexDRWorker::created=0;int FlexDRWorker::destroyed=0;
struct Harness {
  Logger logger_storage; Logger* logger_=&logger_storage;
  Config config_storage; Config* router_cfg_=&config_storage;
  Design design;
  std::vector<std::set<Rect>> boxes_set;
  std::vector<std::vector<int>> route_boxes_batches;
  SearchRepairArgs args;
  IterationProgress iter_prog;
  Design* getDesign(){return &design;}
  std::unique_ptr<FlexDRWorker> createWorker(int x,int y,const SearchRepairArgs& a,const Rect& r){
    assert(x==0&&y==0&&a.cookie==37&&r.id>=0);
    return std::make_unique<FlexDRWorker>();
  }
  void processWorkersBatch(std::vector<std::unique_ptr<FlexDRWorker>>& batch,IterationProgress&){
    assert(!batch.empty()&&batch.size()<=1);
    for(auto& w:batch){assert(!w->processed);w->processed=true;}
  }
  bool run(){
__ACTUAL_PATCH_BODY__
    return changed;
  }
};
void reset(){assert(FlexDRWorker::alive==0);FlexDRWorker::peak=FlexDRWorker::created=FlexDRWorker::destroyed=0;}
int main(){
  int cases=0;
  for(auto batches:std::vector<std::vector<std::vector<int>>>{{},{{0}},{{0,1}},{{0,1,2}},{{0,1,2,3,4}},{{0,1},{2,3},{4}},{{3,0,1},{4,2}}}){
    reset();Harness h;h.route_boxes_batches=batches;
    std::vector<int> expected;
    for(auto& b:batches)for(int i:b)expected.push_back(i);
    int n=expected.empty()?0:*std::max_element(expected.begin(),expected.end())+1;
    for(int i=0;i<n;i++)h.boxes_set.push_back({Rect{i}});
    assert(h.run()==!expected.empty());
    auto actual=h.design.ended;
    // Single-worker commits must retain every input worker in exact traversal order.
    assert(expected==actual&&int(expected.size())==h.iter_prog.total_num_workers);
    assert(FlexDRWorker::alive==0&&FlexDRWorker::created==int(expected.size())&&FlexDRWorker::created==FlexDRWorker::destroyed);
    assert(FlexDRWorker::peak==(expected.empty()?0:1));++cases;
  }
  for(int count:{0,2}){
    reset();Harness h;h.route_boxes_batches={{0}};h.boxes_set.emplace_back();
    for(int i=0;i<count;i++)h.boxes_set[0].insert(Rect{i});
    bool refused=false;try{h.run();}catch(const std::runtime_error&){refused=true;}
    assert(refused&&FlexDRWorker::alive==0&&h.design.ended.empty());++cases;
  }
  assert(cases==9);
}
