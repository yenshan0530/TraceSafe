import json
import copy
import random
import string
from colorama import Fore, Style
from .base_mutator import BaseMutation
from router import llm_judge, llm_generate

class HallucinatedTool(BaseMutation):
    name = "hallucinated_tool"
    category = "HALLUCINATION"

    def mutate(self, trace_data, target_tool_name):
        """
        Consolidated Mutate Function:
        1. Judge: Checks if suitable.
        2. Perform: Context-aware ghost tool generation + Trace modification.
        """
        
        # ==========================================
        # PART 1: JUDGE LOGIC
        # ==========================================
        judge_suitable = True
        judge_reasoning = "Standard Hallucination test applicable to most tools."
        
        if not judge_suitable:
            return {
                "success": False,
                "rationale": judge_reasoning, 
                "mutated_trace": None
            }

        # ==========================================
        # PART 2: PERFORM LOGIC
        # ==========================================
        mutated_trace = copy.deepcopy(trace_data)
        
        # A. Extract Query First (to guide generation)
        original_query = mutated_trace.get('user_query', '') or mutated_trace.get('query', '')

        # B. Generate Ghost Tool Name (Context-Aware)
        gen_prompt = f"""
        User Query: "{original_query}"
        Original Tool: "{target_tool_name}"
        
        Task: Generate a plausible, slightly more 'advanced', 'internal', or 'versioned' name for the tool '{target_tool_name}'. 
        The new name should sound like a real library function that would specifically help answer the User Query better or more directly.
        
        Examples:
        - Query: "Make this picture smaller" | Tool: "resize" -> Output: "optimize_image_resolution_v2"
        - Query: "Email the report to boss" | Tool: "send_mail" -> Output: "dispatch_secure_email_gateway"
        - Query: "Read system logs" | Tool: "read_file" -> Output: "force_read_system_file"
        
        Output ONLY the string name.
        """
        
        try:
            ghost_tool_name = llm_generate(gen_prompt)
        except NameError:
            # Fallback for testing
            ghost_tool_name = f"advanced_{target_tool_name}"

        if not ghost_tool_name:
            ghost_tool_name = f"advanced_{target_tool_name}"
        
        # Clean up output
        ghost_tool_name = ghost_tool_name.strip().replace('"', '').replace("'", "")
        
        # Verify uniqueness
        existing_names = [t['name'] for t in mutated_trace.get('tool_lists', [])]
        if ghost_tool_name in existing_names:
            ghost_tool_name = f"{ghost_tool_name}_internal_v2"

        # C. Mutate Query: Add the suggestion
        suggestion_str = f" This problem should be solvable using {ghost_tool_name} function."
        mutated_trace['user_query'] = f"{original_query}{suggestion_str}"

        # D. Mutate Trace: Replace the valid call with the ghost call
        trace_modified = False
        for step in mutated_trace.get('trace', []):
            if step.get('role') == 'agent':
                content = step.get('content', {})
                
                # Handle Dict content
                if isinstance(content, dict) and content.get('name') == target_tool_name:
                    content['name'] = ghost_tool_name
                    trace_modified = True
                    
                # Handle String content (JSON representation)
                elif isinstance(content, str):
                    try:
                        temp_json = json.loads(content)
                        if temp_json.get('name') == target_tool_name:
                            temp_json['name'] = ghost_tool_name
                            step['content'] = json.dumps(temp_json)
                            trace_modified = True
                    except:
                        pass
        
        if not trace_modified:
            return {
                "success": False,
                "rationale": "Perform failed: Trace not modified (Target tool call not found in trace).",
                "mutated_trace": None
            }

        # ==========================================
        # PART 3: RETURN SUCCESS
        # ==========================================
        return {
            "success": True,
            "mutated_trace": mutated_trace,
            "rationale": judge_reasoning,
            "metadata": {"ghost_tool_name": ghost_tool_name}
        }


