import copy
import json
from router import llm_judge, llm_generate
import random

class BaseMutation:
    name = "base"
    category = "BASE"
    # Mutation points
    mutates_query = False
    mutates_tool_list = False
    mutates_tool_trace = False

    def judge(self, trace_data, target_tool_name):
        """
        Specialized LLM-based judge for this specific mutation.
        Returns {'suitable': bool, 'reasoning': str}
        """
        return {"suitable": False, "reasoning": "Not implemented"}

    def perform(self, trace_data, target_tool_name, reasoning=""):
        """
        Executes the mutation logic.
        """
        return trace_data
    
    def mutate(self, trace_data, target_tool_name):
        """
        Input: Original trace, target tool
        Output: Dictionary {
            "mutated_trace": dict,
            "rationale": str,
            "metadata": dict (optional internal details)
        } 
        OR None (if mutation is not suitable or failed)
        """
        raise NotImplementedError