import asyncio
import json


def build_dag(spec):
    # Create basic DAG with input links.
    if len(spec) == 0:
        raise ValueError("Empty graph specication")
    dag = {}
    have_a_start = False
    for node in spec:
        if node["name"] in dag:
            raise ValueError(f"Duplicate node name '{node['name']}'")
        dag[node["name"]] = {
            "function": node["function"],
            "inputs": node["inputs"],
            "waiting_for": set(),
            "outputs": [],
            "visited": False,
            "live": False,
        }
        if not node["inputs"]:
            have_a_start = True

    if not have_a_start:
        raise ValueError(
            "No nodes ready to run. At least one node must have no inputs."
        )

    # Add output links and waiting_for set.
    for k, dest in dag.items():
        for input in dest["inputs"]:
            if input in dest["waiting_for"]:
                raise ValueError(f"Node {k}: duplicate input '{input}'")
            if input not in dag:
                raise ValueError(f"Node {k}: cannot find input '{input}'")
            dest["waiting_for"].add(input)
            src = dag[input]
            src["outputs"].append(k)

    # TODO: check for cycles
    # TODO: check for unreachable nodes

    return dag


async def run_task(dag, name, context):
    x = await dag[name]["function"](context)
    return (name, x)


def make_task(dag, name, context):
    return asyncio.create_task(run_task(dag, name, context))


async def run_dag(dag, context):
    ready = [k for k, v in dag.items() if not v["waiting_for"]]
    waiting = set([k for k, v in dag.items() if v["waiting_for"]])

    if len(ready) == 0:
        raise ValueError(
            "Internal error: no nodes ready to run. At least one node must have no inputs."
        )

    # Create a list of tasks for the ready nodes
    tasks = [make_task(dag, name, context) for name in ready]

    while tasks:
        # Wait for any of the tasks to complete
        done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        # tasks = list(pending)

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
                dag[output]["waiting_for"].remove(name)
                if not dag[output]["waiting_for"]:
                    waiting.remove(output)
                    tasks.add(make_task(dag, output, context))

    if waiting:
        raise ValueError("Internal error: some nodes are still waiting to run")

        #     node = ready[tasks.index(task)]
        #     for output in dag[node]["outputs"]:
        #         dag[output]["waiting_for"].remove(node)
        #         if not dag[output]["waiting_for"]:
        #             ready.append(output)
        #     ready.remove(node)

        # # Update the ready list
        # ready = [k for k, v in dag.items() if not v["waiting_for"] and k not in ready]


from datetime import datetime, timedelta, timezone


async def work(name, time):
    start = datetime.now().timestamp()
    print(f"{start}: Enter {name}")
    await asyncio.sleep(time)
    end = datetime.now().timestamp()
    print(f"{end}: Exit {name}")
    return {
        "name": name,
        "start": start,
        "end": end,
    }


async def a(context):
    return await work("A", 1)


async def b(context):
    return await work("B", 1)


async def c(context):
    return await work("C", 2)


async def d(context):
    return await work("B", 2)


sample = [
    {"name": "A", "function": a, "inputs": []},
    {"name": "B", "function": b, "inputs": ["A"]},
    {"name": "C", "function": c, "inputs": ["A"]},
    {"name": "D", "function": d, "inputs": ["B", "C"]},
]


def format(context, start):
    stages = context["stages"]
    for k, stage in stages.items():
        print(f"{k}: {stage['start']-start:.2f} -> {stage['end']-start:.2f}")


def go():
    dag = build_dag(sample)
    context = {"stages": {}}
    start = datetime.now().timestamp()
    asyncio.run(run_dag(dag, context))
    print(json.dumps(context, indent=2))
    print()
    format(context, start)


if __name__ == "__main__":
    go()
