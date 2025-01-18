def list_pipelines(runner_factory):
    runner = runner_factory()
    print("Available pipelines:")
    for pipeline in runner._pipelines:
        print(pipeline)
