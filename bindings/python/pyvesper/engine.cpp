#include "engine.hpp"

#include <algorithm>
#include <stdexcept>

namespace pyvesper {

Engine::Engine() = default;
Engine::~Engine() = default;

static bool as_bool(const std::unordered_map<std::string, std::string>& cfg,
                    const std::string& key,
                    bool fallback) {
  auto it = cfg.find(key);
  if (it == cfg.end()) return fallback;
  const auto& v = it->second;
  if (v.size() == 1 && (v[0] == '1' || v[0] == '0')) return v[0] == '1';
  std::string s;
  s.resize(v.size());
  std::transform(v.begin(), v.end(), s.begin(), [](unsigned char c){ return static_cast<char>(std::tolower(c)); });
  if (s == "true") return true;
  if (s == "false") return false;
  return fallback;
}

static std::uint32_t as_uint32(const std::unordered_map<std::string, std::string>& cfg,
                               const std::string& key,
                               std::uint32_t fallback) {
  auto it = cfg.find(key);
  if (it == cfg.end()) return fallback;
  try {
    return static_cast<std::uint32_t>(std::stoul(it->second));
  } catch (...) {
    return fallback;
  }
}

void Engine::initialize(const std::unordered_map<std::string, std::string>& config) {
  deterministic_ = as_bool(config, "deterministic", true);
  planner_adaptive_disabled_ = as_bool(config, "planner_adaptive_disabled", true);
  default_k_ = as_uint32(config, "default_k", 10u);
  apply_determinism_settings();
}

void Engine::open_collection(const std::string& /*name*/, const std::optional<std::string>& /*schema_json*/) {
  // Placeholder: wiring to IndexManager/MetadataStore to be added in later tasks
}

void Engine::upsert(const std::vector<std::uint64_t>& /*ids*/, const std::vector<std::vector<float>>& /*vectors*/, const std::vector<std::unordered_map<std::string, std::string>>& /*metadata*/) {
  // Placeholder: will route to IndexManager and MetadataStore in later tasks
}

std::vector<PyHybridResult> Engine::search_hybrid(const PyHybridQuery& /*query*/, const PyHybridSearchConfig& /*cfg*/) const {
  // Placeholder: will invoke HybridSearcher with converted config/query; return empty for skeleton
  return {};
}

void Engine::apply_determinism_settings() const {
  // Placeholder: disable adaptive planner/history when deterministic_ is true
}

} // namespace pyvesper
