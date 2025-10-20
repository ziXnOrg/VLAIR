import pytest

from orchestrator.context.models import (
  validate_metadata,
  CodeDocument,
  TextDocument,
  TestResultDocument,
)
from orchestrator.context.idempotency import make_idempotency_key


def test_validate_metadata_success():
  validate_metadata({"origin": "agent", "version": 2}, required={"origin": str}, optional={"version": int})


def test_validate_metadata_missing():
  with pytest.raises(ValueError):
    validate_metadata({}, required={"origin": str})


def test_code_document_creation():
  doc = CodeDocument(id=1, path="src/a.cpp", language="cpp", content="int a=0;", metadata={"origin": "agent", "version": 1})
  assert doc.to_dict()["path"] == "src/a.cpp"


def test_text_document_creation():
  doc = TextDocument(id=2, title="Note", content="hello", metadata={"origin": "user", "tags": {"k":"v"}})
  assert doc.metadata["origin"] == "user"


def test_testresult_document_creation():
  doc = TestResultDocument(id=3, test_name="t::a", status="pass", log=None, metadata={"origin": "runner", "run_id": "r1"})
  assert doc.status == "pass"


def test_make_idempotency_key_stable():
  k1 = make_idempotency_key("merge", {"a": 1, "b": {"x": 2}})
  k2 = make_idempotency_key("merge", {"b": {"x": 2}, "a": 1})
  assert k1 == k2


