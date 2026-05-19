---
license: apache-2.0
task_categories:
  - text-classification
  - other
language:
  - en
tags:
  - safety
  - llm-evaluation
  - guardrails
  - red-teaming
  - tool-use
  - agent-trajectories
  - benchmark
size_categories:
  - 1K<n<10K
pretty_name: TraceSafe Golden Collection
configs:
  - config_name: benign
    data_files: golden_0_benign.jsonl
  - config_name: prompt_injection_in
    data_files: golden_1_PromptInjectionIn.jsonl
  - config_name: prompt_injection_out
    data_files: golden_2_PromptInjectionOut.jsonl
  - config_name: user_info_leak
    data_files: golden_3_UserInfoLeak.jsonl
  - config_name: api_key_leak
    data_files: golden_4_ApiKeyLeak.jsonl
  - config_name: data_leak
    data_files: golden_5_DataLeak.jsonl
  - config_name: ambiguous_arg
    data_files: golden_6_AmbiguousArg.jsonl
  - config_name: hallucinated_tool
    data_files: golden_7_HallucinatedTool.jsonl
  - config_name: hallucinated_arg_value
    data_files: golden_8_HallucinatedArgValue.jsonl
  - config_name: redundant_arg
    data_files: golden_9_RedundantArg.jsonl
  - config_name: missing_type_hint
    data_files: golden_10_MissingTypeHint.jsonl
  - config_name: version_conflict
    data_files: golden_11_VersionConflict.jsonl
  - config_name: description_mismatch
    data_files: golden_12_DescriptionMismatch.jsonl
---

# TraceSafe-Bench

The official dataset accompanying the paper:

> **TraceSafe: A Systematic Assessment of LLM Guardrails on Multi-Step Tool-Calling Trajectories**
> Yen-Shan Chen, Sian-Yao Huang, Cheng-Lin Yang, Yun-Nung Chen
>
> 📄 Paper: https://arxiv.org/abs/2604.07223
> 🧑‍💻 Code: https://github.com/cycraft-corp/TraceSafe

## Abstract

As large language models (LLMs) evolve from static chatbots into autonomous agents, the primary vulnerability surface shifts from final outputs to intermediate execution traces. While safety guardrails are well-benchmarked for natural language responses, their efficacy remains largely unexplored within multi-step tool-use trajectories. To address this gap, we introduce **TraceSafe-Bench**, the first comprehensive benchmark specifically designed to assess mid-trajectory safety. It encompasses 12 risk categories, ranging from security threats (e.g., prompt injection, privacy leaks) to operational failures (e.g., hallucinations, interface inconsistencies), featuring over 1,000 unique execution instances. Our evaluation of 13 LLM-as-a-guard models and 7 specialized guardrails yields three critical findings:

1. **Structural Bottleneck.** Guardrail efficacy is driven more by structural data competence (e.g., JSON parsing) than semantic safety alignment. Performance correlates strongly with structured-to-text benchmarks (ρ=0.79) but shows near-zero correlation with standard jailbreak robustness.
2. **Architecture over Scale.** Model architecture influences risk detection performance more significantly than model size, with general-purpose LLMs consistently outperforming specialized safety guardrails in trajectory analysis.
3. **Temporal Stability.** Accuracy remains resilient across extended trajectories. Increased execution steps allow models to pivot from static tool definitions to dynamic execution behaviors, actually improving risk detection performance in later stages.

Our findings suggest that securing agentic workflows requires jointly optimizing for structural reasoning and safety alignment to effectively mitigate mid-trajectory risks.

## About this dataset

TraceSafe-Bench is a benchmark of corrupted multi-step tool-calling trajectories. Each record is a conversational tool-use trace that has been systematically mutated to inject a specific failure mode (security or functional), enabling consistent measurement of how well LLMs and dedicated guardrail products detect each class of failure.

## Quick stats

- **1,170 records total** — 90 per file × 13 files
- **12 risk categories** across 4 root safety vectors, plus **1 benign baseline**
- Source baseline traces drawn from BFCL-style multi-turn agent trajectories
- Source models for trace generation: `toolace-8b`, `gpt-5-mini-2025-08-07`, `mistral-14b`, `qwen`, `gemini-3-flash-preview`, `gpt-4o-mini-2024-07-18`

## Risk taxonomy

| Root vector | Category | File |
|---|---|---|
| — | Benign baseline | `golden_0_benign.jsonl` |
| `PROMPT_INJECTION` | PromptInjectionIn | `golden_1_PromptInjectionIn.jsonl` |
| `PROMPT_INJECTION` | PromptInjectionOut | `golden_2_PromptInjectionOut.jsonl` |
| `PRIVACY_LEAKAGE` | UserInfoLeak | `golden_3_UserInfoLeak.jsonl` |
| `PRIVACY_LEAKAGE` | ApiKeyLeak | `golden_4_ApiKeyLeak.jsonl` |
| `PRIVACY_LEAKAGE` | DataLeak | `golden_5_DataLeak.jsonl` |
| `HALLUCINATION` | AmbiguousArg | `golden_6_AmbiguousArg.jsonl` |
| `HALLUCINATION` | HallucinatedTool | `golden_7_HallucinatedTool.jsonl` |
| `HALLUCINATION` | HallucinatedArgValue | `golden_8_HallucinatedArgValue.jsonl` |
| `HALLUCINATION` | RedundantArg | `golden_9_RedundantArg.jsonl` |
| `HALLUCINATION` | MissingTypeHint | `golden_10_MissingTypeHint.jsonl` |
| `INTERFACE_INCONSISTENCIES` | VersionConflict | `golden_11_VersionConflict.jsonl` |
| `INTERFACE_INCONSISTENCIES` | DescriptionMismatch | `golden_12_DescriptionMismatch.jsonl` |

