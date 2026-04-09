import os
import json
import jsonlines
import statistics
import csv
import re

def get_mutation_index(obj):
    """Parse the trace index where the mutation occurred from the difference field."""
    diff = obj.get('difference', {})
    if not diff:
        return -1
    
    # Search for strings similar to root['trace'][31]
    for key in diff.get('iterable_item_added', {}).keys():
        match = re.search(r'trace\]\[(\d+)\]', key)
        if match:
            return int(match.group(1))
    return -1

def analyze_entry(obj):
    """Analyze a single entry's tools, length, and mutation point."""
    # Prioritize analyzing the mutated trace
    trace_wrapper = obj.get('new_trace', obj.get('original_trace', {}))
    turns = trace_wrapper.get('trace', [])
    if not turns:
        return None

    # 1. Statistics on Unique Tools (find items with agent role and dict content)
    tools_used = set()
    for t in turns:
        content = t.get('content')
        if t.get('role') == 'agent' and isinstance(content, dict):
            tool_name = content.get('name')
            if tool_name:
                tools_used.add(tool_name)

    # 1.5 Calculate total tool count in the tools list
    tool_list = trace_wrapper.get('tool_lists', [])
    total_tools = len(tool_list)

    # 2. Get mutation point
    mutation_step = get_mutation_index(obj)

    # 3. Calculate Message Length
    message_lengths = [len(json.dumps(t.get('content', ''))) for t in turns]
    total_length = sum(message_lengths)
    
    # 4. Calculate Payload Overhead
    overhead = 0
    if 'new_trace' in obj and 'original_trace' in obj:
        orig_turns = obj['original_trace'].get('trace', [])
        orig_len = sum(len(json.dumps(t.get('content', ''))) for t in orig_turns)
        overhead = total_length - orig_len

    return {
        'turn_count': len(turns),
        'total_length': total_length,
        'unique_tools': len(tools_used),
        'total_tools': total_tools,
        'mutation_step': mutation_step,
        'payload_overhead': overhead
    }

def analyze_file(file_path):
    """Analyze file and compute aggregate statistics, handling standard deviation padding."""
    entries = []
    try:
        with jsonlines.open(file_path) as reader:
            for obj in reader:
                res = analyze_entry(obj)
                if res:
                    entries.append(res)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

    if not entries:
        return None

    def safe_stats(data_list):
        if not data_list: return 0, 0
        avg = statistics.mean(data_list)
        # If there is only one data point, standard deviation is set to the mean (padding as required)
        std = statistics.stdev(data_list) if len(data_list) > 1 else avg
        return avg, std

    avg_turns, std_turns = safe_stats([e['turn_count'] for e in entries])
    avg_len, std_len = safe_stats([e['total_length'] for e in entries])
    avg_tools, _ = safe_stats([e['unique_tools'] for e in entries])
    avg_total_tools, _ = safe_stats([e['total_tools'] for e in entries])
    
    m_steps = [e['mutation_step'] for e in entries if e['mutation_step'] >= 0]
    avg_m_step = statistics.mean(m_steps) if m_steps else 0
    
    avg_overhead = statistics.mean([e['payload_overhead'] for e in entries])

    return {
        'file': os.path.basename(file_path),
        'num_entries': len(entries),
        'avg_turns': round(avg_turns, 2),
        'std_turns': round(std_turns, 2),
        'avg_len': round(avg_len, 2),
        'std_len': round(std_len, 2),
        'avg_tools': round(avg_tools, 2),
        'avg_total_tools': round(avg_total_tools, 2),
        'avg_m_step': round(avg_m_step, 2),
        'avg_overhead': round(avg_overhead, 2)
    }

def main():
    # Adjust path according to your environment
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../results/golden_collection_categories'))
    
    results = []
    if not os.path.exists(base_dir):
        print(f"Directory not found: {base_dir}")
        return

    for fname in sorted(os.listdir(base_dir)):
        if fname.endswith('.jsonl'):
            res = analyze_file(os.path.join(base_dir, fname))
            if res:
                results.append(res)

    if not results:
        return

    # Calculate overall aggregates
    total_entries = sum(r['num_entries'] for r in results)
    overall_avg_turns = statistics.mean(r['avg_turns'] for r in results)
    overall_avg_len = statistics.mean(r['avg_len'] for r in results)
    overall_avg_tools = statistics.mean(r['avg_tools'] for r in results)
    overall_avg_total_tools = statistics.mean(r['avg_total_tools'] for r in results)
    overall_avg_m_step = statistics.mean(r['avg_m_step'] for r in results)
    overall_avg_overhead = statistics.mean(r['avg_overhead'] for r in results)

    # Output CSV
    csv_path = 'trace_safe_stats_fixed.csv'
    fieldnames = ['file', 'num_entries', 'avg_turns', 'std_turns', 'avg_len', 'std_len', 'avg_tools', 'avg_m_step', 'avg_overhead']
    fieldnames.insert(7, 'avg_total_tools')
    
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
        
        # Pad AGGREGATED row with average values
        writer.writerow({
            'file': 'OVERALL_AGGREGATED',
            'num_entries': total_entries,
            'avg_turns': round(overall_avg_turns, 2),
            'std_turns': round(overall_avg_turns, 2),
            'avg_len': round(overall_avg_len, 2),
            'std_len': round(overall_avg_len, 2),
            'avg_tools': round(overall_avg_tools, 2),
            'avg_total_tools': round(overall_avg_total_tools, 2),
            'avg_m_step': round(overall_avg_m_step, 2),
            'avg_overhead': round(overall_avg_overhead, 2)
        })

    print(f"Statistics generated: {csv_path}")

if __name__ == '__main__':
    main()
