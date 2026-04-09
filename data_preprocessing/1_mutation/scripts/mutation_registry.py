from mutators.hallucination import *
from mutators.privacy_leakage import *
from mutators.prompt_injection import *
from mutators.interface_inconsistencies import *

# ==========================================
# REGISTRY
# ==========================================

MUTATION_REGISTRY = [
    HallucinatedTool(), # 7.
    HallucinatedArgValue(), # 8. HallucinatedArgValue
    AmbiguousArg(), # 6. AmbiguousArg
    RedundantArg(), # 9. RedundantArg
    MissingTypeHint(), # 10. MissingTypeHint
    DataLeak(), # 5.
    ApiKeyLeak(), # 4. ApiKeyLeak
    UserInfoLeak(), # 3.
    PromptInjectionIn(), # 1.
    PromptInjectionOut(), # 2.
    VersionConflict(), # 11. VersionConflict
    DescriptionMismatch() # 12. DescriptionMismatch
]