import json
import copy
import os
from deepdiff import DeepDiff
from colorama import Fore, Style, init
from ansi2html import Ansi2HTMLConverter

init(autoreset=True)
conv = Ansi2HTMLConverter(dark_bg=True, inline=True)

class MutationTester:
    def __init__(self, mutation_instance, html_path, model_name, input_dir):
        self.mutation = mutation_instance
        self.html_path = html_path
        self.source = "bfcl"
        self.model_name = model_name
        
        # Ensure HTML header exists
        if self.html_path and not os.path.exists(self.html_path):
            with open(self.html_path, "w") as f:
                f.write("<html><head><meta charset='UTF-8'></head>")
                f.write("<body style='background-color: #111; color: #eee; font-family: monospace; padding: 20px;'>")
                f.write("<h1>Red-Team Mutation Report</h1><hr>")

    def log(self, text, color=Fore.WHITE, style=Style.NORMAL):
        formatted_text = f"{style}{color}{text}{Style.RESET_ALL}"
        print(formatted_text)
        # Append to HTML report
        if self.html_path and os.path.exists(self.html_path):
            html_line = conv.convert(formatted_text, full=False)
            with open(self.html_path, "a") as f:
                f.write(html_line.replace("\n", "") + "<br/>")

    def _get_tool_analysis(self, trace):
        all_calls = []
        first_occurrences = {}
        for i, step in enumerate(trace):
            if step.get("role") == "agent":
                content = step.get("content", {})
                # Handle stringified JSON content if necessary
                if isinstance(content, str):
                    try: content = json.loads(content)
                    except: pass
                    
                if isinstance(content, dict):
                    name = content.get("name")
                    if name:
                        all_calls.append(name)
                        if name not in first_occurrences:
                            first_occurrences[name] = i
        return all_calls, first_occurrences

    def run_test(self, original_trace_data, skip_meta=True):
        """
        Executes the mutation logic and returns a list of HF-style dataset rows.
        """
        trace = original_trace_data.get("trace", [])
        _, distinct_tools = self._get_tool_analysis(trace)
        
        dataset_rows = []

        self.log(f"\n{'='*20} MUTATOR: {self.mutation.__class__.__name__} {'='*20}", Fore.CYAN)
        
        for tool_name, index in distinct_tools.items():
            if skip_meta and tool_name in ["finish", "clarify"]:
                continue

            # 1. Truncate Trace (Simulate the state at that step)
            input_trace = copy.deepcopy(original_trace_data)
            input_trace["trace"] = trace[:index + 1]

            # 2. CALL MUTATE (Merged Logic)
            # Should return dict with keys: 'mutated_trace', 'rationale', 'metadata'
            # Or return None
            try:
                result = self.mutation.mutate(input_trace, tool_name)
            except NotImplementedError:
                self.log(f"   [SKIP] {tool_name}: mutate() not implemented yet.", Fore.RED)
                continue
            except Exception as e:
                self.log(f"   [ERROR] {tool_name}: {e}", Fore.RED)
                continue

            # 2. CHECK SUCCESS FLAG
            # We explicitly check for the boolean 'success' key
            if result and result.get("success", False) is True:
                new_trace = result.get("mutated_trace")
                rationale = result.get("rationale", "No rationale provided")
                meta = result.get("metadata", {})

                # 3. Calculate Diff
                # Verify that actual changes occurred
                diff = DeepDiff(input_trace, new_trace, ignore_order=True)
                
                if diff:
                    self.log(f">>> SUCCESS: {tool_name}", Fore.GREEN, Style.BRIGHT)
                    
                    # 4. Create 5-Column Entry
                    dataset_entry = {
                        "mutation_category": getattr(self.mutation, "category", "UNKNOWN"),
                        "original_trace": input_trace,
                        "new_trace": new_trace,
                        "difference": json.loads(diff.to_json()), # Serialize DeepDiff
                        "mutation_metadata": {
                            "mutator_name": self.mutation.__class__.__name__,
                            "target_tool": tool_name,
                            "rationale": rationale,
                            "internal_meta": meta,
                            "source": self.source,
                            "model_name": self.model_name
                        }
                    }
                    dataset_rows.append(dataset_entry)
                else:
                    self.log(f"   [SKIP] {tool_name}: Mutation reported success, but no DeepDiff detected.", Fore.YELLOW)
            
            # 5. HANDLE FAILURE / UNSUITABLE
            else:
                # Extract the rationale for why it was skipped (e.g., "Tool call not found" or "No args in query")
                fail_reason = "Mutate returned None"
                if result and "rationale" in result:
                    fail_reason = result["rationale"]
                
                # Log this as a skip so you can debug why specific tools aren't being mutated
                # Using DIM style so it doesn't clutter the logs too much
                self.log(f"   [SKIP] {tool_name}: {fail_reason}", Fore.WHITE, Style.DIM) 
                pass

        return dataset_rows