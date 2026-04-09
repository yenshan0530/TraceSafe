import os
import json
import jsonlines
from collections import defaultdict


def main():
    base_dir = os.path.join(
        os.path.dirname(__file__),
        '../results/golden_collection_categories'
    )
    base_dir = os.path.abspath(base_dir)

    if not os.path.exists(base_dir):
        print(f"Directory not found: {base_dir}")
        return

    model_counts = defaultdict(int)
    model_turns = defaultdict(list)
    unique_queries = set()
    model_turn_lengths = defaultdict(list)
    model_total_lengths = defaultdict(list)

    raw_base_dir = os.path.join(
        os.path.dirname(__file__),
        '../results/eval_data/raw_mutated_results'
    )
    raw_base_dir = os.path.abspath(raw_base_dir)
    raw_counts = defaultdict(int)

    if os.path.exists(raw_base_dir):
        for model_name in os.listdir(raw_base_dir):
            model_path = os.path.join(raw_base_dir, model_name)
            if not os.path.isdir(model_path):
                continue
            for root, _, files in os.walk(model_path):
                for file in files:
                    if file.endswith('.json') or file.endswith('.jsonl'):
                        fpath = os.path.join(root, file)
                        try:
                            with open(fpath, 'r') as f:
                                data = json.load(f)
                                if isinstance(data, list):
                                    raw_counts[model_name] += len(data)
                                else:
                                    raw_counts[model_name] += 1
                        except Exception:
                            continue

    for fname in os.listdir(base_dir):
        if not fname.endswith('.jsonl'):
            continue
        fpath = os.path.join(base_dir, fname)
        try:
            with jsonlines.open(fpath) as reader:
                for obj in reader:
                    meta = obj.get('golden_meta', {})
                    model = meta.get('source_model', 'Unknown')
                    model_counts[model] += 1

                    trace = obj.get('new_trace', obj.get('original_trace', {}))
                    turns = trace.get('trace', [])
                    model_turns[model].append(len(turns))

                    # Compute total trace length (sum of all message lengths)
                    total_length = 0
                    for t in turns:
                        content = t.get('content', '')
                        if isinstance(content, dict):
                            content = json.dumps(content)
                        total_length += len(str(content))
                    model_total_lengths[model].append(total_length)

                    # Compute average message length per turn
                    for t in turns:
                        content = t.get('content', '')
                        if isinstance(content, dict):
                            content = json.dumps(content)
                        model_turn_lengths[model].append(len(str(content)))

                    user_query = trace.get('user_query', None)
                    if user_query:
                        unique_queries.add(user_query.strip())
        except Exception as e:
            print(f"Error reading {fpath}: {e}")

    print("=== Sample Count per Source Model ===")
    for model, count in model_counts.items():
        print(f"{model}: {count}")

    print("\n=== Average Turns per Source Model ===")
    for model, turns in model_turns.items():
        if turns:
            avg_turns = sum(turns) / len(turns)
            min_turns = min(turns)
            max_turns = max(turns)
            print(f"{model}: avg={avg_turns:.2f}, min={min_turns}, max={max_turns}, samples={len(turns)}")

    print("\n=== Turn Length Distribution per Source Model ===")
    for model, lengths in model_turn_lengths.items():
        if lengths:
            avg_len = sum(lengths) / len(lengths)
            min_len = min(lengths)
            max_len = max(lengths)
            print(f"{model}: avg={avg_len:.1f}, min={min_len}, max={max_len}, samples={len(lengths)}")

    print("\n=== Average Total Trace Length per Source Model ===")
    for model, totals in model_total_lengths.items():
        if totals:
            avg_total = sum(totals) / len(totals)
            min_total = min(totals)
            max_total = max(totals)
            print(f"{model}: avg={avg_total:.1f}, min={min_total}, max={max_total}, samples={len(totals)}")

    print("\n=== Distinct BFCL Entries (Unique User Queries) ===")
    print(f"Total unique user queries: {len(unique_queries)}")

    print("\n=== Raw Entry Count per Model (0315_test) ===")
    for model, count in raw_counts.items():
        print(f"{model}: {count}")


if __name__ == '__main__':
    main()
