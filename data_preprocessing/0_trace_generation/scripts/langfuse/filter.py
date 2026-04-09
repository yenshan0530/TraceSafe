import json
import os
import re
from collections import Counter
from dateutil import parser

def load_data(filename):
    data = []
    print(f"   Reading {filename}...")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue 
    except FileNotFoundError:
        print(f"     [Error] File not found: {filename}")
        return []
    return data

def get_first_user_content(messages):
    if not messages:
        return None
    if isinstance(messages, str):
        try:
            messages = json.loads(messages)
        except json.JSONDecodeError:
            return messages
    if isinstance(messages, list) and len(messages) > 0 and isinstance(messages[0], list):
        flat_messages = [item for sublist in messages for item in sublist]
    elif isinstance(messages, list):
        flat_messages = messages
    else:
        flat_messages = [messages]
    for msg in flat_messages:
        if isinstance(msg, dict):
            if msg.get('role') == 'user':
                return msg.get('content')
        elif isinstance(msg, str):
            return msg
    return None

def natural_sort_key(s):
    """
    Extracts numbers from a string to allow sorting by integer value.
    Example: 'multi_turn_base_99' -> [99]
    Example: 'multi_turn_base_1-0-0' -> [1, 0, 0]
    """
    return [int(text) for text in re.findall(r'\d+', s)]

def main():
    # --- CONFIGURATION ---
    QUESTIONS_FILE = './gorilla/berkeley-function-call-leaderboard/bfcl_eval/data/BFCL_v4_multi_turn_miss_param.json'
    OBSERVATIONS_FILE = 'all_observations.jsonl'
    
    # Output directory named after the QUESTIONS file
    questions_base = os.path.splitext(os.path.basename(QUESTIONS_FILE))[0]
    output_dir = f"{questions_base}_results"
    os.makedirs(output_dir, exist_ok=True)
    # ---------------------

    print("1. Loading Data...")
    questions_data = load_data(QUESTIONS_FILE)
    observations_data = load_data(OBSERVATIONS_FILE)

    if not questions_data or not observations_data:
        return

    print(f"2. Indexing {len(questions_data)} questions...")
    prompt_to_qid = {}
    for entry in questions_data:
        q_id = entry.get('id')
        prompt_text = get_first_user_content(entry.get('question', []))
        if prompt_text:
            prompt_to_qid[prompt_text] = q_id

    print(f"3. Processing {len(observations_data)} observations...")
    best_entries = {}
    
    for obs in observations_data:
        # Extract model from costDetails as requested
        # Fallback to top-level 'model' if costDetails is missing
        raw_model = obs.get('costDetails', {}).get('model') or obs.get('model')
        
        # Sanitize for filesystem
        model_name_fs = str(raw_model).replace('/', '_').replace(' ', '_') if raw_model else "unknown_model"

        prompt_text = get_first_user_content(obs.get('input', []))
        if not prompt_text or prompt_text not in prompt_to_qid:
            continue

        q_id = prompt_to_qid[prompt_text]
        try:
            obs_time = parser.isoparse(obs['startTime'])
        except (ValueError, KeyError, TypeError):
            continue

        key = (model_name_fs, q_id)
        if key not in best_entries or obs_time > best_entries[key]['timestamp']:
            # Save only the requested fields
            slim_data = {
                "id": q_id,
                "model": raw_model,
                "input": obs.get("input"),
                "output": obs.get("output")
            }
            best_entries[key] = { 'timestamp': obs_time, 'data': slim_data, 'model_fs': model_name_fs }

    # --- STEP 4: ORGANIZE AND SORT ---
    model_groups = {}
    for entry in best_entries.values():
        m = entry['model_fs']
        if m not in model_groups:
            model_groups[m] = []
        model_groups[m].append(entry['data'])

    # Sort each model's data by the integer values found in the ID
    for m in model_groups:
        model_groups[m].sort(key=lambda x: natural_sort_key(x['id']))

    print("\n" + "="*50)
    print(f"{'Model Name':<35} | {'Instances':<8}")
    print("-" * 50)
    
    for model_name_fs, traces in sorted(model_groups.items()):
        output_path = os.path.join(output_dir, f"{model_name_fs}.jsonl")
        with open(output_path, 'w', encoding='utf-8') as f:
            for trace in traces:
                f.write(json.dumps(trace) + '\n')
        print(f"{model_name_fs[:35]:<35} | {len(traces):<8}")
    
    print("="*50 + "\n")
    print(f"Done! Results saved to directory: {output_dir}/")

if __name__ == "__main__":
    main()