#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include "engine.hpp"

namespace py = pybind11;

using pyvesper::Engine;
using pyvesper::FusionAlgorithm;
using pyvesper::PyHybridQuery;
using pyvesper::PyHybridResult;
using pyvesper::PyHybridSearchConfig;
using pyvesper::QueryStrategy;

namespace {

static std::vector<float> to_float_vector_from_numpy(const py::array &arr) {
  // forcecast ensures dtype is converted to float32 if possible
  auto a = arr.cast<py::array_t<float, py::array::c_style | py::array::forcecast>>();
  auto buf = a.request();
  if (buf.ndim != 1) {
    throw py::value_error("embedding must be 1D float32 array");
  }
  auto *ptr = static_cast<float *>(buf.ptr);
  return std::vector<float>(ptr, ptr + buf.shape[0]);
}

static std::vector<float> to_float_vector(py::handle obj) {
  if (obj.is_none()) {
    return {};
  }
  if (py::isinstance<py::array>(obj)) {
    return to_float_vector_from_numpy(obj.cast<py::array>());
  }
  // fallback: list[float]
  return obj.cast<std::vector<float>>();
}

static std::optional<std::string> as_optional_str(py::handle obj) {
  if (obj.is_none()) return std::nullopt;
  return obj.cast<std::string>();
}

static std::optional<std::unordered_map<std::string, std::string>> as_optional_kv(py::handle obj) {
  if (obj.is_none()) return std::nullopt;
  return obj.cast<std::unordered_map<std::string, std::string>>();
}

} // namespace

