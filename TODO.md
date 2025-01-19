# TODO

* Top
  * describe command
    * pretty prints a case of a run
  * ability to run each case multiple times
  * from concurrent.futures import ThreadPoolExecutor
    * See https://github.com/Textualize/rich/blob/master/examples/downloader.py
  * . progress bar - https://rich.readthedocs.io/en/latest/progress.html
    * Revisit progress bar hide fix in Runner.go()
  * infer.mock = flakey | perfect | None
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
  * Clean up summary code
  * . summary keywords
  * . Boolean expression parser
    * Test suite
      * Original
      * Words [a-zA-Z_.][a-zA-Z_.-0-9]
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
  * Rerun command
    * Unified pipeline configuration architecture
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
  * Exception enhancer
    * Adds context and information to raw exceptions (e.g. which pipeline, which case)
  * Logger architecture
    * Console logging
    * File logging
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
