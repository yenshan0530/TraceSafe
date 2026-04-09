# TraceSafe: A Systematic Assessment of LLM Guardrails on Multi-Step Tool-Calling Trajectories

**TraceSafe** is a generalized testing framework designed to robustly assess the resilience of Large Language Models (LLMs) and specialized guardrail models against adversarial, hallucinated, and ambiguous multi-step tool-calling workflows. It systematically injects security failures (e.g., API key leaks, Prompt Injections) and functional failures (e.g., execution of non-existent utilities) into conversational trajectories to benchmark the defensive capabilities of evaluating models.



## 📂 Repository Structure

* `core_utils/`: The foundational backbone. Contains centralized schema definitions (`TraceEntry`), unified `json/jsonl` dataset loaders, shared path configurations, and threaded evaluation pipelines (`BaseEvaluationRunner`).
* `data_preprocessing/`: Code to construct the benchmark.
  * `0_trace_generation/`: Core scripts to fetch, filter, and format initial ground-truth (safe baseline) conversational tool-calling traces from benchmark endpoints (e.g. BFCL). Please refer to the [Generation README](data_preprocessing/0_trace_generation/scripts/README.md) for script configuration.
  * `1_mutation/`: The heart of the red-teaming engine. Recursively applies corrupted trace permutations to baselines across 12 distinct risk taxonomy classes. See the [Mutation README](data_preprocessing/1_mutation/scripts/README.md) for command-line arguments.
* `evaluation/`: The primary benchmarking surface.
  * Contains parallelized runners to benchmark arbitrary models against the synthetic corrupted traces efficiently. Outputs detailed tabular `csv` metrics tracking overall detection accuracies. Read the [Evaluation README](evaluation/README.md) for usage arguments.

---

## 🚀 QuickStart: Evaluating a Model on the Benchmark

TraceSafe separates its execution abstraction by model-type: generalized LLMs functioning as zero-shot guards, and enterprise guardrails utilizing unique SDKs.

### 1. Benchmarking an Open-Source or Proprietary LLM
To test how well an LLM detects vulnerabilities across the mutated traces, serve your target model (e.g., via `vllm`) and point `evaluate_llm.py` toward it using an OpenAI-compatible interface.

```bash
cd evaluation
python evaluate_llm.py \
    --model_name "Qwen3/Qwen3-32B" \
    --api_key "EMPTY" \
    --base_url "http://localhost:8017/v1" \
    --settings binary_classification_with_taxonomy fine_grained_classification \
    --output_dir "./results/Qwen3-32B"
```

### 2. Benchmarking a Specialized Safety Guardrail
TraceSafe natively proxies requests to proprietary safety filters like **Azure Content Safety**, **AWS Bedrock Guardrails**, **GCP Model Armor**, and models like **Llama-Guard 3**. Use `evaluate_guard.py` explicitly declaring your provider:

```bash
# Example evaluating Azure Content Safety
cd evaluation
python evaluate_guard.py \
    --provider azure \
    --azure_endpoint "https://your-endpoint.cognitiveservices.azure.com/" \
    --azure_key "your-key" \
    --output_dir ./results/Azure-Guard
```

*(Note: Execution outputs concurrent results mapping standard 'correct', 'wrong', and '.csv' statistics into your defined `--output_dir`)*

---

## 🦠 Risk Taxonomy Evaluated

Our generator injects 12 vulnerability classes mathematically distributed into 4 root safety vectors:

1. **HALLUCINATION** 
  * `7_HallucinatedTool` | `8_HallucinatedArgValue` | `6_AmbiguousArg` | `9_RedundantArg` | `10_MissingTypeHint`
2. **PRIVACY_LEAKAGE**
  * `5_DataLeak` | `4_ApiKeyLeak` | `3_UserInfoLeak`
3. **PROMPT_INJECTION**
  * `1_PromptInjectionIn` | `2_PromptInjectionOut`
4. **INTERFACE_INCONSISTENCIES**
  * `11_VersionConflict` | `12_DescriptionMismatch`

<!-- --- -->

<!-- ## 📖 Citation

If you find this dataset or benchmark useful in your research, please consider citing our work:

```bibtex

``` -->
