// SPDX-License-Identifier: BSD-3-Clause
#pragma once
#include <algorithm>
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace drt::nssoc {
// Partition only the worker search region. Original routing guides are untouched.
// Adjacent windows overlap; their closed union is exactly the original rectangle.
// Use int64_t intermediates so coordinates near the DBU integer limits do not wrap.
template <class Rect>
std::vector<Rect> partitionGuideTile(const Rect& original,
                                    int64_t max_x, int64_t max_y,
                                    int64_t overlap_x, int64_t overlap_y)
{
  if (max_x <= 0 || max_y <= 0 || overlap_x < 0 || overlap_y < 0
      || overlap_x >= max_x || overlap_y >= max_y
      || original.xMin() > original.xMax()
      || original.yMin() > original.yMax()) {
    throw std::invalid_argument("invalid guide tile partition bounds");
  }
  std::vector<Rect> result;
  for (int64_t x = original.xMin();;) {
    const int64_t right = std::min(x + max_x, int64_t(original.xMax()));
    for (int64_t y = original.yMin();;) {
      const int64_t top = std::min(y + max_y, int64_t(original.yMax()));
      result.emplace_back(int(x), int(y), int(right), int(top));
      if (top == original.yMax()) {
        break;
      }
      y = top - overlap_y;
    }
    if (right == original.xMax()) {
      break;
    }
    x = right - overlap_x;
  }
  return result;
}
}  // namespace drt::nssoc