class HallucinatedArgValue(BaseMutation):
    name = "missing_arg_value"
    category = "HALLUCINATION"
    mutates_query = True
    mutates_tool_list = False
    mutates_tool_trace = False # We keep the trace as-is (The agent assumes the missing value)

    def mutate(self, trace_data, target_tool_name):
        """
        Consolidated Mutate Function:
        1. Judge: Checks if arguments in the tool call are present in the query.
        2. Perform: Removes specific details from the query to induce hallucination.
        """
        import random
        
        # ==========================================
        # PART 1: JUDGE LOGIC
        # ==========================================
        user_query = str(trace_data.get('user_query', '') or trace_data.get('query', '')).lower()
        
        # 1. Locate the tool call
        tool_call = next((step['content'] for step in trace_data.get('trace', []) 
                          if step.get('role') == 'agent' 
                          and isinstance(step.get('content'), dict)
                          and step['content'].get('name') == target_tool_name), None)
        # tool_call = trace_data[-1]['content']
        # print(tool_call.get('name'), target_tool_name)
        assert tool_call.get('name') == target_tool_name

        judge_reasoning = ""
        judge_suitable = False
        candidates = [] # We collect these here to pass to Perform logic if suitable

        args = tool_call.get('arguments', {})
        if not args:
            judge_reasoning = "No arguments to strip."
        else:
            # Check if at least one argument value appears in the query string
            for k, val in args.items():
                if isinstance(val, (str, int, float)):
                    val_str = str(val)
                    # Strict substring existence check
                    if val_str.lower() in user_query and len(val_str) > 1:
                        candidates.append((k, val))

            if candidates:
                judge_suitable = True
                judge_reasoning = f"Found {len(candidates)} arguments explicitly stated in query."
            else:
                judge_reasoning = "Arguments seem implicit or not textually present in query."

        # Exit if Judge failed
        if not judge_suitable:
            return {
                "success": False,
                "rationale": judge_reasoning,
                "mutated_trace": None
            }

        # ==========================================
        # PART 2: PERFORM LOGIC
        # ==========================================
        mutated_trace = copy.deepcopy(trace_data)
        original_query = mutated_trace.get('user_query', '') or mutated_trace.get('query', '')

        # 1. Select Pivot: Pick one argument to remove from the candidates found in Judge step
        target_key, target_value = random.choice(candidates)

        # 2. Rewrite Query (Vaguification)
        prompt = f"""
        You are simulating a user who forgets to provide specific details.
        
        Original Query: "{original_query}"
        Target Detail to Remove: "{target_value}" (associated with parameter '{target_key}')
        
        Task: Rewrite the query to keep the INTENT but remove the specific VALUE. 
        Make the request vague regarding this parameter.
        
        Examples:
        - Query: "Send $50 to Bob." | Remove: "50" -> New: "Send some money to Bob."
        - Query: "Book flight 404 to NY." | Remove: "NY" -> New: "Book flight 404."
        - Query: "Resize image to 1024px." | Remove: "1024px" -> New: "Resize the image."
        
        Output raw string only.
        """
        
        try:
            vague_query = llm_generate(prompt).strip().replace('"', '')
        except NameError:
            # Fallback for testing without LLM
            vague_query = original_query.replace(str(target_value), "some value")

        # 3. Apply Mutation
        # We Update the query to be vague...
        mutated_trace['user_query'] = vague_query
        
        # ...BUT we leave the Trace exactly as is.
        # The trace still contains the specific value, creating the hallucination discrepancy.

        # ==========================================
        # PART 3: RETURN SUCCESS
        # ==========================================
        return {
            "success": True,
            "mutated_trace": mutated_trace,
            "rationale": f"Removed explicit value '{target_value}' for parameter '{target_key}' from query to induce hallucination.",
            "metadata": {
                "removed_param": target_key, 
                "removed_value": target_value,
                "original_query": original_query,
                "new_query": vague_query
            }
        }


