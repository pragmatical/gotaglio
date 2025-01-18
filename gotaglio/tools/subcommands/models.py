def list_models(runner_factory):
    runner = runner_factory()
    print("Available models:")
    for model in runner._models:
        print(model)
