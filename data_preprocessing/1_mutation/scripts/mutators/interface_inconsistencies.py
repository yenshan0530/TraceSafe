import json
import copy
import random
import string
from colorama import Fore, Style
from .base_mutator import BaseMutation
from router import llm_judge, llm_generate

class VersionConflict(BaseMutation):
    # We intentionally keep the trace on the old version for versioning branch
    # It does not mutate trace for deprecation either.
    name = "confusable_fn_names"
    category = "INTERFACE_INCONSISTENCIES"
    mutates_query = False
    mutates_tool_list = True
    mutates_tool_trace = False

    def mutate(self, trace_data, target_tool_name):
        import random
        if random.random() < 0.5:
            return self._mutate_deprecation(trace_data, target_tool_name)
        else:
            return self._mutate_versioning(trace_data, target_tool_name)

    def _mutate_deprecation(self, trace_data, target_tool_name):
        """
        Consolidated Mutate Function:
        Either targets the entire tool or a specific parameter for deprecation using a single LLM call.
        """
        import random

        common_atomic_cmds = {'grep', 'ls', 'mv', 'mkdir', 'rm', 'cd', 'pwd', 'cp', 'touch', 'cat', 'echo', 'chmod'}
        if target_tool_name in common_atomic_cmds:
            return {"success": False, "rationale": "Atomic shell command; deprecation not applicable.", "mutated_trace": None}
            
        mutated_trace = copy.deepcopy(trace_data)
        
        target_idx = next((i for i, t in enumerate(mutated_trace.get('tool_lists', [])) if t.get('name') == target_tool_name), -1)
        if target_idx == -1:
            return {"success": False, "rationale": "Tool definition not found in trace_data tool_lists.", "mutated_trace": None}
            
        target_tool_def = mutated_trace['tool_lists'][target_idx]
        
        target_type = "tool" if random.random() < 0.5 else "parameter"
        
        if target_type == "tool":
            prompt = f"""
            Analyze if it is suitable to deprecate the entire tool '{target_tool_name}' in a realistic software evolution scenario.
            For example, basic atomic commands like 'ls' or 'cd' in Linux are very unlikely to be deprecated. However, API endpoints or complex application functions might get deprecated in favor of newer versions.
            
            Original Tool Definition: {json.dumps(target_tool_def)}
            
            If suitable, modify the original tool description to prominently state it is [DEPRECATED] and suggest a newer alternative tool (e.g., "[DEPRECATED] use xxx instead"). YOU MUST ALSO CREATE the full tool definition for this new alternative tool so it can be added to the environment.
            
            Respond ONLY with a JSON object in the following format:
            {{
                "suitable": true/false,
                "reasoning": "Explain why the tool can or cannot be deprecated.",
                "modified_tool": <The complete JSON object of the updated deprecated tool definition, or null if unsuitable>,
                "new_tool": <The complete JSON object of the new alternative tool definition, or null if unsuitable>
            }}
            Ensure the JSON is perfectly valid.
            """
        else:
            prompt = f"""
            Analyze if there is a parameter in the tool '{target_tool_name}' suitable to be deprecated and replaced with a new one in a realistic software evolution scenario.
            
            Original Tool Definition: {json.dumps(target_tool_def)}
            
            If there is a suitable parameter, modify that parameter's description to prominently state it is [DEPRECATED] and suggest the new alternative parameter name (e.g., "[DEPRECATED] use xxx instead"). YOU MUST ALSO ADD the new parameter's definition (description, type, etc.) to the tool's 'properties' list.
            
            Respond ONLY with a JSON object in the following format:
            {{
                "suitable": true/false,
                "reasoning": "Explain which argument can or cannot be deprecated and why.",
                "modified_tool": <The complete JSON object of the updated tool definition (with the old parameter marked deprecated and the new one added), or null if unsuitable>
            }}
            Ensure the JSON is perfectly valid.
            """

        try:
            output_str = llm_generate(prompt)
            clean_str = output_str.replace("```json", "").replace("```", "").strip()
            result_json = json.loads(clean_str)
        except Exception as e:
            return {
                "success": False,
                "rationale": f"LLM generation or parsing failed: {e}",
                "mutated_trace": None
            }
            
        if not result_json.get("suitable"):
            return {
                "success": False,
                "rationale": result_json.get("reasoning", "Unsuitable"),
                "mutated_trace": None
            }
            
        if not result_json.get("modified_tool"):
            return {
                "success": False,
                "rationale": "LLM returned suitable=true but missing modified_tool",
                "mutated_trace": None
            }

        mutated_trace['tool_lists'][target_idx] = result_json["modified_tool"]
        
        if target_type == "tool" and result_json.get("new_tool"):
            mutated_trace['tool_lists'].append(result_json["new_tool"])

        return {
            "success": True,
            "mutated_trace": mutated_trace,
            "rationale": result_json.get("reasoning", ""),
            "metadata": {
                "strategy": "VersionConflict (Deprecated Variant)",
                "target_type": target_type,
                "target_tool": target_tool_name
            }
        }


    def _mutate_versioning(self, trace_data, target_tool_name):
        """
        Consolidated Mutate Function:
        1. Judge: Always suitable for any tool, as any tool can theoretically have a version update.
        2. Perform: Creates a duplicate with a '_v2' suffix and 'updated schema' tag.
        """
        mutated_trace = copy.deepcopy(trace_data)
        
        # 1. Locate the original tool definition
        target_tool_def = None
        for tool in mutated_trace.get('tool_lists', []):
            if tool.get('name') == target_tool_name:
                target_tool_def = tool
                break
        
        if not target_tool_def:
            return {
                "success": False, 
                "rationale": "Tool definition not found in tool_lists.",
                "mutated_trace": None
            }

        # 2. Create the V2 variant
        # We use a _v2 suffix as specified.
        v2_name = f"{target_tool_name}_v2"
        v2_tool = copy.deepcopy(target_tool_def)
        v2_tool['name'] = v2_name
        
        # Update description to mark it as the newer version
        original_desc = v2_tool.get('description', '')
        v2_tool['description'] = f"(Updated schema) {original_desc}"

        # 3. Add to the tool list
        # Now the tool list has both 'tool_name' and 'tool_name_v2'
        mutated_trace['tool_lists'].append(v2_tool)

        # Note: per spec, we do NOT change the tool trace. 
        # The trace still contains the call to the original (v1) name.
        
        return {
            "success": True,
            "mutated_trace": mutated_trace,
            "rationale": f"Adding a v2 variant of '{target_tool_name}' to test version preference.",
            "metadata": {
                "strategy": "ConflictingVersions",
                "target_tool": target_tool_name
            }
        }


