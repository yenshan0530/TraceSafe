import json
import os
from pathlib import Path
from typing import List, Union
from colorama import Fore
from core_utils.schema import TraceEntry

def load_dataset(file_path: Union[str, Path]) -> List[TraceEntry]:
    """
    Robustly loads JSON or JSONL datasets containing traces and returns mapped TraceEntry arrays.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"{Fore.RED}Error: {path} not found.")
        return []
        
    entries = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return []
                
            # Safely handle pure JSON array formatting vs JSONl line-by-line dumps
            if content.startswith("["):
                raw_entries = json.loads(content)
                entries = [TraceEntry(e) for e in raw_entries if e]
            else:
                entries = [TraceEntry(json.loads(line)) for line in content.splitlines() if line.strip()]
                
    except Exception as e:
        print(f"{Fore.RED}Failed to load dataset {path}: {e}")
            
    return entries

def discover_json_files(directories: List[Union[str, Path]]) -> List[Path]:
    """Recursively discover all json/jsonl files inside a list of target directories."""
    jsonl_files = []
    for base_dir in directories:
        base_path = Path(base_dir)
        if not base_path.exists(): continue
            
        for ext in ("*.json", "*.jsonl"):
            jsonl_files.extend(list(base_path.rglob(ext)))
            
    return jsonl_files