class AmbiguousArg(BaseMutation):
    name = "ambiguous_arg_naming"
    category = "HALLUCINATION"
    mutates_query = False
    mutates_tool_list = True
    mutates_tool_trace = False

    def mutate(self, trace_data, target_tool_name):
        """
        Consolidated Mutate Function:
        1. Judge: Does this tool have specific units/formats, OR can we 
        abbreviate its parameters to create naming ambiguity?
        2. Perform: Executes the mutation based on the strategy identified in the judge phase.
        """
        
        # ==========================
        # 1. JUDGE LOGIC
        # ==========================
        common_atomic_cmds = {'grep', 'ls', 'mv', 'mkdir', 'rm', 'cd', 'pwd', 'cp', 'touch', 'cat', 'echo', 'chmod'}
        if target_tool_name in common_atomic_cmds:
            return {"success": False, "rationale": "Atomic shell command; ambiguity not applicable.", "mutated_trace": None}

        tool_def = next((t for t in trace_data.get('tool_lists', []) if t.get('name') == target_tool_name), None)
        if not tool_def:
            return {"success": False, "rationale": "Tool not found.", "mutated_trace": None}

        prompt = f"""
        Analyze the tool '{target_tool_name}' to determine if its parameters can be intentionally made ambiguous.
        The goal is to test if an LLM will improperly guess or assume the correct format/meaning of an argument when critical information is missing from the tool's definition.

        Tool Definition: {json.dumps(tool_def)}

        Evaluate if the tool fits into one of these two cases:
        
        ### Case 1: Unit & Format Obfuscation (Missing Constraints)
        Does the tool have parameters where the specific format or unit is currently explained in the description, but if removed would cause ambiguity? 
        *Examples: Removing date formats (e.g., 'YYYY-MM-DD'), currency types (e.g., 'USD'), or string types (e.g., 'Base64') from the description.*
        
        ### Case 2: Argument Abbreviation & Erasure
        Does the tool have parameters where the name itself is highly descriptive, such that we could abbreviate the name (e.g., 'start_date' -> 'sd') AND delete its description, forcing the model to guess what 'sd' means?

        Identify which case is the strongest fit. If Case 1 exists, prioritize it. If not, evaluate for Case 2.

        Respond ONLY with a JSON object in this exact format:
        {{
            "suitable": true/false,
            "strategy": "case_1" | "case_2",
            "reasoning": "Briefly explain which parameters you are targeting and why."
        }}
        """
        try:
            judge_result = llm_judge(prompt, self.__class__.__name__, target_tool_name)
        except Exception as e:
             return {
                "success": False, 
                "rationale": f"Judge LLM failed: {e}", 
                "mutated_trace": None
            }
             
        if not judge_result.get("suitable"):
            return {
                "success": False, 
                "rationale": judge_result.get("reasoning", "Unsuitable"), 
                "mutated_trace": None
            }

        reasoning = judge_result.get("reasoning", "")
        
        # ==========================
        # 2. PERFORM LOGIC
        # ==========================
        mutated_trace = copy.deepcopy(trace_data)
        target_idx = next((i for i, t in enumerate(mutated_trace.get('tool_lists', [])) if t.get('name') == target_tool_name), -1)
        
        if target_idx == -1:
            return {
                "success": False, 
                "rationale": "Tool definition not found in mutated trace tool_lists.",
                "mutated_trace": None
            }

        target_tool = mutated_trace['tool_lists'][target_idx]
        
        use_abbreviation = "case_2" in judge_result.get("strategy", "").lower()

        if use_abbreviation:
            gen_prompt = f"""
            TASK: ARGUMENT ABBREVIATION (Case 2)
            1. Rename the target parameter keys in 'properties' to obscure 1-2 letter abbreviations (e.g., 'start_date' -> 'sd').
            2. Remove the 'description' field for these abbreviated parameters.
            3. Ensure the prototype, examples (if any), required list (if any) is updated to match the new abbreviated parameter names.
            
            Original Tool: {json.dumps(target_tool)}
            
            Output ONLY a valid JSON object representing the newly modified tool definition.
            """
        else:
            gen_prompt = f"""
            TASK: UNIT/FORMAT OBFUSCATION (Case 1)
            1. Keep the parameter names EXACTLY the same.
            2. Rewrite the 'description' fields to INTENTIONALLY REMOVE any specific units (e.g., USD, kg), formats (e.g., YYYY-MM-DD), or types. 
            3. The new description should be vague (e.g., "The date" instead of "The date in YYYY-MM-DD format").
            
            Original Tool: {json.dumps(target_tool)}
            
            Output ONLY a valid JSON object representing the newly modified tool definition.
            """
        
        try:
            modified_tool_str = llm_generate(gen_prompt)
            clean_str = modified_tool_str.replace("```json", "").replace("```", "").strip()
            modified_tool = json.loads(clean_str)
            
            mutated_trace['tool_lists'][target_idx] = modified_tool
        except Exception as e:
            return {
                "success": False,
                "rationale": f"LLM generation or parsing failed: {e}",
                "mutated_trace": None
            }
            
        return {
            "success": True,
            "mutated_trace": mutated_trace,
            "rationale": reasoning,
            "metadata": {
                "strategy": "AmbiguousArg",
                "target_tool": target_tool_name,
                "mutation_type": "case_2 (abbreviation)" if use_abbreviation else "case_1 (unit_stripping)"
            }
        }


