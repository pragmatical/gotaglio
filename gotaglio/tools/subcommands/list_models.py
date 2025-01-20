def list_models(runner_factory):
    runner = runner_factory()
    print("Available models:")
    for k, v in runner._models.items():
        print(f"  {k}: {v.metadata()["description"]}")
