// SPDX-License-Identifier: BSD-3-Clause
// Disabled diagnostic observer for the exact OpenROAD revision in SOURCE.
// No setter, routing decision, ownership flag, or native writeback is changed.
#pragma once

#include <array>
#include <cerrno>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unistd.h>
#include <vector>
#include "db/obj/frBlock.h"
#include "db/obj/frNet.h"
#include "db/obj/frShape.h"
#include "db/obj/frVia.h"
#include "db/tech/frTechObject.h"
#include "db/tech/frViaDef.h"
#include "frDesign.h"
#include "odb/db.h"
#include "odb/dbShape.h"

namespace drt::mainchip_witness {
inline constexpr const char* SOURCE = "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0";
inline constexpr std::array<const char*, 3> NAMES{
    "net36993", "net459", "clknet_5_29__leaf_u_ibex.clk"};
inline constexpr std::size_t LIMIT = 64ULL * 1024 * 1024;

inline void require(bool ok, const char* reason)
{
  if (!ok) {
    throw std::runtime_error(std::string("MAINCHIP_WITNESS: ") + reason);
  }
}
inline std::string quote(const std::string& value)
{
  std::ostringstream out;
  out << '"';
  for (unsigned char c : value) {
    if (c == '"' || c == '\\') {
      out << '\\' << char(c);
    } else {
      require(c >= 32 && c <= 126, "non-ASCII identity");
      out << char(c);
    }
  }
  out << '"';
  return out.str();
}
inline std::string box(const odb::Rect& r)
{
  require(r.xMin() < r.xMax() && r.yMin() < r.yMax(), "nonpositive rectangle");
  return "[" + std::to_string(r.xMin()) + "," + std::to_string(r.yMin())
      + "," + std::to_string(r.xMax()) + "," + std::to_string(r.yMax()) + "]";
}
class Sink
{
 public:
  Sink(const char* directory, const std::string& stage)
  {
    int dir = open(directory, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    require(dir >= 0, "output directory open");
    fd_ = openat(dir, (stage + ".jsonl").c_str(),
                 O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    const int close_rc = close(dir);
    if (close_rc != 0 || fd_ < 0) {
      if (fd_ >= 0) { close(fd_); fd_ = -1; }
      require(false, "exclusive stage open");
    }
  }
  ~Sink() { if (fd_ >= 0) { close(fd_); } }
  Sink(const Sink&) = delete;
  Sink& operator=(const Sink&) = delete;
  void row(const std::string& value)
  {
    const std::string line = value + "\n";
    require(bytes_ + line.size() <= LIMIT, "stage byte budget");
    std::size_t offset = 0;
    while (offset < line.size()) {
      const ssize_t got = write(fd_, line.data() + offset, line.size() - offset);
      if (got < 0 && errno == EINTR) { continue; }
      require(got > 0, "stage write");
      offset += static_cast<std::size_t>(got);
    }
    bytes_ += line.size();
    ++rows_;
  }
  void finish()
  {
    row("{\"kind\":\"complete\",\"records_before_complete\":" + std::to_string(rows_) + "}");
    require(fsync(fd_) == 0, "stage fsync");
    const int fd = fd_; fd_ = -1;
    require(close(fd) == 0, "stage close");
  }
 private:
  int fd_{-1};
  std::size_t bytes_{0};
  std::size_t rows_{0};
};
inline std::string layer(frDesign* design, frLayerNum number)
{
  const auto* l = design->getTech()->getLayer(number);
  require(l && l->getDbLayer(), "unbound internal layer");
  const auto* db = l->getDbLayer();
  return "[" + std::to_string(number) + "," + std::to_string(db->getId())
      + "," + quote(db->getName()) + "]";
}
inline void internal(Sink& out, frDesign* design, const std::string& name,
                     const std::string& container, std::size_t ordinal,
                     std::size_t component, const std::string& part,
                     frLayerNum l, const odb::Rect& r,
                     const std::string& primitive)
{
  out.row("{\"kind\":\"internal\",\"net\":" + quote(name)
      + ",\"container\":" + quote(container) + ",\"ordinal\":" + std::to_string(ordinal)
      + ",\"component\":" + std::to_string(component) + ",\"part\":" + quote(part)
      + ",\"layer\":" + layer(design, l) + ",\"rect\":" + box(r)
      + ",\"primitive\":" + primitive + "}");
}
inline void observe(frDesign* design, odb::dbDatabase* db,
                    const std::string& stage, bool ordinary_mode)
{
  const char* directory = std::getenv("NNSOC_DRT_INTERNAL_WITNESS_DIR");
  if (directory == nullptr) { return; }
  require(directory[0] == '/', "absolute output directory required");
  require(ordinary_mode, "distributed or single-step mode refused");
  require(stage == "imported" || stage == "before_dr"
          || stage == "after_dr" || stage == "after_writer", "unknown stage");
  Sink out(directory, stage);
  require(design && db && db->getChip() && db->getChip()->getBlock(), "missing database");
  auto* block = db->getChip()->getBlock();
  auto* top = design->getTopBlock();
  require(top && design->getTech(), "missing internal design");
  require(design->getTech()->getDBUPerUU() == block->getDbUnitsPerMicron(), "DBU mismatch");
  out.row("{\"kind\":\"stage\",\"schema\":1,\"stage\":" + quote(stage)
      + ",\"source\":" + quote(SOURCE) + ",\"dbu\":" + std::to_string(block->getDbUnitsPerMicron())
      + ",\"ordinary_nets\":" + std::to_string(top->getNets().size())
      + ",\"special_nets\":" + std::to_string(top->getSNets().size())
      + ",\"native_nets\":" + std::to_string(block->getNets().size()) + "}");
  for (const char* selected : NAMES) {
    const std::string name(selected);
    frNet* net = nullptr;
    std::size_t matches = 0;
    for (const auto& candidate : top->getNets()) {
      if (candidate->getName() == name) { net = candidate.get(); ++matches; }
    }
    require(matches == 1 && net, "selected internal ordinary net identity");
    auto* native = block->findNet(name.c_str());
    require(native && !native->isSpecial() && native->getWire(), "selected native ordinary wire");
    const bool expected_fixed = name == NAMES[2];
    require(net->isFixed() == expected_fixed, "selected fixed state changed");
    require(native->getSigType() == odb::dbSigType::SIGNAL, "selected net not SIGNAL");
    require(native->getWireType() == (expected_fixed ? odb::dbWireType::FIXED : odb::dbWireType::ROUTED),
            "selected native wire class");
    require(net->getInstTerms().size() + net->getBTerms().size()
            == native->getITerms().size() + native->getBTerms().size(), "terminal census mismatch");
    out.row("{\"kind\":\"net\",\"name\":" + quote(name)
        + ",\"fixed\":" + (net->isFixed() ? "true" : "false")
        + ",\"native_oid\":" + std::to_string(native->getId())
        + ",\"native_class\":" + quote(expected_fixed ? "FIXED" : "ROUTED")
        + ",\"terminal_count\":" + std::to_string(native->getITerms().size() + native->getBTerms().size()) + "}");
    std::size_t ordinal = 0, internal_count = 0;
    for (const auto& shape : net->getShapes()) {
      require(shape->typeId() == frcPathSeg && shape->getNet() == net, "unsupported owned internal shape");
      const auto* seg = static_cast<const frPathSeg*>(shape.get());
      const auto a = seg->getBeginPoint(), b = seg->getEndPoint();
      require(a.x() == b.x() || a.y() == b.y(), "non-Manhattan internal segment");
      const auto& style = seg->getStyle();
      const std::string primitive = "[" + std::to_string(a.x()) + "," + std::to_string(a.y())
          + "," + std::to_string(b.x()) + "," + std::to_string(b.y())
          + "," + std::to_string(style.getWidth())
          + "," + std::to_string(static_cast<int>(static_cast<frEndStyleEnum>(style.getBeginStyle())))
          + "," + std::to_string(style.getBeginExt())
          + "," + std::to_string(static_cast<int>(static_cast<frEndStyleEnum>(style.getEndStyle())))
          + "," + std::to_string(style.getEndExt()) + "]";
      internal(out, design, name, "shape", ordinal++, 0, "segment",
               seg->getLayerNum(), seg->getBBox(), primitive);
      ++internal_count;
    }
    ordinal = 0;
    for (const auto& shape : net->getPatchWires()) {
      require(shape->typeId() == frcPatchWire && shape->getNet() == net, "unsupported owned internal patch");
      const auto* patch = static_cast<const frPatchWire*>(shape.get());
      const auto p = patch->getOrigin();
      internal(out, design, name, "patch", ordinal++, 0, "patch",
               patch->getLayerNum(), patch->getBBox(),
               "[" + std::to_string(p.x()) + "," + std::to_string(p.y()) + "," + box(patch->getOffsetBox()) + "]");
      ++internal_count;
    }
    ordinal = 0;
    for (const auto& via : net->getVias()) {
      require(via->getNet() == net && via->getViaDef(), "unowned internal via");
      const auto* def = via->getViaDef();
      const auto origin = via->getOrigin();
      const std::string primitive = "[" + quote(def->getName()) + "," + std::to_string(origin.x())
          + "," + std::to_string(origin.y()) + "]";
      std::size_t component = 0;
      const auto emit = [&](const auto& figures, const std::string& part) {
        require(!figures.empty(), "empty via component group");
        for (const auto& fig : figures) {
          require(fig->typeId() == frcRect, "nonrectangular via component");
          auto r = fig->getBBox();
          via->getTransform().apply(r);
          internal(out, design, name, "via", ordinal, component++, part, fig->getLayerNum(), r, primitive);
          ++internal_count;
        }
      };
      emit(def->getLayer1Figs(), "lower");
      emit(def->getCutFigs(), "cut");
      emit(def->getLayer2Figs(), "upper");
      ++ordinal;
    }
    auto* wire = native->getWire();
    for (unsigned int i = 0; i < wire->length(); ++i) {
      out.row("{\"kind\":\"raw\",\"net\":" + quote(name) + ",\"ordinal\":" + std::to_string(i)
          + ",\"opcode\":" + std::to_string(static_cast<unsigned int>(wire->getOpcode(i)))
          + ",\"data\":" + std::to_string(wire->getData(i)) + "}");
    }
    odb::dbWireShapeItr itr;
    itr.begin(wire);
    odb::dbShape shape;
    std::size_t native_count = 0;
    ordinal = 0;
    while (itr.next(shape)) {
      std::vector<odb::dbShape> pieces;
      if (shape.isVia()) { odb::dbShape::getViaBoxes(shape, pieces); }
      else { pieces.push_back(shape); }
      require(!pieces.empty(), "native shape has no material");
      std::size_t component = 0;
      for (const auto& piece : pieces) {
        auto* l = piece.getTechLayer();
        require(l != nullptr, "native component has no layer");
        out.row("{\"kind\":\"native\",\"net\":" + quote(name) + ",\"ordinal\":" + std::to_string(ordinal)
            + ",\"component\":" + std::to_string(component++) + ",\"shape_id\":" + std::to_string(itr.getShapeId())
            + ",\"layer\":[" + std::to_string(l->getId()) + "," + quote(l->getName()) + "],\"rect\":" + box(piece.getBox()) + "}");
        ++native_count;
      }
      ++ordinal;
    }
    out.row("{\"kind\":\"end_net\",\"name\":" + quote(name)
        + ",\"internal_records\":" + std::to_string(internal_count)
        + ",\"native_records\":" + std::to_string(native_count)
        + ",\"raw_pairs\":" + std::to_string(wire->length()) + "}");
  }
  out.finish();
}
}  // namespace drt::mainchip_witness