PYBIND11_MODULE(pyvesper, m) {
  m.doc() = "pyvesper bindings: Vesper hybrid search and context engine integration";

  // Enums
  py::enum_<QueryStrategy>(m, "QueryStrategy", "Query planning strategy controlling dense/sparse execution order.")
      .value("AUTO", QueryStrategy::AUTO)
      .value("DENSE_FIRST", QueryStrategy::DENSE_FIRST)
      .value("SPARSE_FIRST", QueryStrategy::SPARSE_FIRST)
      .value("PARALLEL", QueryStrategy::PARALLEL);

  py::enum_<FusionAlgorithm>(m, "FusionAlgorithm", "Score fusion algorithm for combining dense and sparse results.")
      .value("RECIPROCAL_RANK", FusionAlgorithm::RECIPROCAL_RANK)
      .value("WEIGHTED_SUM", FusionAlgorithm::WEIGHTED_SUM)
      .value("MAX_SCORE", FusionAlgorithm::MAX_SCORE)
      .value("LATE_INTERACTION", FusionAlgorithm::LATE_INTERACTION);

  // Config and Result types
  py::class_<PyHybridSearchConfig>(m, "HybridSearchConfig", "Configuration for hybrid search (k, strategy, fusion, weights, rerank).")
      .def(py::init<>())
      .def_readwrite("k", &PyHybridSearchConfig::k)
      .def_readwrite("query_strategy", &PyHybridSearchConfig::query_strategy)
      .def_readwrite("fusion_algorithm", &PyHybridSearchConfig::fusion_algorithm)
      .def_readwrite("rrf_k", &PyHybridSearchConfig::rrf_k)
      .def_readwrite("dense_weight", &PyHybridSearchConfig::dense_weight)
      .def_readwrite("sparse_weight", &PyHybridSearchConfig::sparse_weight)
      .def_readwrite("rerank_factor", &PyHybridSearchConfig::rerank_factor);

  py::class_<PyHybridResult>(m, "HybridResult", "Result row containing per-path scores and fused ranking metadata.")
      .def(py::init<>())
      .def_readwrite("doc_id", &PyHybridResult::doc_id)
      .def_readwrite("dense_score", &PyHybridResult::dense_score)
      .def_readwrite("sparse_score", &PyHybridResult::sparse_score)
      .def_readwrite("fused_score", &PyHybridResult::fused_score)
      .def_readwrite("dense_rank", &PyHybridResult::dense_rank)
      .def_readwrite("sparse_rank", &PyHybridResult::sparse_rank);

  // Optional: expose PyHybridQuery for completeness (list-based embedding usage)
  py::class_<PyHybridQuery>(m, "HybridQuery", "Query object: natural-language text, optional dense embedding, optional filters.")
      .def(py::init<>())
      .def_readwrite("text", &PyHybridQuery::text)
      .def_readwrite("dense_embedding", &PyHybridQuery::dense_embedding)
      .def_readwrite("filter_json", &PyHybridQuery::filter_json)
      .def_readwrite("filter_kv", &PyHybridQuery::filter_kv);

  // Engine class
  py::class_<Engine>(m, "Engine", "Vesper Engine wrapper exposing deterministic hybrid search and upserts.")
      .def(py::init<>())
      .def("initialize",
           [](Engine &self, const std::unordered_map<std::string, std::string> &cfg) {
             self.initialize(cfg);
           },
           "Initialize engine from key/value config. Set config['deterministic'] = 'true' to force deterministic mode.",
           py::arg("config"))
      .def("open_collection",
           [](Engine &self, const std::string &name, py::object schema_json) {
             std::optional<std::string> schema;
             if (!schema_json.is_none()) schema = schema_json.cast<std::string>();
             self.open_collection(name, schema);
           },
           "Open or create a collection by name. Optional schema_json is a JSON string describing metadata schema.",
           py::arg("name"), py::arg("schema_json") = py::none())
      .def("upsert",
           [](Engine &self,
              const std::vector<std::uint64_t> &ids,
              py::sequence vectors,
              const std::vector<std::unordered_map<std::string, std::string>> &metadata) {
             if (ids.size() != static_cast<std::size_t>(vectors.size()) || ids.size() != metadata.size()) {
               throw py::value_error("ids, vectors, metadata must have the same length");
             }
             std::vector<std::vector<float>> vectors_converted;
             vectors_converted.reserve(ids.size());
             for (py::handle item : vectors) {
               vectors_converted.push_back(to_float_vector(item));
             }
             self.upsert(ids, vectors_converted, metadata);
           },
           "Upsert documents by id with vectors (list[list[float]] or 1D numpy arrays) and metadata (list[dict]).",
           py::arg("ids"), py::arg("vectors"), py::arg("metadata"))
      .def("set_deterministic", &Engine::set_deterministic,
           "Toggle deterministic mode for planner and randomized components.",
           py::arg("deterministic"))
      .def("get_deterministic", &Engine::get_deterministic,
           "Return current deterministic mode state.")
      // numpy-friendly search_hybrid wrapper
      .def("search_hybrid",
           [](const Engine &self,
              const std::string &text,
              py::object embedding,
              py::object filter, // str or dict or None
              const PyHybridSearchConfig &cfg) {
             PyHybridQuery q;
             q.text = text;
             q.dense_embedding = to_float_vector(embedding);
             if (!filter.is_none()) {
               if (py::isinstance<py::dict>(filter)) {
                 q.filter_kv = as_optional_kv(filter);
               } else if (py::isinstance<py::str>(filter)) {
                 q.filter_json = as_optional_str(filter);
               } else {
                 throw py::value_error("filter must be dict, str, or None");
               }
             }
             return self.search_hybrid(q, cfg);
           },
           "Execute hybrid search.\n\nArgs:\n  text: query text (optional if embedding provided).\n  embedding: 1D numpy float32 array or list[float].\n  filter: dict[str,str] or JSON string for metadata filtering (optional).\n  config: HybridSearchConfig.\n\nReturns: List[HybridResult]. Deterministic for fixed inputs when deterministic mode is enabled.",
           py::arg("text") = std::string{},
           py::arg("embedding") = py::none(),
           py::arg("filter") = py::none(),
           py::arg("config"));
}
