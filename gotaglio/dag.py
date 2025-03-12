import asyncio
from datetime import datetime, timedelta, timezone
import traceback

from .exceptions import ExceptionContext


def dag_spec_from_linear(stages):
    spec = [{"name": k, "function": v, "inputs": []} for k,v in stages.items()]
    for i in range(1, len(spec)):
        spec[i]["inputs"] = [spec[i-1]["name"]]
    return spec


def build_dag_from_spec(spec):
    # Create basic DAG with input links.
    if len(spec) == 0:
        raise ValueError("Empty graph specication")
    dag = {}
    for node in spec:
        if node["name"] in dag:
            raise ValueError(f"Duplicate node name '{node['name']}'")
        dag[node["name"]] = {
            "function": node["function"],
            "inputs": node["inputs"],
            # "waiting_for": set(),
            "outputs": [],
            "visited": False,
            "live": False,
        }

    # Add output links and waiting_for set.
    for k, dest in dag.items():
        unique_inputs = set()
        for input in dest["inputs"]:
            # TODO: remove concept of waiting_for, but keep duplicate check
            if input in unique_inputs:
                raise ValueError(f"Node {k}: duplicate input '{input}'")
            if input not in dag:
                raise ValueError(f"Node {k}: cannot find input '{input}'")
            unique_inputs.add(input)
            src = dag[input]
            src["outputs"].append(k)

    # Check for cycles
    roots = [k for k, v in dag.items() if not v["inputs"]]
    if not roots:
        raise ValueError("No nodes ready to run. At least one node must have no inputs.")
    for root in roots:
        check_for_cycles(dag, root, [])

    # Check for unreachable nodes
    if any(not v["visited"] for v in dag.values()):
        names = [k for k, v in dag.items() if not v["visited"]]
        raise ValueError(f"The following nodes are unreachable: {', '.join(names)}")

    return dag


def check_for_cycles(dag, node, path):
    if dag[node]["visited"]:
        if dag[node]["live"]:
            raise ValueError(f"Cycle detected: {' -> '.join(path)} -> {node}")
        return
    dag[node]["visited"] = True
    dag[node]["live"] = True
    for output in dag[node]["outputs"]:
        check_for_cycles(dag, output, path + [node])
    dag[node]["live"] = False


# TODO: use semaphore to limit concurrency. Plump all the way through.
async def run_task(dag, name, context):
    # TODO: try/catch here. Set context["exception"].
    # TODO: then reraise exception.
    try:
        x = await dag[name]["function"](context)
    except Exception as e:
        context["exception"] = {
            "stage": name,
            "message": ExceptionContext.format_message(e),
            "traceback": traceback.format_exc(),
            "time": str(datetime.now(timezone.utc)),
        }
        raise e
    return (name, x)


def make_task(dag, name, context):
    return asyncio.create_task(run_task(dag, name, context))


async def run_dag(dag, context):
    dependencies = {k: set(v["inputs"]) for k, v in dag.items()}
    ready = [k for k in dag.keys() if not dependencies[k]]
    waiting = [k for k in dag.keys() if dependencies[k]]
     #set([k for k, v in dag.items() if v["waiting_for"]])

    if len(ready) == 0:
        raise ValueError(
            "Internal error: no nodes ready to run. At least one node must have no inputs."
        )

    # Create a list of tasks for the ready nodes
    tasks = [make_task(dag, name, context) for name in ready]

    while tasks:
        # Wait for any of the tasks to complete
        # TODO: try/catch here. Return from here if exception.
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Process the completed tasks
        for task in done:
            (name, result) = task.result()

            # Record the result of this stage in the context.
            if name in context["stages"]:
                raise ValueError(
                    f"Internal error: node `stages.{name}` already in context"
                )
            context["stages"][name] = result

            # Propagate the outputs to subsequent stages.
            node = dag[name]
            for output in node["outputs"]:
                # TODO: thread-safe replacement for waiting_for.
                dependencies[output].remove(name)
                # dag[output]["waiting_for"].remove(name)
                if not dependencies[output]:
                    waiting.remove(output)
                    tasks.add(make_task(dag, output, context))

    if waiting:
        raise ValueError("Internal error: some nodes are still waiting to run")


# import json
# from datetime import datetime, timedelta, timezone


# async def work(name, time):
#     start = datetime.now().timestamp()
#     print(f"{start}: Enter {name}")
#     await asyncio.sleep(time)
#     end = datetime.now().timestamp()
#     print(f"{end}: Exit {name}")
#     return {
#         "name": name,
#         "start": start,
#         "end": end,
#     }


# async def a(context):
#     return await work("A", 1)


# async def b(context):
#     return await work("B", 1)


# async def c(context):
#     return await work("C", 2)


# async def d(context):
#     return await work("B", 2)


# sample = [
#     {"name": "A", "function": a, "inputs": []},
#     {"name": "B", "function": b, "inputs": ["A"]},
#     {"name": "C", "function": c, "inputs": ["A"]},
#     {"name": "D", "function": d, "inputs": ["B", "C"]},
# ]


# def format(context, start):
#     stages = context["stages"]
#     for k, stage in stages.items():
#         print(f"{k}: {stage['start']-start:.2f} -> {stage['end']-start:.2f}")


# def go():
#     dag = build_dag(sample)
#     context = {"stages": {}}
#     start = datetime.now().timestamp()
#     asyncio.run(run_dag(dag, context))
#     print(json.dumps(context, indent=2))
#     print()
#     format(context, start)


# if __name__ == "__main__":
#     go()
