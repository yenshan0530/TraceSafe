"""
Download the TraceSafe-Bench golden collection from Hugging Face into the
local path expected by core_utils.config.

Usage:
    python data_preprocessing/download_data.py

Requirements:
    pip install huggingface_hub
    The dataset is gated; run `huggingface-cli login` once and request access
    at https://huggingface.co/datasets/CyCraftAI/TraceSafe before downloading.
"""
from pathlib import Path
from huggingface_hub import snapshot_download

REPO_ID = "CyCraftAI/TraceSafe"
TARGET = Path(__file__).resolve().parent.parent / "data"


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=REPO_ID,
        repo_type="dataset",
        local_dir=str(TARGET),
        allow_patterns=["golden_*.jsonl", "README.md"],
    )
    print(f"downloaded {REPO_ID} → {TARGET}")


if __name__ == "__main__":
    main()
