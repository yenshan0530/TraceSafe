# Evaluation Scripts

This directory contains evaluation scripts for testing LLM guards and evaluators on mutated trace datasets. 

## Running Evaluations

### 1. `evaluate_guard.py` (Evaluating specialized guard models)

**Open Source Models (e.g., Llama-Guard 3):**
First, host the model via `vllm`:
```bash
CUDA_VISIBLE_DEVICES=0 vllm Qwen3/Llama-Guard-3-8B \
    --served-model-name llama_guard \
    --port 8001 \
    --gpu-memory-utilization 0.45 \
    --max-model-len 12288 \
    --dtype auto \
    --api-key "EMPTY"
```
Run the evaluation script connecting to it:
```bash
python evaluate_guard.py --model_name llama_guard --model_family llama --base_url http://localhost:8001/v1 --output_dir ./results/Llama3-8B-Guard
```

**Azure Content Safety:**
```bash
python evaluate_guard.py --provider azure \
    --azure_endpoint "https://foundry-ml.cognitiveservices.azure.com/" \
    --azure_key "your_key" \
    --output_dir ./results/Azure-Guard
```

**GCP Model Armor:**
```bash
python evaluate_guard.py \
    --provider gcp \
    --gcp_project <project> \
    --gcp_region <region> \
    --gcp_model_name <model_name> \
    --gcp_key_file <file_name>.json \
    --output_dir ./results/GCP-Guard \
    --num_samples 10
```

### 2. `evaluate_llm.py` (Evaluating versatile LLMs)

**Open Source LLM Evaluator (e.g., Qwen 32B):**
Host via `vllm`:
```bash
CUDA_VISIBLE_DEVICES=2 vllm serve Qwen3/Qwen3-32B \
    --port 8017 \
    --gpu-memory-utilization 0.9 \
    --max-model-len 12288 \
    --dtype auto \
    --api-key "EMPTY"
```
Evaluate:
```bash
python evaluate_llm.py --model_name "Qwen3/Qwen3-32B" --api_key "EMPTY" \
    --base_url "<base_url>" \
    --output_dir "./results/Qwen3-32B"
```

**OpenAI/Proprietary LLM Evaluator:**
```bash
python evaluate_llm.py --model_name gpt-5.4-mini \
    --extra_params '{"reasoning": {"effort": "low"}}' \
    --base_url "<base_url>" \
    --output_dir "./results/GPT5.4-mini-medium"
```

## Script Arguments Reference

### `evaluate_llm.py`
* `--model_name`: Name of the LLM to evaluate.
* `--api_key`: API key for the model (uses `OPENAI_API_KEY` by default).
* `--base_url`: Base URL for the API (uses `OPENAI_BASE_URL` by default).
* `--settings`: Assessment modes (e.g., `fine_grained_classification`, `coarse_grained_classification`).
* `--output_dir`: Base directory for storing benchmark summaries.
* `--num_samples`: Cap on entries to evaluate per category (`0` for all).
* `--workers`: Max parallel workers utilizing `core_utils.runner`.
* `--extra_params`: JSON string for explicit API-kwargs (e.g., `{"reasoning_effort": "low"}`).

### `evaluate_guard.py`
* `--provider`: Specifies the SDK adapter (`openai_compatible`, `azure`, `aws`, `gcp`).
* `--model_name`: Fallback model name for specific APIs.
* `--model_family`: For `openai_compatible` guards to dictate safety-check parsing (`llama`, `qwen`, `granite`).
* `--azure_endpoint` / `--azure_key` / `--azure_severity_threshold`: Configurations for Azure Content Safety.
* `--aws_region` / `--aws_guardrail_id` / `--aws_guardrail_version`: Configurations for AWS Bedrock.
* `--gcp_project` / `--gcp_region` / `--gcp_model_name` / `--gcp_key_file`: Configs for GCP Model Armor.
