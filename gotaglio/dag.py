
async def a(context):
  print("Enter A")

async def b(context):
  print("Enter b")

async def c(context):
  print("Enter c")

async def d(context):
  print("Enter d")

sample = [
  {
    "name": "A",
    "function": a,
    "inputs": []
  },
  {
    "name": "B",
    "function": b,
    "inputs": ["a"]
  },
  {
    "name": "C",
    "function": c,
    "inputs": ["a"]
  },
  {
    "name": "D",
    "function": d,
    "inputs": ["b", "c"]
  },
]

def build_dag(spec):
  # Create basic DAG with input links.
  dag = {}
  for node in spec:
    if node["name"] in dag:
      raise ValueError(f"Duplicate node name '{node['name']}'")
    dag[node["name"]] = {
      "function": node["function"],
      "inputs": node["inputs"],
      "waiting_for": set(),
      "outputs": []
    }

  # Add output links and waiting_for set.
  for k,dest in dag.items():
    for input in dest["inputs"]:
      if input in dest["waiting_for"]:
        raise ValueError(f"Node {k}: duplicate input '{input}'")
      if input not in dag:
        raise ValueError(f"Node {k}: cannot find input '{input}'")
      dest["waiting_for"].add(input)
      src = dag[input]
      src.outputs.append(k)

  return dag

async def run_dag(dag):
  ready = [k for k,v in dag.items() if not v["waiting_for"]]
  waiting = set([k for k,v in dag.items() if not v["waiting_for"]])
  
  # waiting = {k:v for k,v in dag.items() if v}