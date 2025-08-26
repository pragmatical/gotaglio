# Samples: Azure Realtime

This folder contains a minimal sample showing how to call the Azure OpenAI Realtime model from a gotaglio stage/pipeline.

- Place a short WAV file at `samples/realtime/hello.wav`
- Add a model entry `azure-realtime` to your models config (see `documentation/realtime.md`)
- Create a pipeline that includes a stage similar to `realtime_stage` in the docs
- Use the YAML cases file at `samples/realtime/data/cases.yaml` (uses `{audio_file}` placeholder).

Run:

```bash
gotag run realtime \
  samples/realtime/data/cases.yaml \
  infer.model.name=azure-realtime \
  realtime.audio_file=samples/realtime/hello.wav
```
