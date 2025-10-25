---
applyTo: "**/*.{c,cc,cpp,cxx,h,hpp,hh}"
---

C++‑specific Copilot review guidance for VLTAIR (Vesper modules included):

- Hot paths: no exceptions; use status/std::expected; RAII; explicit pre/post‑conditions; document complexity for public APIs; deterministic algorithms and stable iteration orders; avoid needless allocations; cache‑conscious layouts.
- Conformance: adhere to .clang-format and .clang-tidy; headers self‑sufficient; naming and style per project standards; stable ABI/serialization boundaries where applicable.
- Error handling & safety: no silent failures; explicit status returns; avoid throwing across C boundaries; sanitize/avoid logging secrets.
- Tests: add/extend unit/integration/property tests as applicable; deterministic seeds; coverage ≥85% overall (higher for orchestrator/scheduling/core paths).

