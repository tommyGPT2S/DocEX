import importlib

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "docex.processors.llm",
        "docex.processors.rag",
        "docex.processors.kb",
        "docex.prompts",
        "docex.services.generic_knowledge_base_service",
    ],
)
def test_removed_llm_rag_kb_modules_hard_fail(module_name):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)
