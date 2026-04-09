import json
import glob
import os
import argparse
import csv

# Mapping for input directories
SETTING_MAP = {
    "fine": "fine_grained_classification",
    "coarse": "coarse_grained_classification",
    "taxonomy": "binary_classification_with_taxonomy",
    "binary": "binary_classification_without_taxonomy"
}

# CONSTRAINED ORDER: This defines the CSV column sequence exactly as requested
TAXONOMY_ORDER = [
    "benign",
    "PromptInjectionIn",
    "PromptInjectionOut",
    "UserInfoLeak",
    "ApiKeyLeak",
    "DataLeak",
    "AmbiguousArg",
    "HallucinatedTool",
    "HallucinatedArgValue",
    "RedundantArg",
    "MissingTypeHint",
    "VersionConflict",
    "DescriptionMismatch"
]

def get_model_stats(model_path):
    model_results = {}

    for setting_key, setting_dir_name in SETTING_MAP.items():
        stats = {}
        target_dir = os.path.join(model_path, setting_dir_name)
        
        files = [
            (glob.glob(os.path.join(target_dir, "*_correct.json")), 'correct'),
            (glob.glob(os.path.join(target_dir, "*_wrong.json")), 'wrong')
        ]

        for file_list, label in files:
            for file_path in file_list:
                with open(file_path, 'r') as f:
                    try:
                        data = json.load(f)
                        entries = data if isinstance(data, list) else [data]
                        for entry in entries:
                            # Note: Ensure these 'mutator' strings in your JSON 
                            # match the strings in TAXONOMY_ORDER
                            cat = entry.get("mutator", "UNKNOWN")
                            if cat not in stats:
                                stats[cat] = {'correct': 0, 'wrong': 0}
                            stats[cat][label] += 1
                    except (json.JSONDecodeError, IOError):
                        continue

        setting_accs = {}
        total_correct = 0
        total_samples = 0

        for cat, counts in stats.items():
            total = counts['correct'] + counts['wrong']
            acc = (counts['correct'] / total * 100) if total > 0 else 0
            setting_accs[cat] = round(acc, 2)
            
            # For the average calculation
            total_correct += counts['correct']
            total_samples += total
        
        # Add a calculated average for the row
        setting_accs["average"] = round((total_correct / total_samples * 100), 2) if total_samples > 0 else 0
        model_results[setting_key] = setting_accs
    
    return model_results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str, required=True, help="Path to evaluation results")
    parser.add_argument("--output", type=str, default="taxonomy_summary.csv")
    args = parser.parse_args()

    if not os.path.exists(args.input_dir):
        print(f"Error: Directory {args.input_dir} does not exist.")
        return

    model_dirs = sorted([d for d in os.listdir(args.input_dir) if os.path.isdir(os.path.join(args.input_dir, d))])
    
    all_rows = []
    # Final header: Model Info + Constrained Taxonomy + Average
    fieldnames = ["Model", "Eval_Method"] + TAXONOMY_ORDER + ["average"]

    print(f"Processing {len(model_dirs)} models...")

    for model_name in model_dirs:
        model_path = os.path.join(args.input_dir, model_name)
        results = get_model_stats(model_path)

        # Ensure rows are output in a consistent setting order as well
        for setting_key in ["fine", "coarse", "taxonomy", "binary"]:
            row = {
                "Model": model_name,
                "Eval_Method": setting_key
            }
            
            setting_data = results.get(setting_key, {})
            
            # Fill in the constrained columns
            for cat in TAXONOMY_ORDER:
                # If a category is missing for a model, default to 0.0 or ""
                row[cat] = setting_data.get(cat, 0.0)
            
            row["average"] = setting_data.get("average", 0.0)
            all_rows.append(row)

    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Done! Results written to {args.output}")

if __name__ == "__main__":
    main()