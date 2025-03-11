import pytest

from gotaglio.dag import build_dag, run_dag


def test_valid():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should not raise an exception
    build_dag(spec)


def test_duplicate_name():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "A", "function": f, "inputs": ["A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        build_dag(spec)
    assert "Duplicate node name 'A'" in str(e.value)


def test_invalid_input():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["X"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        build_dag(spec)
    assert "Node B: cannot find input 'X'" in str(e.value)


def test_duplicate_input():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["A", "A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        build_dag(spec)
    assert "Node B: duplicate input 'A'" in str(e.value)


def test_no_root():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": ["D"]},
        {"name": "B", "function": f, "inputs": ["A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        build_dag(spec)
    assert "No nodes ready to run" in str(e.value)


def test_has_cycle():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["A", "D"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        build_dag(spec)
    assert "Cycle detected: A -> B -> D -> B" in str(e.value)


def test_unreachable_nodes():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
        {"name": "E", "function": f, "inputs": ["F"]},
        {"name": "F", "function": f, "inputs": ["E"]},
    ]

    # Should raise an exception
    with pytest.raises(ValueError) as e:
        build_dag(spec)
    assert "The following nodes are unreachable: E, F" in str(e.value)

def test_valid():
    async def f(context):
        pass

    spec = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": f, "inputs": ["A"]},
        {"name": "C", "function": f, "inputs": ["A"]},
        {"name": "D", "function": f, "inputs": ["B", "C"]},
    ]

    # Should not raise an exception
    build_dag(spec)
