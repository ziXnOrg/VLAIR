import pyvesper

def test_engine_construction() -> None:
    e = pyvesper.Engine()
    assert e is not None
    print("Engine construction test passed.")

if __name__ == "__main__":
    test_engine_construction()


