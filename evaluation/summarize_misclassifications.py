import argparse
import json
import os
from collections import Counter

def main():
    parser = argparse.ArgumentParser(description="Summarize misclassifications.")
    parser.add_argument("--model", type=str, default="Llama-3B", help="Model name (e.g., Llama-3B)")
    parser.add_argument("--categories", type=str, nargs="+", default=[
        "AmbiguousArg", "VersionConflict", "HallucinatedArgValue", 
        "DescriptionMismatch", "HallucinatedTool", "RedundantArg", 
        "MissingTypeHint", "UserInfoLeak", "ApiKeyLeak", "DataLeak", 
        "PromptInjectionIn", "PromptInjectionOut"
    ], help="List of categories to summarize")
    
    args = parser.parse_args()
    
    output_dir = f"results/{args.model}/fine_grained_classification"
    categories = args.categories

    for cat in categories:
        filepath = os.path.join(output_dir, f"golden_{cat}_wrong.json")
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
            
            verdicts = [item.get("model_verdict", "").strip() for item in data]
            counter = Counter(verdicts)
            print(f"\n--- {cat} Misclassifications ---")
            for verdict, count in counter.most_common(5):
                print(f"{count} times: {verdict}")
        else:
            print(f"File not found: {filepath}")

if __name__ == "__main__":
    main()
