# Pybind11 Type Mapping Design (Task 3)

## Goals
- Seamless, deterministic conversions between Python and C++ for hybrid search.
- Zero/low-copy for large embeddings via NumPy buffer protocol.
- Clear error propagation to Python exceptions.

## Includes and Modules
- `#include <pybind11/pybind11.h>`
- `#include <pybind11/stl.h>` (std::vector/std::unordered_map)
- `#include <pybind11/numpy.h>` (py::array_t<float>)
- `namespace py = pybind11;`

## Inputs
- Text: `std::string` ⇄ Python `str` (UTF‑8 by default)
- Embeddings: prefer `py::array_t<float>`
  - Validate C‑contiguous, 1‑D, dtype=float32
  - Use `request()` to access pointer without copy; fallback: accept `List[float]` and copy into `std::vector<float>`
- Filters:
  - Accept `dict[str, str|int|float|bool]` (implicit AND) or JSON `str` for explicit operators
  - Convert to JSON (for dict) and call `vesper::metadata::utils::parse_filter_json`; or `kv_to_filter` for fast eq ‑ conjunctions

## Enums
- `QueryStrategy` ⇄ Python `Enum` (AUTO, DENSE_FIRST, SPARSE_FIRST, PARALLEL)
- `FusionAlgorithm` ⇄ Python `Enum` (RECIPROCAL_RANK, WEIGHTED_SUM, MAX_SCORE, LATE_INTERACTION)

## Config and Result Structs
- Bind `PyHybridSearchConfig` and `PyHybridResult` via `py::class_`
  - Expose fields as read/write attributes for Python ergonomic use

## Functions
- `engine_init(config: dict) -> None`
- `open_collection(name: str, schema: Optional[dict]) -> None`
- `upsert(docs: List[dict]) -> None`
  - doc = {"id": int, "vector": (py::array_t<float> or list[float]), "metadata": dict}
- `search_hybrid(query: PyHybridQuery, cfg: PyHybridSearchConfig) -> List[PyHybridResult]`
  - Accept `query.dense_embedding` as `py::array_t<float>` or list; validate and convert

## Error Propagation
- Translate Vesper error/status to Python `RuntimeError`/`ValueError` with stable messages
- Provide context: op, field, operator, and reason when filter parse fails

## Performance Notes
- Use buffer protocol for embeddings to avoid copies
- Avoid heap churn in per‑call scaffolding (reserve vectors)

## Determinism
- Expose a deterministic flag in bindings (later task) to disable adaptive planner history if needed
- Always record config/seed parameters to logs for reproducibility

## Example Snippets
```cpp
// Embedding path (no copy)
auto arr = query_embedding.cast<py::array_t<float, py::array::c_style | py::array::forcecast>>();
auto buf = arr.request();
if (buf.ndim != 1) throw py::value_error("embedding must be 1D float32 array");
auto* ptr = static_cast<float*>(buf.ptr);
std::vector<float> vec(ptr, ptr + buf.shape[0]); // copy-once if API requires vector
```

## Next
- Implement `bindings/python/pyvesper/module.cpp` enums/classes and function signatures (Task 6)
- Implement `engine.cpp` conversion glue (Task 5)
- Finalize `engine.hpp` layout (Task 4) to hold Vesper handles and deterministic flags
