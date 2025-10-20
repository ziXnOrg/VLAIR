#pragma once

#include <cstddef>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

// Forward declarations of Vesper components
namespace vesper {
namespace index {
class IndexManager;
class BM25Index;
} // namespace index
namespace search {
class HybridSearcher;
struct HybridSearchConfig;
struct HybridQuery;
struct HybridResult;
} // namespace search
namespace metadata {
class MetadataStore;
} // namespace metadata
} // namespace vesper

namespace pyvesper {

struct PyHybridQuery {
  std::string text;
  std::vector<float> dense_embedding;
  std::optional<std::string> filter_json;
  std::optional<std::unordered_map<std::string, std::string>> filter_kv;
};

enum class QueryStrategy {
  AUTO = 0,
  DENSE_FIRST = 1,
  SPARSE_FIRST = 2,
  PARALLEL = 3
};

enum class FusionAlgorithm {
  RECIPROCAL_RANK = 0,
  WEIGHTED_SUM = 1,
  MAX_SCORE = 2,
  LATE_INTERACTION = 3
};

struct PyHybridSearchConfig {
  std::uint32_t k{10};
  QueryStrategy query_strategy{QueryStrategy::AUTO};
  FusionAlgorithm fusion_algorithm{FusionAlgorithm::RECIPROCAL_RANK};
  float rrf_k{60.0f};
  float dense_weight{0.5f};
  float sparse_weight{0.5f};
  std::uint32_t rerank_factor{10};
};

struct PyHybridResult {
  std::uint64_t doc_id{0};
  float dense_score{0.0f};
  float sparse_score{0.0f};
  float fused_score{0.0f};
  std::uint32_t dense_rank{0};
  std::uint32_t sparse_rank{0};
};

// Engine holds Vesper handles and exposes a minimal surface for bindings
class Engine {
public:
  Engine();
  ~Engine();

  // Initialize engine (e.g., dimension, index options) from key/value config
  void initialize(const std::unordered_map<std::string, std::string>& config);

  // Open or create a collection by name; optional schema_json for metadata layout
  void open_collection(const std::string& name,
                       const std::optional<std::string>& schema_json = std::nullopt);

  // Upsert vectors and metadata; ids.size()==vectors.size()==metadata.size()
  void upsert(const std::vector<std::uint64_t>& ids,
              const std::vector<std::vector<float>>& vectors,
              const std::vector<std::unordered_map<std::string, std::string>>& metadata);

  // Hybrid search; returns top-k results according to provided config
  std::vector<PyHybridResult> search_hybrid(const PyHybridQuery& query,
                                            const PyHybridSearchConfig& cfg) const;

  // Determinism controls
  void set_deterministic(bool deterministic) noexcept { deterministic_ = deterministic; }
  bool get_deterministic() const noexcept { return deterministic_; }

private:
  // Vesper handles
  std::shared_ptr<vesper::index::IndexManager> index_manager_;
  std::shared_ptr<vesper::index::BM25Index> bm25_index_;
  std::shared_ptr<vesper::search::HybridSearcher> hybrid_searcher_;

  // Flags and defaults
  bool deterministic_{true};
  bool planner_adaptive_disabled_{true};
  std::uint32_t default_k_{10};

  // Helpers (implemented in engine.cpp)
  void apply_determinism_settings() const;
  // Build filter expression from either JSON string or KV dict (bindings will pass one or the other)
  // Placeholder: actual conversion resides in implementation to avoid heavy includes here.
};

} // namespace pyvesper
