# TODO

* Top
  * prefix search should only find uuid.json files
  * Compare
    * Mention git sha diffs
    * Mention config diffs
    * --compare flag for run and rerun
    * Compare and Summarize don't need to be in runner.py
    * x Short uuids
    * x Summary row with counts
    * x Keywords column
    * x Enforce same pipeline
    * x Check for identical runs
    * x Summmarize cases in common and those in one run only
    * x Group common cases by type of diff
    * x Totals and percentages at bottom
  * Example.py
    * Need a way to pass configurations to stages. Runner should do this.
    * Model configuration for infer needs to be passed to model constructor
    * is there any way of removing default values from the config?
    * should summarize() and compare() be static class methods?
    * x Some means of getting static name and description from pipeline before constructing
  * Extract command - extract JSON for specific case in specific run
  * Keyword boolean filter expressions
    * Would these filter the cases in the log file?
  * list_models() should show models introduced by pipeline
  * x Rerun command
    * x Wire up concurrancy for run and rerun
    * x Handle `latest` prefix
    * x Function to get logfilename from prefix or throw
    * x Extract cases from log file
    * x Unified pipeline configuration architecture
  * Convert pipeline into pojo with description and key mapping
    * x name
    * x description
    * key mapping
    * Key-value shortcuts, eg prepare.template => template, infer.model.name => model
    * help
  * Extract flakey and perfect for reusable mocks
  * Use rich consistantly
    * Replace print()
    * bias towards tools/subcommands
    * avoid elsewhere
    * is it ok for pipeline summarization and compare to use rich?
  * Guard against command-line key-value configure of bad paths
    * e.g. infer.model=x instead of infer.model.name=x
    * At least show better error message
    * glom.core.PathAccessError: could not access 'name', part 2 of Path('infer', 'model', 'name'), got error: AttributeError("'str' object has no attribute 'name'")
  * x Remove exception handlers not in stages
  * Exception enhancer
    * Add exception trace when there isn't a context? When the exception is unknown?
    * x Adds context and information to raw exceptions (e.g. which pipeline, which case)
    * Integrate `with ExceptionContext` into codebase
    * Reevaluate need for except statements.
    * with log_context() ...
  * x Remove colorama
  * x Remove Echo model
  * pipeline spec
    * pojo object
      * name
      * description
      * configuration
      * stages
      * static
        * summarize
        * compare
        * oneline summarize
  * infer.mock = flakey | perfect | None
  * . Boolean expression parser
    * Test suite
      * Original
      * Words [a-zA-Z_.][a-zA-Z_.-0-9]
  * Logger architecture
    * Console logging
    * File logging
  * describe command
    * pretty prints a case of a run
  * ability to run each case multiple times
  * from concurrent.futures import ThreadPoolExecutor
    * See https://github.com/Textualize/rich/blob/master/examples/downloader.py
  * . progress bar - https://rich.readthedocs.io/en/latest/progress.html
    * Revisit progress bar hide fix in Runner.go()
  * Clean up summary code
  * . summary keywords
  * x add-ids subcommand
    * x -f or --force
  * x Break out subcommands folder
  * x Flat dict merge algorithm
  * x Table layout algorithm
    * x Do ANSI terminal characters contribute to string length?
  * Schema
    * Header - promoted to database row
    * Config/Metadata - json in database
    * Details - json in database
  * Try out
    * gpt4=mini
    * entire suite
  * BUGS
    * x Summary table score border on right side and curor in score column
    * Why is score 10.99899...? Why not 11? Assuming I subtract .002.
      * phi3 model
      * python apps\example.py summarize 575
    * repair is not mult-threaded - reset id
    * repair doesn't seem to work correctly for first case in
      * python apps\example.py run data\small.json simple2 template=data\template.txt model=gpt3.5
      * See trees at end of this file
      * Also shouldn't have to change attribute quantity to 1 if this is the default
  * Summarize and Compare
    * compare configs (e.g. pipeline, template, model)
    * compare results
      * cases in common
      * cases not in common
      * passes in common
      * failures no in common
    * aggregates
    * detailed compare of two runs
    * brief table compare or summary of n runs
    * Fixed width columns
    * summarize and compare should be able to use SHA prefix of `LAST`
    * display tags
    * option to generate csv
  * keywords and tags
    * show them in the summary and compare output to characterize failures
    * query by Boolean expression
  * Models command
    * Display description
  * Pipelines command
    * Display description
  * Documentation
    * What are the key responsibilities of a pipeline?
  * Assess stage
    * x Modify cases
    * x Bring over tree compare
    * x Update summary
    * Determine whether tree diff is working correctly
  * x Multi-turn
    * x Modify template
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
    * clean up unused code
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
  * Links
    * On python modules
      * https://stackoverflow.com/questions/14132789/relative-imports-for-the-billionth-time
      * 


  ~~~
  "extract": {
    "items": [
      {
        "quantity": 1,
        "name": "latte",
        "options": [
          {
            "quantity": 1,
            "name": "half caf"
          },
          {
            "quantity": 1,
            "name": "vanilla syrup",
            "amount": "regular"
          }
        ]
      }
    ]
  },
~~~

~~~
  "query": "a skinny half-caf latte with two pumps of vanilla",
  "expected": {
    "items": [
      {
        "quantity": 1,
        "name": "latte",
        "options": [
          {
            "quantity": 1,
            "name": "half caf"
          },
          {
            "quantity": 1,
            "name": "nonfat milk"
          },
          {
            "quantity": 2,
            "name": "vanilla syrup"
          }
        ]
      }
    ]
  }
~~~

~~~
  "assess": {
    "op": "REPAIR",
    "cost": 4,
    "steps": [
      "0.1:vanilla syrup: change name to `nonfat milk`",
      "0.1:vanilla syrup: remove amount",
      "1.2:vanilla syrup: insert default version",
      "1.2:vanilla syrup: change attribute(quantity) to '2'"
    ]
  }
~~~


## Service

* schemas
    GET returns a list of schemas
    POST creates a new schema and returns its id
* schemas/id
    GET returns the schema description
    DELETE
    Schemas are immutable
    The schema defines the type system for is cases
* schemas/id/cases
    GET returns all cases or those matching query
    POST schemas/id/cases creates a new case and returns its id
* schemas/id/aschemas
    GET returns a list of annotation-schemas
    POST creates a new annotation-schema and returns its id
    The annotation-schema contains templates for the cases and the annotation create/edit form
* schemas/id1/aschems/id2/
    GET returns all annotations or those matching query
    POST creates a new annotation-schema
    PATCH modifies an annotation

## Views

* Table of case join annotation.
    Filtering
    Sorting
    Editing annotation