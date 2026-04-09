from typing import Dict, Any

class TraceEntry(dict):
    """
    A lightweight dictionary subclass acting as a typed schema for mutated trace logs.
    Ensures safe access to common nested keys without strictly throwing errors on 
    missing non-standard fields.
    """
    
    @property
    def mutator_name(self) -> str:
        return self.get("mutation_metadata", {}).get("mutator_name", "Unknown")
        
    @property
    def target_tool(self) -> str:
        return self.get("mutation_metadata", {}).get("target_tool", "Unknown")
        
    @property
    def mutation_category(self) -> str:
        return self.get("mutation_category", "Unknown")
        
    @property
    def original_trace(self) -> Any:
        return self.get("original_trace", {})
        
    @property
    def new_trace(self) -> Any:
        return self.get("new_trace", {})

    @property
    def is_benign(self) -> bool:
        mut = self.mutator_name.lower()
        return mut == "falsesuccess" or "benign" in mut
