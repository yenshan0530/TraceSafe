import json
import os
import copy
import sys
import shutil
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from mutation_registry import MUTATION_REGISTRY
from mutation_unit_tests.test_utils import MutationTester
from colorama import Fore, Style
from core_utils.data_loader import load_dataset

INPUT_DIR = "../../0_trace_generation/results/"
OUTPUT_DIR = "../results/raw_mutated_results"

    # Legacy load_data entirely abstracted to core_utils.data_loader

def process_json_file(json_path, base_output_dir, args):
    """Process a single JSON file and generate per-mutator outputs and report."""
    file_name = os.path.splitext(os.path.basename(json_path))[0]
    output_dir = os.path.join(base_output_dir, file_name)
    html_report = os.path.join(output_dir, f"{file_name}_report.html") if getattr(args, "html_report", False) else None

    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    except Exception as e:
        print(f"{Fore.RED}Error initializing output directory for {file_name}: {e}")
        return f"FAILED: {file_name} (Dir Init)"

    all_traces = load_dataset(json_path)
    results = {}

    if "all" in args.mutator:
        target_mutators = MUTATION_REGISTRY
    else:
        target_mutators = [m for m in MUTATION_REGISTRY if m.__class__.__name__ in args.mutator]
        if not target_mutators:
            print(f"{Fore.RED}No matching mutators found in registry for {args.mutator}.")
            return f"FAILED: {file_name} (Mutator Not Found)"

    for mutator in target_mutators:
        mutator_name = mutator.__class__.__name__
        
        file_path = os.path.join(output_dir, f"{mutator_name}.json")
        if os.path.exists(file_path) and not args.overwrite:
            print(f"{Fore.YELLOW}[{file_name}] Skipping {mutator_name}: Output already exists (-overwrite not set).")
            results[mutator_name] = "SKIPPED (Existing)"
            continue

        mutated_collection = []

        # Terminal output identifies which worker/file is being handled
        print(f"{Fore.CYAN}--- [{file_name}] Starting Mutator: {mutator_name} ---")

        for i, trace_entry in enumerate(all_traces):
            try:
                tester = MutationTester(mutator, html_path=html_report, model_name=file_name, input_dir=INPUT_DIR)
                successful_variants = tester.run_test(
                    trace_entry,
                    skip_meta=(mutator_name != "FalseSuccess")
                )
                if successful_variants:
                    mutated_collection.extend(successful_variants)
                    
                    # Save intermediate results in batches
                    if len(mutated_collection) % args.batch_size == 1 or len(mutated_collection) >= args.max_samples:
                        try:
                            with open(file_path, 'w') as jf:
                                json.dump(mutated_collection, jf, indent=4)
                        except Exception as e:
                            print(f"{Fore.RED}[{file_name} ERROR] Failed to batch-save JSON for {mutator_name}: {e}")
                    
                    if args.test_mode or len(mutated_collection) >= args.max_samples:
                        msg = "Test mode enabled" if args.test_mode else f"Collected >= {args.max_samples} samples"
                        print(f"{Fore.MAGENTA}{msg}: stopping early for {mutator_name}.")
                        mutated_collection = mutated_collection[:args.max_samples] if not args.test_mode else mutated_collection[:1]
                        break
            except Exception as e:
                print(f"   {Fore.RED}[{file_name} ERROR] Trace {i} / {mutator_name}: {e}")
                continue

        try:
            if mutated_collection:
                with open(file_path, 'w') as jf:
                    json.dump(mutated_collection, jf, indent=4)
                results[mutator_name] = f"PASSED ({len(mutated_collection)} samples)"
            else:
                results[mutator_name] = "NO_DATA"
        except Exception as e:
            print(f"{Fore.RED}[{file_name} ERROR] saving JSON for {mutator_name}: {e}")
            results[mutator_name] = "SAVE_FAILED"

    # Print summary for the specific file processed by this worker
    print("\n" + "=" * 60)
    print(f"Summary for {file_name}")
    print(f"{'MUTATION METHOD':<35} | {'RESULT/COUNT'}")
    print("=" * 60)
    for name, status in results.items():
        color = Fore.GREEN if "PASSED" in status else Fore.YELLOW
        if "FAILED" in status: color = Fore.RED
        print(f"{name:<35} | {color}{status}{Style.RESET_ALL}")
    if html_report:
        print(f"Report: {html_report}")
    print("=" * 60)

    return f"COMPLETED: {file_name}"


def run_suite_and_save_json(args):
    """Process all JSON files in the input directory using Multi-Processing."""
    if not os.path.exists(args.input_dir):
        print(f"{Fore.RED}Error: Input directory {args.input_dir} not found.")
        sys.exit(1)

    json_files = [f for f in os.listdir(args.input_dir) if f.endswith(".jsonl")]
    if not json_files:
        print(f"{Fore.YELLOW}No JSON files found in {args.input_dir}.")
        return

    print(f"{Style.BRIGHT}{Fore.MAGENTA}>>> Launching Multi-Process Suite with {args.max_workers} workers...")

    # Initialize the Process Pool
    with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
        # Create a dictionary of future objects mapped to filenames
        futures = {
            executor.submit(process_json_file, os.path.join(args.input_dir, jf), args.output_dir, args): jf 
            for jf in json_files
        }

        # Handle results as they complete
        for future in as_completed(futures):
            filename = futures[future]
            try:
                result_msg = future.result()
                print(f"{Fore.GREEN}{Style.BRIGHT}Worker {result_msg}")
            except Exception as e:
                print(f"{Fore.RED}Critical Error processing file {filename}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run mutation unit tests on trace datasets.")
    parser.add_argument("--input_dir", type=str, default=INPUT_DIR, help="Input directory containing JSONL files")
    parser.add_argument("--output_dir", type=str, default=OUTPUT_DIR, help="Output base directory")
    parser.add_argument("--mutator", nargs="+", default=["all"], help="Name(s) of specific mutator classes to run (e.g., VersionConflict AmbiguousArg) or 'all'")
    parser.add_argument("--test-mode", action="store_true", help="Stop generating after one successful variant per mutator")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files for the targeted mutator(s)")
    parser.add_argument("--max_workers", type=int, default=64, help="Maximum number of worker processes")
    parser.add_argument("--max_samples", type=int, default=10, help="Maximum number of successful variants to collect per mutator (default: 10)")
    parser.add_argument("--batch_size", type=int, default=10, help="Frequency of saving output JSON during generation (default: 10)")
    parser.add_argument("--html-report", action="store_true", dest="html_report", help="Generate an HTML diff report")
    args = parser.parse_args()

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        
    run_suite_and_save_json(args)