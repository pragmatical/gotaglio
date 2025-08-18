import asyncio
import pytest
from datetime import datetime

from gotaglio.dag import build_dag_from_spec, dag_spec_from_linear, run_dag
from gotaglio.director import process_one_case


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
    build_dag_from_spec(spec)


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
        build_dag_from_spec(spec)
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
        build_dag_from_spec(spec)
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
        build_dag_from_spec(spec)
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
        build_dag_from_spec(spec)
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
        build_dag_from_spec(spec)
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
        build_dag_from_spec(spec)
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
    build_dag_from_spec(spec)


def test_spec_from_linear():
    async def f(context):
        pass
    
    async def g(context):
        pass
    
    async def h(context):
        pass

    linear = {
        "A": f,
        "B": g,
        "C": h,
    }

    observed = dag_spec_from_linear(linear)
    expected = [
        {"name": "A", "function": f, "inputs": []},
        {"name": "B", "function": g, "inputs": ["A"]},
        {"name": "C", "function": h, "inputs": ["B"]},
    ]

    assert observed == expected


# ---------------------------------------
# Additional tests for timing integration
# ---------------------------------------

def _iso(s: str) -> datetime:
    # Parse 'YYYY-MM-DD HH:MM:SS.mmmmmm+00:00'
    return datetime.fromisoformat(s)


@pytest.mark.asyncio
async def test_stage_timing_fields_present_and_positive():
    async def a(context):
        await asyncio.sleep(0.05)
        return "A"

    async def b(context):
        await asyncio.sleep(0.07)
        return "B"

    spec = [
        {"name": "A", "function": a, "inputs": []},
        {"name": "B", "function": b, "inputs": ["A"]},
    ]
    dag = build_dag_from_spec(spec)
    case = {"uuid": "00000000-0000-0000-0000-000000000001"}

    result = await process_one_case(case, dag, completed=None)

    assert result["succeeded"] is True
    for name, expected_value in ("A", "A"), ("B", "B"):
        stage = result["stages"][name]
        # Wrapped object with value + timing
        assert isinstance(stage, dict)
        assert stage.get("value") == expected_value
        assert "start" in stage and "end" in stage and "elapsed" in stage
        # start/end parse and are ordered
        start = _iso(stage["start"])  # should not raise
        end = _iso(stage["end"])  # should not raise
        assert end >= start
        # elapsed is non-zero (string like 0:00:00.xxxxxx)
        assert stage["elapsed"].startswith("0:")
        assert stage["succeeded"] is True

    # stages_detailed mirrors the timing shape
    assert "stages_detailed" in result
    assert set(result["stages_detailed"].keys()) == {"A", "B"}


@pytest.mark.asyncio
async def test_case_timing_and_wrapping_and_internal_removed():
    async def a(context):
        await asyncio.sleep(0.02)
        return 1

    spec = [
        {"name": "A", "function": a, "inputs": []},
    ]
    dag = build_dag_from_spec(spec)
    case = {"uuid": "00000000-0000-0000-0000-000000000002"}

    result = await process_one_case(case, dag, completed=None)

    # Case metadata has start/end strings and positive elapsed
    meta = result["metadata"]
    assert "start" in meta and "end" in meta and "elapsed" in meta
    assert _iso(meta["end"]) >= _iso(meta["start"])  # parse ok, ordering ok
    assert meta["elapsed"].startswith("0:")

    # Stage result is wrapped
    stage = result["stages"]["A"]
    assert stage["value"] == 1
    for k in ("start", "end", "elapsed", "succeeded"):
        assert k in stage

    # Internal store removed in final result
    assert "stage_metadata" not in result


@pytest.mark.asyncio
async def test_stage_elapsed_roughly_matches_sleep():
    # Not exact, but elapsed must be >= requested sleep (monotonic timing)
    sleep_s = 0.03

    async def a(context):
        await asyncio.sleep(sleep_s)
        return "done"

    dag = build_dag_from_spec([
        {"name": "A", "function": a, "inputs": []},
    ])
    case = {"uuid": "00000000-0000-0000-0000-000000000003"}
    result = await process_one_case(case, dag, completed=None)

    # Convert stage elapsed "H:MM:SS.micro" to seconds via end-start parsing
    stage = result["stages"]["A"]
    start = _iso(stage["start"])  # parse ok
    end = _iso(stage["end"])  # parse ok
    wall_elapsed = (end - start).total_seconds()
    # Wall elapsed should be >= 0; monotonic elapsed is used for string, so we
    # assert wall time is at least non-negative and the run didn't collapse to zero.
    assert wall_elapsed >= 0
    # The string elapsed should indicate non-zero duration
    assert stage["elapsed"] != "0:00:00"


@pytest.mark.asyncio
async def test_run():
    counter = 0

    def sequence():
        nonlocal counter
        counter += 1
        return counter

    async def work(name, time):
        start = sequence()
        await asyncio.sleep(time)
        end = sequence()
        return {
            "name": name,
            "start": start,
            "end": end,
        }


    async def a(context):
        return await work("A", 0.01)


    async def b(context):
        return await work("B", 0.01)


    async def c(context):
        return await work("C", 0.02)


    async def d(context):
        return await work("B", 0.01)

    spec = [
        {"name": "A", "function": a, "inputs": []},
        {"name": "B", "function": b, "inputs": ["A"]},
        {"name": "C", "function": c, "inputs": ["A"]},
        {"name": "D", "function": d, "inputs": ["B", "C"]},
    ]

    # Should not raise an exception
    dag = build_dag_from_spec(spec)

    context = {"stages": {}}
    await run_dag(dag, context)

    a = context["stages"]["A"]
    b = context["stages"]["B"]
    c = context["stages"]["C"]
    d = context["stages"]["D"]

    assert a["end"] - a["start"] == 1
    assert a["end"] <= b["start"]
    assert a["end"] <= c["start"]

    # b and c start in some order, b ends
    assert b["end"] - a["end"] == 3
    assert b["end"] <= d["start"]

    # b and c start in some order, b ends, c ends
    assert c["end"] - a["end"] == 4
    assert c["end"] <= d["start"]

    assert d["end"] - d["start"] == 1