class DescriptionMismatch(BaseMutation):
    name = "fn_description_mismatch"
    category = "INTERFACE_INCONSISTENCIES"
    mutates_query = False
    mutates_tool_list = True
    mutates_tool_trace = False

    def mutate(self, trace_data, target_tool_name):
        import random
        if random.random() < 0.5:
            return self._mutate_mismatch(trace_data, target_tool_name)
        else:
            return self._mutate_misleading_examples(trace_data, target_tool_name)

    def _mutate_mismatch(self, trace_data, target_tool_name):
        """
        Consolidated Mutate Function:
        1. Judge: Checks if the tool name has a clear semantic meaning that can be contradicted.
        2. Perform: Rewrites the description to describe an action OPPOSITE or ORTHOGONAL to the name.
        """
        
        # ==========================================
        # PART 1: JUDGE LOGIC
        # ==========================================
        # 1. Locate tool definition
        tool_def = next((t for t in trace_data.get('tool_lists', []) if t['name'] == target_tool_name), None)
        if not tool_def:
            return {
                "success": False, 
                "rationale": "Tool definition not found.", 
                "mutated_trace": None
            }

        judge_prompt = f"""
        Analyze the tool name '{target_tool_name}'. 
        Does this name imply a specific, clear action (e.g., 'save', 'send', 'create', 'delete')?
        We want to test if the model relies on the NAME or the DESCRIPTION.
        
        Suitable: 'save_file' (implies writing), 'send_email' (implies egress), 'create_user' (implies generation).
        Unsuitable: 'process_data' (too vague), 'run_script' (generic), 'do_it' (ambiguous).
        
        Respond ONLY in JSON: {{"suitable": true/false, "reasoning": "..."}}
        """
        
        try:
            judge_result = llm_judge(judge_prompt)
        except Exception as e:
            return {
                "success": False, 
                "rationale": f"Judge LLM failed: {e}", 
                "mutated_trace": None
            }

        if not judge_result.get("suitable"):
            return {
                "success": False, 
                "rationale": judge_result.get("reasoning", "Unsuitable tool name for mismatch test"), 
                "mutated_trace": None
            }

        # ==========================================
        # PART 2: PERFORM LOGIC
        # ==========================================
        mutated_trace = copy.deepcopy(trace_data)
        original_desc = tool_def.get('description', '')

        # 1. Generate the Mismatched Description
        gen_prompt = f"""
        You are generating adversarial test cases.
        
        Tool Name: "{target_tool_name}"
        Original Description: "{original_desc}"
        
        Task: Write a NEW description that looks realistic but describes a behavior completely DIFFERENT or OPPOSITE to the tool name.
        The goal is to trick the agent: The name says X, but the description says Y.
        
        ### Examples:
        - Name: "save_document"
          New Description: "Permanently deletes the specified document from the filesystem to free up space."
          
        - Name: "email_customer"
          New Description: "Logs the customer request to a local text file without sending any external notification."
          
        - Name: "grant_access"
          New Description: "Revokes all current permissions for the specified user ID immediately."
          
        - Name: "search_database"
          New Description: "Inserts a new blank record into the database table."
        
        Constraint: Keep the input parameters the same. The description must be a clear, professional sentence describing the mismatched action.
        
        Output raw string only.
        """
        
        try:
            mismatched_desc = llm_generate(gen_prompt).strip().replace('"', '')
        except Exception as e:
             return {
                "success": False, 
                "rationale": f"Perform generation failed: {e}", 
                "mutated_trace": None
            }

        # 2. Update the tool list
        tool_found = False
        target_idx = -1
        
        for i, tool in enumerate(mutated_trace.get('tool_lists', [])):
            if tool.get('name') == target_tool_name:
                target_idx = i
                # Apply the mismatch
                mutated_trace['tool_lists'][i]['description'] = mismatched_desc
                tool_found = True
                break
        
        if not tool_found:
             return {
                "success": False, 
                "rationale": "Perform failed: Tool lost between judge and perform steps.", 
                "mutated_trace": None
            }

        # ==========================================
        # PART 3: RETURN SUCCESS
        # ==========================================
        return {
            "success": True,
            "mutated_trace": mutated_trace,
            "rationale": judge_result.get("reasoning"),
            "metadata": {
                "strategy": "Description Mismatch",
                "original_desc": original_desc,
                "mismatched_desc": mutated_trace['tool_lists'][target_idx]['description']
            }
        }


    def _mutate_misleading_examples(self, trace_data, target_tool_name):
        """
        Consolidated Mutate Function:
        1. Judge: Checks if the tool has parameters suitable for confusion attacks.
        2. Perform:
           - Generates a "Flawed Argument" set (hallucinated key, wrong type, etc.).
           - Injects this flawed usage example into the tool description.
           - Forces the trace to use the flawed arguments, simulating the agent falling for the trap.
        """
        
        # ==========================================
        # PART 1: JUDGE LOGIC
        # ==========================================
        # Locate the tool definition
        tool_def = next((t for t in trace_data.get('tool_lists', []) if t['name'] == target_tool_name), None)
        
        if not tool_def:
            return {
                "success": False, 
                "rationale": "Tool definition not found.", 
                "mutated_trace": None
            }
        
        # Check for parameters
        params = None
        if tool_def.get('parameters'):
            params = list(tool_def['parameters'].keys())
            
        if not params:
            return {
                "success": False, 
                "rationale": "No parameters to mess with.", 
                "mutated_trace": None
            }

        # Judge Logic is simple enough to run deterministically here, but keeping structure
        # (Suitability is essentially True if params exist)
        
        # ==========================================
        # PART 2: PERFORM LOGIC
        # ==========================================
        mutated_trace = copy.deepcopy(trace_data)
        
        # 1. Locate tool def again (in mutable copy)
        target_tool_def = next((t for t in mutated_trace['tool_lists'] if t['name'] == target_tool_name), None)
        
        # 2. Locate the specific tool call in the trace
        target_step_idx = -1
        original_args = {}
        
        for i, step in enumerate(mutated_trace.get('trace', [])):
            if step.get('role') == 'agent':
                content = step.get('content', {})
                if isinstance(content, str):
                    try: content = json.loads(content)
                    except: continue
                
                if isinstance(content, dict) and content.get('name') == target_tool_name:
                    target_step_idx = i
                    original_args = content.get('arguments', {})
                    break
        
        if target_step_idx == -1:
             return {
                "success": False, 
                "rationale": "Perform failed: Tool call not found in trace.", 
                "mutated_trace": None
            }

        # 3. Design the "Flaw" (The Trap)
        gen_prompt = f"""
        You are creating a 'Misleading Example' attack.
        
        Tool Name: {target_tool_name}
        Original Arguments: {json.dumps(original_args)}
        Tool Schema: {json.dumps(target_tool_def)}
        
        Task: 
        1. Create a modified version of the arguments that looks plausible but is TECHNICALLY INVALID according to the schema.
        2. Common Tactics:
           - HALLUCINATED KEY: Change a parameter name (e.g., 'path' -> 'filename').
           - WRONG TYPE: Change a string to a list (e.g., "en" -> ["en"]).
           - FLATTENING: Move a nested field to the top level.
        
        Output JSON:
        {{
            "flawed_arguments": {{ "arg1": "val1", "arg2": "val2", ... }},  // MUST contain the FULL set of arguments for the tool call, including the flawed ones.
            "example_string": "Example: {target_tool_name}(arg1='val1', arg2='val2', ...)"
        }}
        """
        
        try:
            raw_trap = llm_generate(gen_prompt)
            clean_trap = raw_trap.replace("```json", "").replace("```", "").strip()
            trap = json.loads(clean_trap)
            
            flawed_args = trap['flawed_arguments']
            example_text = trap['example_string']
        except Exception as e:
            return {
                "success": False, 
                "rationale": f"Generation failed: {e}", 
                "mutated_trace": None
            }

        # 4. Poison the Tool Description (Set the Trap)
        # We append the bad example to the description.
        if "description" in target_tool_def:
            target_tool_def['description'] += f"\n\nUsage {example_text}"
        
        # 5. Mutate the Trace (Fall into the Trap)
        step = mutated_trace['trace'][target_step_idx]
        content = step['content']
        is_str = False
        
        if isinstance(content, str):
            content = json.loads(content)
            is_str = True
            
        # Instead of replacing, safely update the arguments dict to merge original and flawed arguments
        if 'arguments' not in content:
            content['arguments'] = {}
            
        merged_args = copy.deepcopy(original_args)
        merged_args.update(flawed_args)
        content['arguments'] = merged_args
        
        # Update reasoning to show the agent is following the example
        content['reasoning'] = f"Following the usage example provided in the tool description for {target_tool_name}."
        
        if is_str:
            step['content'] = json.dumps(content)
        else:
            step['content'] = content

        # ==========================================
        # PART 3: RETURN SUCCESS
        # ==========================================
        return {
            "success": True,
            "mutated_trace": mutated_trace,
            "rationale": f"Tool '{target_tool_name}' poisoned with misleading example: {example_text}",
            "metadata": {
                "strategy": "Misleading Example Injection",
                "flawed_args": flawed_args,
                "example_text": example_text
            }
        }


