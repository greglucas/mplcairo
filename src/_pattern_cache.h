#pragma once

#include <functional>
#include <unordered_map>
#include <cairo/cairo.h>

#include <pybind11/pybind11.h>
#include <pybind11/eval.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include "_util.h"

namespace mpl_cairo {

namespace py = pybind11;

using dash_t = std::tuple<double, std::string>;  // Hack to use std::hash<std::string>.

dash_t convert_dash(cairo_t* cr);
dash_t convert_dash(
    std::tuple<std::optional<double>, std::optional<py::object>> dash_spec);
void set_dashes(cairo_t* cr, dash_t dash);

class PatternCache {
  struct CacheKey {
    py::object path;
    cairo_matrix_t matrix;
    void (*draw_func)(cairo_t*);
    double linewidth;
    dash_t dash;
  };
  struct Hash {
    size_t operator()(py::object const& path) const;
    size_t operator()(CacheKey const& key) const;
  };
  struct EqualTo {
    bool operator()(CacheKey const& lhs, CacheKey const& rhs) const;
  };

  struct PatternEntry {
    // Bounds of the transformed path.
    double x, y, width, height;
    std::unique_ptr<cairo_pattern_t*[]> patterns;
  };

  double threshold_;
  size_t n_subpix_;
  // Bounds of the non-transformed path.
  std::unordered_map<py::object, cairo_rectangle_t, Hash> bboxes_;
  // Bounds of the transformed path, and patterns.
  std::unordered_map<CacheKey, PatternEntry, Hash, EqualTo> patterns_;

  public:
  PatternCache(double threshold);
  ~PatternCache();
  void mask(cairo_t* cr, CacheKey key, double x, double y);
};

}
