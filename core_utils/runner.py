import os
import csv
import json
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from colorama import Fore

from core_utils.schema import TraceEntry
from core_utils.data_loader import load_dataset, discover_json_files

class BaseEvaluationRunner:
    """
    An abstract runner that strictly standardizes how pipeline evaluations load data,
    chunk payloads via ThreadPoolExecutor, save outputs concurrently, and print CSV summaries.
    Subclasses only need to implement `evaluate_sample()`.
    """
    def __init__(self, max_workers: int = 64, num_samples: int = 0):
        self.max_workers = max_workers
        self.num_samples = num_samples
        
    def evaluate_sample(self, entry: TraceEntry, setting: str, client, model_name: str, **kwargs):
        """
        MUST return a tuple of: (mutator_name, is_success_boolean, result_data_dict)
        If explicitly skipped/errored, return `None` for is_success_boolean.
        """
        raise NotImplementedError("Subclasses must implement evaluate_sample.")
        
    def run_benchmark(self, input_dirs: list, output_dir: str, settings: list, client, model_name: str, csv_headers: list = None, **kwargs):
        out_dir_path = Path(output_dir)
        out_dir_path.mkdir(parents=True, exist_ok=True)
        
        json_paths = discover_json_files(input_dirs)
        if not json_paths:
            print(f"{Fore.RED}No input files found in provided directories: {input_dirs}")
            return
            
        stats = {s: {} for s in settings}

        for file_path in json_paths:
            all_correct = {s: [] for s in settings}
            all_wrong = {s: [] for s in settings}
            original_filename = file_path.stem
            
            print(f"\n{Fore.YELLOW}Processing File: {file_path}")
            
            entries = load_dataset(file_path)
            if self.num_samples > 0:
                entries = entries[:self.num_samples]
                
            for setting in settings:
                print(f"{Fore.CYAN}>>> Setting {setting}...")
                setting_output_dir = out_dir_path / setting
                setting_output_dir.mkdir(parents=True, exist_ok=True)
                
                out_base = setting_output_dir / original_filename
                
                if Path(f"{out_base}_correct.json").exists() and Path(f"{out_base}_wrong.json").exists():
                    print(f"{Fore.YELLOW}Skipping {out_base} (Already Processed)")
                    continue
                    
                tasks = []
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    for entry in entries:
                        mutator = entry.mutator_name
                        if mutator not in stats[setting]: 
                            stats[setting][mutator] = {"total": 0, "correct": 0}
                            
                        stats[setting][mutator]["total"] += 1
                        tasks.append(executor.submit(self.evaluate_sample, entry, setting, client, model_name, **kwargs))

                    for future in tqdm(as_completed(tasks), total=len(tasks), desc=f"{original_filename} ({setting})"):
                        try:
                            mutator, success, enriched = future.result()
                            if success is None:
                                stats[setting][mutator]["total"] -= 1
                            elif success:
                                stats[setting][mutator]["correct"] += 1
                                all_correct[setting].append(enriched)
                            else:
                                all_wrong[setting].append(enriched)
                        except Exception as e:
                            print(f"{Fore.RED}Unhandled Thread Exception: {e}")
                            
                with open(f"{out_base}_correct.json", "w") as f: json.dump(all_correct[setting], f, indent=4)
                with open(f"{out_base}_wrong.json", "w") as f: json.dump(all_wrong[setting], f, indent=4)
                
        self._write_csv_summary(out_dir_path, model_name, settings, stats, csv_headers)

    def _write_csv_summary(self, output_dir: Path, model_name: str, settings: list, stats: dict, custom_headers: list = None):
        csv_path = output_dir / "summary_results.csv"
        file_exists = csv_path.is_file()
        
        # Default Headers
        if not custom_headers:
            custom_headers = ["Timestamp", "Model Name", "Setting", "Mutator", "Total", "Correct", "Accuracy (%)"]
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(csv_path, "a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=custom_headers)
            if not file_exists:
                writer.writeheader()

            for s in settings:
                for mutator, data in stats[s].items():
                    if data["total"] > 0:
                        acc = (data["correct"] / data["total"] * 100)
                        writer.writerow({
                            "Timestamp": timestamp,
                            "Model Name": model_name,
                            "Setting": s,
                            "Mutator": mutator,
                            "Total": data["total"],
                            "Correct": data["correct"],
                            "Accuracy (%)": round(acc, 2)
                        })
