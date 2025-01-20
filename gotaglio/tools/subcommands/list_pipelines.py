def list_pipelines(runner_factory):
    runner = runner_factory()
    print("Available pipelines:")
    for k, v in runner._pipelines.items():
        print(f"  {k}: {v._description}")
