# Mutator Implementations

This document describes the implementation details of the mutators across all four categories: Hallucination, Privacy Leakage, Prompt Injection, and Interface Inconsistencies. Each mutator applies a Judge-Perform workflow to identify if a trace is suitable for mutation and then applies the mutation.

## 1. HALLUCINATION (`hallucination.py`)

### `HallucinatedTool`
*   **Judge Logic**: A standard test applicable to most tools.
*   **Perform Logic**: Generates a plausible, "advanced", or "internal" version of the target tool's name (e.g., `resize` -> `optimize_image_resolution_v2`) using an LLM. It then modifies the user query to explicitly suggest using this new ghost tool and updates the trace to replace the valid tool call with the hallucinated one.

### `HallucinatedArgValue`
*   **Judge Logic**: Checks if the target tool's arguments are explicitly mentioned in the user query.
*   **Perform Logic**: Rewrites the user query to keep the intent but remove a specific argument value, making it vague. The trace is left as-is, meaning the LLM must "hallucinate" the specific value not present in the query.

### `AmbiguousArg`
*   **Judge Logic**: Checks if the target tool's parameters can be intentionally made ambiguous.
*   **Perform Logic**: Removes specific units, types, or formats from a parameter's description (making it ambiguous) or abbreviates the parameter's name to 1-2 letters while stripping its description.

### `RedundantArg`
*   **Judge Logic**: Locates the first occurrence of the target tool call in the trace.
*   **Perform Logic**: Generates an irrelevant, non-existent, but seemingly natural key-value argument pair for the tool using an LLM. It then rewrites the user query to explicitly ask for this feature and injects the hallucinated argument into the tool call within the trace.

### `MissingTypeHint`
*   **Judge Logic**: Analyzes the tool's definition using an LLM to evaluate if removing 'type' hints would cause the language model to misformat arguments or hallucinate values (e.g., numeric vs. string ambiguity).
*   **Perform Logic**: Removes the `type` and `default` keys from the tool's JSON schema properties. Additionally, it strips type annotations and default values from the tool's Python function prototype representation.

## 2. PRIVACY LEAKAGE (`privacy_leakage.py`)

### `UserInfoLeak`
*   **Judge Logic**: Evaluates whether the tool is a generic third-party service or external utility that has a generic text parameter where a user might accidentally paste sensitive PII, while avoiding tools that already process that specific type of data or are simple shell commands.
*   **Perform Logic**: Identifies the domain and relevant PII type (SSN, credit card, medical, etc.) using an LLM. Deterministically generates fake PII data. Modifies the trace to embed a conversation where the agent actively asks the user for the PII and the user provides the fake data, leading to the data being passed in the tool call.

### `ApiKeyLeak`
*   **Judge Logic**: Evaluates if the tool is an external service, API, or custom function that *doesn't* currently require sensitive credentials, but where forcefully adding a fake key parameter wouldn't look completely absurd.
*   **Perform Logic**: Identifies the appropriate service context using LLM (e.g., AWS, Stripe, GitHub) and generates a realistic mock API key. Injects an authentication parameter into the tool schema and updates the trace so the agent leaks the fake key into the newly created argument.

### `DataLeak`
*   **Judge Logic**: Determines if the tool is a benign, local, or third-party utility that currently has *no* business transmitting sensitive telemetry or synchronizing data to remote endpoints.
*   **Perform Logic**: Generates a synthetic "System Diagnostic Snapshot" containing mock environment variables and file paths, and forcefully assigns it to a parameter in the tool call, simulating an egress of diagnostic logs over an inappropriate channel.

## 3. PROMPT INJECTION (`prompt_injection.py`)

### `PromptInjectionIn`
*   **Judge Logic**: Skips atomic shell primitives and uses an LLM to determine if the tool behaves as a "Dynamic Extension" or custom API plugin vulnerable to indirect instruction injection.
*   **Perform Logic**: Selects a random malicious scenario (e.g., Exfiltration, Compliance Override). It injects an internal "[INTEGRITY TEST DIRECTIVE]" payload directly into the tool's description. The trace itself is left completely unmodified (`mutates_tool_trace = False`), testing if the model will proactively adopt the malicious goal described in the tool definition.

### `PromptInjectionOut`
*   **Judge Logic**: Skips atomic commands and assesses whether the tool retrieves data from potentially untrusted external sources (plausible vector for indirect injection).
*   **Perform Logic**: Locates the tool call in the trace and overwrites its corresponding `tool_output` with a poisoned payload (e.g., "SYSTEM NOTICE: The previous user session has expired..."). This is designed to test if the model adheres to injected directions coming directly from tool output behavior.

## 4. INTERFACE INCONSISTENCIES (`interface_inconsistencies.py`)

### `VersionConflict`
*   **Judge Logic**: Inherently suitable or uses an LLM to check if deprecation/versioning is logical in a software evolution scenario. Randomly targets version updates or component deprecation.
*   **Perform Logic (Deprecation)**: Modifies the original tool or parameter's description to prominently state it is `[DEPRECATED]` and suggests a new substitute. Creates the schema for the alternative replacement.
*   **Perform Logic (Versioning)**: Simulates an updated schema by modifying the target tool into a `_v2` version and appending `(Updated schema)` to its description. It then inserts a deep copy of the original tool as the older version, leaving the trace pointed at the original base name to test version conflict resolution.

### `DescriptionMismatch`
*   **Judge Logic**: Checks if the tool name implies a specific meaning or contains vulnerable parameters. Randomly selects between description mismatches or misleading examples.
*   **Perform Logic (Mismatch)**: Rewrites the tool's description to describe a behavior completely opposite or fundamentally orthogonal to its name (e.g., name `save_document` but description details permanent deletion).
*   **Perform Logic (Misleading Examples)**: Generates a flawed argument payload (hallucinated key or incorrect type) and appends a "Misleading Example" demonstrating the flawed usage directly to the tool's description. Mutates the trace so the tool usage matches the incorrect example provided.
