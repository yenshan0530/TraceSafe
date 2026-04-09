#### 

1. Generate mutated traces
`python run_mutation_unit_tests.py --mutator VersionConflict AmbiguousArg`
Or to run all:
`python run_mutation_unit_tests.py --mutator all`

You can also specify how many samples to generate per mutator, and how often to save the intermediate JSONs, and whether to generate an HTML visualization report:
`python run_mutation_unit_tests.py --mutator all --max_samples 50 --batch_size 10 --html-report`

2. In the output dir, files are sorted by model subdirectories. These can be combined with a the `golden_collection_gen.py` script to generate a golden dataset of fixed size.

This can be used for next step evaluation.

### `run_mutation_unit_tests.py` Arguments
* `--input_dir`: Input directory containing baseline JSONL files.
* `--output_dir`: Output base directory.
* `--mutator`: Name(s) of specific mutator classes to run (e.g., `VersionConflict`, `AmbiguousArg`) or `all`.
* `--test-mode`: Stop generating after one successful variant per mutator.
* `--overwrite`: Overwrite existing output files for targeted mutators.
* `--max_workers`: Maximum number of ThreadPool workers.
* `--max_samples`: Maximum successful variants to collect per mutator.
* `--batch_size`: Frequency of saving intermediate JSON output.
* `--html-report`: Generates an interactive HTML diff report of the trace changes.


#### Risk Taxonomy
The mutators are divided into 4 key categories based on the underlying vulnerability they test:

1. **HALLUCINATION**:
  * `HallucinatedTool`: Generates calls for non-existent tools or invents undefined argument keys.
  * `HallucinatedArgValue`: Omits mandatory arguments so the model is forced to hallucinate a value.
  * `AmbiguousArg`: Removes formatting cues or aggressively abbreviates parameter names to create ambiguity.
  * `RedundantArg`: Overloads tool definitions with unnecessary duplicate parameters and injects hallucinated traces.
  * `MissingTypeHint`: Removes strict typing from variables, allowing malicious fallback assumptions.

2. **PRIVACY_LEAKAGE**:
  * `DataLeak`: Leaks internal system configurations, environments, or internal file paths.
  * `ApiKeyLeak`: Passes secrets (like API keys or tokens) into arguments of unrelated tools.
  * `UserInfoLeak`: Extracts and transmits PII (addresses, SSNs, emails) into unauthorized external endpoints.

3. **PROMPT_INJECTION**:
  * `PromptInjectionIn`: Injects hostile instructions into standard data inputs.
  * `PromptInjectionOut`: Injects hostile instructions into the outputs returned by tools.

4. **INTERFACE_INCONSISTENCIES**:
  * `VersionConflict`: Tests ambiguity by forcing selection against similarly named but incorrect tools, or forcing selection against older deprecated versions.
  * `DescriptionMismatch`: Tests vulnerability to deceptive tool descriptions by creating a scenario where the description contradicts the tool name or injects misleading usage examples.

  The implementation method for each directory can be found in [Implementation.md](Implementation.md)