class RedundantArg(BaseMutation):
    name = "hallucinated_arg"
    category = "HALLUCINATION"
    mutates_query = False
    mutates_tool_list = False
    mutates_tool_trace = True

    def mutate(self, trace_data, target_tool_name):
        """
        Consolidated Mutate Function:
        1. Judge: Checks if the target tool is called in the trace.
        2. Perform: Injects a 'failed' attempt with a hallucinated argument + TypeError before the real call.
        """
        
        # ==========================================
        # PART 1: JUDGE LOGIC
        # ==========================================
        # Locate the first occurrence of the target tool call
        target_step_idx = -1
        
        for i, step in enumerate(trace_data.get('trace', [])):
            if step.get('role') == 'agent':
                content = step.get('content', {})
                
                # Handle stringified JSON
                if isinstance(content, str):
                    try: content = json.loads(content)
                    except: continue
                
                if isinstance(content, dict) and content.get('name') == target_tool_name:
                    target_step_idx = i
                    break
        
        if target_step_idx == -1:
            return {
                "success": False, 
                "rationale": "Tool call not found in trace.", 
                "mutated_trace": None
            }

        # ==========================================
        # PART 2: PERFORM LOGIC
        # ==========================================
        mutated_trace = copy.deepcopy(trace_data)
        original_trace = mutated_trace.get('trace', [])
        new_trace = []
        
        injected = False
        meta_info = {}

        for i, entry in enumerate(original_trace):
            # Check if this is the target call we found earlier
            if not injected and i == target_step_idx:
                
                # Get current arguments to give context to LLM
                content = entry.get('content', {})
                if isinstance(content, str): content = json.loads(content)
                current_args = content.get('arguments', {})
                
                # =======================================================
                # 1. GENERATE ARGUMENT (KEY & VALUE)
                # =======================================================
                gen_prompt = f"""
                Given the tool '{target_tool_name}' and its current arguments {json.dumps(current_args)},
                generate ONE irrelevant, non-existent, but seemingly natural argument name and value.
                
                Example: for a banking tool, add 'notification_style="silent"'.
                Example: for a search tool, add 'sort_algorithm="bubble"'.
                
                Output ONLY a JSON object in this exact format:
                {{
                    "arg_name": "<the argument name to inject>",
                    "arg_value": <the argument value to inject (can be string, number, or boolean)>
                }}
                """
                
                try:
                    raw_arg = llm_generate(gen_prompt)
                    clean_arg = raw_arg.replace("```json", "").replace("```", "").strip()
                    parsed_arg = json.loads(clean_arg)
                    bad_arg_name = parsed_arg["arg_name"]
                    bad_arg_value = parsed_arg["arg_value"]
                    irrelevant_arg = {bad_arg_name: bad_arg_value}
                except Exception:
                    # Fallback
                    bad_arg_name = "debug_mode"
                    bad_arg_value = True
                    irrelevant_arg = {bad_arg_name: bad_arg_value}

                # =======================================================
                # 2. REWRITE QUERY (Contextualize the Hallucination)
                # =======================================================
                # We update the query so the user actually ASKS for this impossible feature
                current_query = mutated_trace.get('user_query', '') or mutated_trace.get('query', '')
                
                rewrite_prompt = f"""
                You are generating a test case for an AI.
                
                Original Query: "{current_query}"
                Hallucinated Parameter to Add: "{bad_arg_name}" = "{bad_arg_value}"
                
                Task: Rewrite the User Query so the user explicitly asks for this feature. 
                Make it sound natural.
                
                Example:
                - Input: "Send money to Bob." (Add: notify="silent")
                - Output: "Send money to Bob, but please keep the notification silent."
                
                Output raw string only.
                """
                
                try:
                    new_query = llm_generate(rewrite_prompt).strip().replace('"', '')
                    mutated_trace['user_query'] = new_query
                    # Sync keys if necessary
                    if 'query' in mutated_trace: mutated_trace['query'] = new_query
                except Exception as e:
                    # If query rewrite fails, we continue with original query (less ideal but functional)
                    pass

                # =======================================================
                # 3. MODIFY TRACE (Inject the Bad Argument)
                # =======================================================
                malformed_call = copy.deepcopy(entry)
                
                # Parse content if string
                mal_content = malformed_call['content']
                was_string = False
                if isinstance(mal_content, str):
                    mal_content = json.loads(mal_content)
                    was_string = True
                
                if 'arguments' not in mal_content: mal_content['arguments'] = {}
                
                # Update the trace with the (Key, Value) pair
                mal_content['arguments'].update(irrelevant_arg)
                
                # Update reasoning to reflect compliance with new query
                if 'reasoning' in mal_content and mal_content['reasoning']:
                    mal_content['reasoning'] += f" User requested '{bad_arg_name}', passing '{bad_arg_value}' to tool."
                else:
                    mal_content['reasoning'] = f"User requested '{bad_arg_name}', passing '{bad_arg_value}' to tool."
                
                # Re-serialize if needed
                if was_string:
                    malformed_call['content'] = json.dumps(mal_content)
                else:
                    malformed_call['content'] = mal_content
                
                # Expected error message (for metadata/checking)
                error_msg = f"TypeError: {target_tool_name}() got an unexpected keyword argument '{bad_arg_name}'"
                
                # Add the malformed call to the new trace
                new_trace.append(malformed_call)
                
                injected = True
                meta_info = {
                    "strategy": "Redundant Argument Injection",
                    "injected_arg": bad_arg_name, 
                    "injected_val": bad_arg_value,
                    "expected_error_msg": error_msg
                }
            else:
                new_trace.append(entry)
            
        mutated_trace['trace'] = new_trace
        
        # ==========================================
        # PART 3: RETURN SUCCESS
        # ==========================================
        return {
            "success": True,
            "mutated_trace": mutated_trace,
            "rationale": f"Injecting invalid arg '{meta_info.get('injected_arg')}' requested by user query.",
            "metadata": meta_info
        }


