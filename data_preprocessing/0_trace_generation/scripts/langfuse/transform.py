import json
import os
import re
import ast

def generate_prototype(tool):
    """
    Generates a python-style function signature from the tool definition.
    """
    if not tool:
        return "def unknown(): pass"
        
    name = tool.get('name', 'unknown')
    # Safety: Ensure parameters is a dict before accessing properties
    parameters = tool.get('parameters', {})
    if parameters is None: parameters = {}
    
    params = parameters.get('properties', {})
    required = parameters.get('required', [])
    
    param_list = []
    if params:
        for p_name, p_info in params.items():
            if not p_info: continue # Skip if param info is None
            p_type = p_info.get('type', 'Any')
            default = p_info.get('default', None)
            if p_name in required:
                param_list.append(f"{p_name}: {p_type}")
            else:
                default_val = f"'{default}'" if isinstance(default, str) else default
                param_list.append(f"{p_name}: {p_type} = {default_val}")
                
    return f"def {name}({', '.join(param_list)}) -> Any: pass"

def parse_tool_calls(text):
    if not isinstance(text, str): return []
    calls = []
    pattern = r'(\w+)\((.*?)\)'
    matches = re.findall(pattern, text)
    
    for name, args_str in matches:
        args_dict = {}
        if args_str.strip():
            arg_pairs = re.findall(r'(\w+)\s*=\s*(["\']?.*?["\']?)(?:,|$)', args_str)
            for k, v in arg_pairs:
                v = v.strip("'\"")
                if v.lower() == 'true': v = True
                elif v.lower() == 'false': v = False
                elif v.isdigit(): v = int(v)
                args_dict[k] = v
        calls.append({"name": name, "arguments": args_dict})
    return calls

def extract_tools_from_system(system_msg):
    if not system_msg: return []

    anchor = "Here is a list of functions in json format that you can invoke."
    if anchor in system_msg:
        try:
            json_text = system_msg.split(anchor)[1]
            start = json_text.find('[')
            end = json_text.rfind(']') + 1
            if start != -1 and end != -1:
                return json.loads(json_text[start:end])
        except Exception:
            pass

    try:
        matches = re.findall(r'\[\s*\{.*?\}\s*\]', system_msg, re.DOTALL)
        if matches:
            longest_match = max(matches, key=len)
            return json.loads(longest_match)
    except Exception:
        pass

    return []

def transform_entry(entry):
    try:
        if not entry: return None
        
        inputs = entry.get('input', [])
        outputs = entry.get('output', [])
        
        # 1. Extract Tools
        system_msg_content = next((m.get('content', "") for m in inputs if m.get('role') in ['developer', 'system']), "")
        raw_tools = extract_tools_from_system(system_msg_content)
        
        if not raw_tools:
            raw_tools = entry.get('tools', [])
        
        # 2. Extract User Query
        user_queries = [m.get('content', "") for m in inputs if m.get('role') == 'user' and "role': 'tool'" not in str(m.get('content'))]
        if not user_queries: return None
        
        # 3. Interleaved Trace
        new_trace = []
        called_tool_names = set()
        
        full_conversation = inputs[1:] + (outputs if isinstance(outputs, list) else [outputs])

        i = 0
        while i < len(full_conversation):
            msg = full_conversation[i]
            if not msg: # Skip None messages
                i += 1
                continue
                
            role = msg.get('role')
            content = msg.get('content', "")

            if role == 'assistant':
                if isinstance(content, list) and content:
                    content = content[0].get('text', "")
                
                current_calls = parse_tool_calls(content)
                
                # Peek ahead for simulator response
                next_msg = full_conversation[i+1] if i + 1 < len(full_conversation) else None
                simulator_results = []
                is_simulator_next = False
                
                if next_msg and next_msg.get('role') == 'user':
                    next_content = next_msg.get('content', "")
                    if isinstance(next_content, str) and ("role': 'tool'" in next_content or next_content.strip().startswith('[')):
                        try:
                            simulator_results = ast.literal_eval(next_content)
                            if isinstance(simulator_results, list):
                                is_simulator_next = True
                        except:
                            pass

                if current_calls and is_simulator_next:
                    for call, res in zip(current_calls, simulator_results):
                        called_tool_names.add(call['name'])
                        new_trace.append({
                            "role": "agent",
                            "content": call,
                            "reasoning": "Executing tool call."
                        })
                        sim_content = res.get('content', "") if isinstance(res, dict) else str(res)
                        new_trace.append({
                            "role": "tool",
                            "content": sim_content
                        })
                    i += 2
                    continue
                
                elif current_calls:
                    for call in current_calls:
                        called_tool_names.add(call['name'])
                        new_trace.append({
                            "role": "agent",
                            "content": call,
                            "reasoning": "Executing tool call (No result captured)."
                        })
                    i += 1
                else:
                    i += 1

            elif role == 'user':
                if "role': 'tool'" not in str(content):
                    new_trace.append({"role": "user", "content": content})
                i += 1
            else:
                i += 1

        # 4. Final Tool List (With Safety Check)
        final_tools = []
        if raw_tools:
            for t in raw_tools:
                if not t: continue # Skip None tools
                
                t_name = t.get('name', 'unknown')
                final_tools.append({
                    "name": t_name,
                    "description": t.get('description', ''),
                    "prototype": generate_prototype(t),
                    "parameters": t.get('parameters', {}).get('properties', {}),
                    "is_distractor": t_name not in called_tool_names
                })

        return {
            "domain": "BFCL Code Agents",
            "user_query": user_queries[0],
            "scenario_description": "Interleaved multi-turn tool interaction.",
            "environment": "Gorilla File System environment.",
            "tool_lists": final_tools,
            "trace": new_trace,
            "agent_model": entry.get('model', 'unknown')
        }
    except Exception:
        # Silently fail and return None to skip this entry
        return None

def main():
    dir_name = 'BFCL_v4_multi_turn_base_results'
    input_dir = f'raw/{dir_name}'
    output_dir = f'transformed-gorilla/{dir_name}'
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_dir):
        print(f"Input directory {input_dir} not found.")
        return

    for filename in os.listdir(input_dir):
        if filename.endswith('.jsonl'):
            print(f"Processing {filename}...")
            with open(os.path.join(input_dir, filename), 'r') as f_in, \
                 open(os.path.join(output_dir, filename), 'w') as f_out:
                for line in f_in:
                    if not line.strip(): continue
                    try:
                        entry = json.loads(line)
                        transformed = transform_entry(entry)
                        if transformed:
                            f_out.write(json.dumps(transformed) + '\n')
                    except json.JSONDecodeError:
                        continue

if __name__ == "__main__":
    main()