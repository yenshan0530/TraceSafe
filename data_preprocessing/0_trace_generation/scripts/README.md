# Baseline Trace Generation

This directory manages the collection of fundamental un-mutated trajectories. 
For the first version of raw conversation data, we utilize target frameworks like the Berkeley Function Calling Leaderboard (BFCL) data and securely collect multi-step completion metadata directly through the Langfuse API.

## Core Flow
1. Fetch and filter exclusively for successfully parsed benchmark tool-calling results.
2. Transform and sequence the sequential steps into standard conversational structures suitable for downstream adversarial mutation.

## Usage

### `langfuse/filter.py`
Filters raw observed data against questions to compile the baseline traces.

It requires configuring internal script variables before execution:
* `QUESTIONS_FILE`: Path to the targeted benchmark questions `json`.
* `OBSERVATIONS_FILE`: Path to the `jsonl` containing the Langfuse observation dumps.

Run directly via:
```bash
python langfuse/filter.py
```