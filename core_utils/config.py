import os
from pathlib import Path

# Resolve the Root of the TraceSafe repo
REPO_ROOT = Path(__file__).resolve().parent.parent

# Define central paths based universally off the repo root
DATA_PREPROCESSING_DIR = REPO_ROOT / "data_preprocessing"
EVALUATION_DIR = REPO_ROOT / "evaluation"

TRACE_GEN_RESULTS_DIR = DATA_PREPROCESSING_DIR / "0_trace_generation" / "results"
MUTATION_RESULTS_DIR = DATA_PREPROCESSING_DIR / "1_mutation" / "results"
GOLDEN_COLLECTION_DIR = MUTATION_RESULTS_DIR / "golden_collection_categories"

EVAL_RESULTS_DIR = EVALUATION_DIR / "results"

def get_env_var(key: str, default=None):
    """Safely fetch an environment variable or return default."""
    return os.environ.get(key, default)