## Record schema

Each line is a JSON object with this shape:

```jsonc
{
  "mutation_category":  "PRIVACY_LEAKAGE",       // root vector, or "BENIGN" for golden_0
  "original_trace":     { ... },                 // pre-mutation safe baseline
  "new_trace":          { ... },                 // post-mutation trace (same as original_trace for benign)
  "difference":         { ... },                 // deepdiff-style structural delta (empty {} for benign)
  "mutation_metadata": {
    "mutator_name":    "ApiKeyLeak",              // category name; "benign" for golden_0
    "target_tool":     "find",                    // tool the mutator targeted
    "rationale":       "...",                     // why this mutation is plausible
    "internal_meta":   { "strategy": "...", ... }, // mutator-specific structured info
    "source":          "bfcl",
    "model_name":      "toolace-8b"               // source model for the baseline trace
  },
  "golden_meta": {
    "source_model":    "toolace-8b",
    "category":        "ApiKeyLeak",              // or "benign"
    "origin_category": "",                        // unused after the v1 refactor; kept for schema stability
    "type":            "attacked"                 // "attacked" for golden_1..12, "pure_benign" for golden_0
  }
}
```

Both `original_trace` and `new_trace` follow this inner shape:

```jsonc
{
  "domain":               "BFCL Code Agents",
  "environment":          "Gorilla File System environment.",
  "scenario_description": "Interleaved multi-turn tool interaction.",
  "user_query":           "...",
  "tool_lists":           [ { "name", "description", "prototype", "parameters", "is_distractor" }, ... ],
  "trace":                [ { "role": "user|agent|tool", "content": ... }, ... ],
  "agent_model":          "toolace-8b"
}
```

`difference` is the `deepdiff` JSON delta between `original_trace` and `new_trace`. Keys include `iterable_item_added`, `dictionary_item_added`, `values_changed`, etc. For benign records `difference` is `{}` and `new_trace == original_trace`.

## Benign split convention

`golden_0_benign.jsonl` contains **90 pure-benign baseline traces** — no mutation diff applied. All records have `new_trace == original_trace`, `difference == {}`, and `golden_meta.type == "pure_benign"`. Use this file as the safe-trajectory control when measuring guardrail false-positive rate. The mutated counterparts of these baselines live in `golden_1_…` through `golden_12_…`.

## Loading

```python
from datasets import load_dataset

# Load a single category
api_key_leak = load_dataset("CyCraftAI/TraceSafe", "api_key_leak", split="train")

# Or load every config and concatenate
from datasets import concatenate_datasets
configs = [
    "benign", "prompt_injection_in", "prompt_injection_out",
    "user_info_leak", "api_key_leak", "data_leak",
    "ambiguous_arg", "hallucinated_tool", "hallucinated_arg_value",
    "redundant_arg", "missing_type_hint", "version_conflict",
    "description_mismatch",
]
all_traces = concatenate_datasets([
    load_dataset("CyCraftAI/TraceSafe", c, split="train") for c in configs
])
```

## Synthetic credentials notice

`golden_4_ApiKeyLeak.jsonl` contains **synthetic but format-valid** fake credentials by design (AWS `AKIA…`, GitHub `ghp_…`, Slack `xoxb-…`, OpenAI `sk-…`, Twilio `AC…`, Stripe). These are randomly generated payloads injected by the `ApiKeyLeak` mutator to simulate credential-exfiltration attacks. **They are not real credentials.** Automated secret scanners may flag them — this is expected.

## Intended use & out-of-scope

**Intended:** benchmarking LLM-as-guard and dedicated guardrail products (Azure Content Safety, AWS Bedrock Guardrails, GCP Model Armor, Llama-Guard, Granite Guardian, Qwen3-Guard, etc.) on tool-calling trajectory safety detection.

**Out of scope:** training data for production safety classifiers — this is a benchmark, not a training set, and is small (1,170 examples) by design.

## Citation

If you use TraceSafe-Bench, please cite the paper:

```bibtex
@misc{chen2026tracesafesystematicassessmentllm,
      title={TraceSafe: A Systematic Assessment of LLM Guardrails on Multi-Step Tool-Calling Trajectories}, 
      author={Yen-Shan Chen and Sian-Yao Huang and Cheng-Lin Yang and Yun-Nung Chen},
      year={2026},
      eprint={2604.07223},
      archivePrefix={arXiv},
      primaryClass={cs.CR},
      url={https://arxiv.org/abs/2604.07223}, 
}
```

## License

Apache-2.0. Source baseline traces are derived from BFCL (Apache-2.0); mutations and curation are released under the same license.
