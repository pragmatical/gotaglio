# TODO

* Top
  * add-ids subcommand
  * Documentation
    * What are the key responsibilities of a pipeline?
  * Assess stage
    * Modify cases
    * Bring over tree compare
    * Update summary
  * Multi-turn
    * Modify template
  * Architecture
    * How does summarize if pipeline used is no longer available?
    * pipeline registration chicken+egg - name not available when factory registered
    * runner.summarize() should return string
  * Tactical
    * May not always need jinja2 template
    * verify poetry on clean venv
    * x rename run.py to runner.py
    * x gotag.bat conflicts with gotag.py
    * figure out where gotag.py belongs
    * summarize and compare should be able to use SHA prefix of `LAST`
    * clean up unused code
  * Exception enhancer
    * Adds context and information to raw exceptions (e.g. which pipeline, which case)
  * Logger architecture
    * Console logging
    * File logging
  * Models command
    * Display description
  * Pipelines command
    * Display description
  * Rerun command
    * Unified pipeline configuration architecture
  * Sample pipeline
    * data folder with cases
    * x pipeline code in separate folder with imports
  * README.md
    * Overview
    * Build instructions
    * Run examples
  * x Create github repo
  * x Refactor for example/gotaglio split
    * x Move load_template() from pipeline.py to templating.py
    * x Move SimplePipeline from pipelines.py to apps/example.py
    * x Pass pipelines dict to main() and Runner constructor.
    * x Convert main() to a class. Make constructor take models and pipelines. Create runner.
    * x Retarget gotag.bat, gotag.sh to apps/example
    * x Remove old gotag.py