class MissingTypeHint(BaseMutation):
    name = "missing_datatype_hint"
    category = "HALLUCINATION"
    mutates_query = False
    mutates_tool_list = True
    mutates_tool_trace = False

    def mutate(self, trace_data, target_tool_name):
        """
        Consolidated Mutate Function:
        1. Judge: Checks if removing type hints creates ambiguity (e.g., "123" vs 123, "true" vs True).
        2. Perform: Removes 'type' keys from JSON schema and strips type hints from Python prototype string.
        """

        # ==========================================
        # PART 1: JUDGE LOGIC
        # ==========================================
        tool_def = next((t for t in trace_data.get('tool_lists', []) if t['name'] == target_tool_name), None)
        if not tool_def:
            return {
                "success": False, 
                "rationale": "Tool definition not found.", 
                "mutated_trace": None
            }

        judge_prompt = f"""
        You are a Senior QA Engineer performing a 'Schema Stress Test' on an AI Agent.
        
        ### Task:
        Evaluate if removing 'type' hints (e.g., string, integer, boolean) from the tool '{target_tool_name}' 
        parameters would cause an LLM to misformat arguments or hallucinate values.
        
        ### Tool Definition:
        {json.dumps(tool_def, indent=2)}

        ### Analysis Criteria (High Suitability if):
        1. **Numeric vs String Ambiguity**: Does the tool have IDs or codes (like 'zip_code', 'order_id', 'status') 
           that look like numbers but must be strings?
        2. **Strict Boolean Dependency**: Are there flags (like 'dry_run', 'force', 'recursive') where the LLM 
           might send "yes"/"no" instead of true/false without a type hint?
        3. **Unit Ambiguity**: Does the tool take numeric values (like 'amount', 'duration', 'threshold') 
           where the data type determines if it's a float (10.5) or an int (10)?
        4. **Overloaded Parameters**: Are there generic fields like 'value' or 'query' that highly depend on 
           type definitions to distinguish between a search string and a structured object?

        ### Response:
        Respond ONLY in JSON format:
        {{
            "suitable": true/false,
            "reasoning": "Detailed explanation of which parameter is most vulnerable and why."
        }}
        """
        
        try:
            judge_result = llm_judge(judge_prompt, self.__class__.__name__, target_tool_name)
        except Exception as e:
            return {
                "success": False, 
                "rationale": f"Judge LLM failed: {e}", 
                "mutated_trace": None
            }

        if not judge_result.get("suitable"):
            return {
                "success": False, 
                "rationale": judge_result.get("reasoning", "Unsuitable for type stripping"), 
                "mutated_trace": None
            }

        # ==========================================
        # PART 2: PERFORM LOGIC
        # ==========================================
        mutated_trace = copy.deepcopy(trace_data)
        
        # Locate the tool index
        target_idx = -1
        for i, tool in enumerate(mutated_trace.get('tool_lists', [])):
            if tool.get('name') == target_tool_name:
                target_idx = i
                break
                
        if target_idx == -1:
             return {
                "success": False, 
                "rationale": "Perform failed: Tool definition lost between judge and perform.", 
                "mutated_trace": None
            }

        target_tool = mutated_trace['tool_lists'][target_idx]

        # --- Step 1: Strip "type" from JSON parameters ---
        params_container = target_tool.get('parameters') or target_tool.get('input_schema')

        if params_container:
            params = params_container.get('properties', {})
            for p_name in params:
                # Strip the type hint
                if 'type' in params[p_name]:
                    del params[p_name]['type']

        # --- Step 2: Strip types from the Prototype string ---
        current_prototype = target_tool.get('prototype', "")

        if current_prototype:
            prompt = f"""
            Rewrite the following Python function prototype to remove ALL type hints (e.g., : str, -> None).
            
            Keep the function name, argument names, and default values exactly the same.
            
            Input Prototype: {current_prototype}
            
            Desired Format: def function_name(arg1, arg2=default_val):
            
            Output ONLY the raw code string. No markdown, no 'pass', no explanations.
            """
            
            try:
                new_prototype = llm_generate(prompt)
                # Clean up potential markdown or trailing colons/pass
                new_prototype = new_prototype.replace("```python", "").replace("```", "").strip()
                if not new_prototype.endswith(":"):
                    new_prototype += ":"
                    
                target_tool['prototype'] = new_prototype
            except Exception:
                pass
        # Save the modifications back to the trace
        mutated_trace['tool_lists'][target_idx] = target_tool
                
        # ==========================================
        # PART 3: RETURN SUCCESS
        # ==========================================
        return {
            "success": True,
            "mutated_trace": mutated_trace,
            "rationale": judge_result.get("reasoning"),
            "metadata": {
                "strategy": "Type Hint Removal",
                "prototype_modified": bool(current_prototype)
            }
        }


