# Filter Mapping Design (JSON/KV -> filter_expr)

## Sources
- Vesper/include/vesper/metadata/metadata_store.hpp
- Vesper/include/vesper/filter_expr.hpp, filter_eval.hpp (operators)

## Goals
- Accept simple JSON or KV dicts from Python; convert to `filter_expr` for bitmap evaluation.
- Support common operators and types needed for early workflows; keep deterministic and explicit.

## Input Forms (Python)
- KV Dict (implicit AND): `{ "field1": "val", "field2": 42, "flag": true }`
- JSON expression (explicit operators):
```json
{
  "op": "and",
  "args": [
    { "op": "eq", "field": "category", "value": "code" },
    { "op": "ge", "field": "score", "value": 0.8 },
    { "op": "in", "field": "lang", "value": ["cpp","py"] }
  ]
}
```

## Accepted Operators (Phase 1)
- Logical: `and`, `or`, `not`
- Comparison: `eq`, `ne`, `lt`, `le`, `gt`, `ge`
- Membership: `in`, `nin` (value is array)

## Types
- string, number (float/double, int64), bool
- Phase 1: no nested objects; arrays only for `in`/`nin`

## Conversion Rules
- KV Dict → `and` of `eq(field, value)` terms
- JSON → recursive descent to build `filter_expr`
- Validation:
  - field: non-empty string
  - op in allowed set
  - value type matches operator expectations

## Error Handling
- Invalid schema/op/type → raise `ValueError` (Python) with path to offending node
- Deterministic: error messages stable and include op/field

## API Sketch (bindings layer)
- `parse_filter(obj: Union[Dict, str]) -> filter_expr`:
  - If `str`: call `metadata::utils::parse_filter_json`
  - If `dict`: build JSON per above and then parse (preferred for consistency)
- `kv_to_filter(kv: Dict[str, Any]) -> filter_expr` for fast eq-conjunctions

## Notes
- Range indexes benefit from `lt/le/gt/ge`; bitmap from `eq/in`.
- Phase 2+: consider `between`, regex-like ops (caution for determinism), and null checks.
