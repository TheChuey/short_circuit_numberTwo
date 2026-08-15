"""
build/composition.py
====================

THE COMPOSITION ROOT (the app's single wiring point)
----------------------------------------------------

Every class in build/class_definition.py knows ONE job and takes its
dependencies explicitly. The connections are made HERE, in one visible place:

    ModelStore -> ModelSelector -> ModelContext -> ChatBackend

This module builds the shared singletons the whole process uses and exposes
`ask_llm`, the plain-text backend that LLMClient (and app/tools/tools.py)
receive via constructor injection. Because the wiring lives in its own module,
build/class_definition.py stays a pure library: classes can be built, tested
and reused independently.

Import graph (one direction, no cycles):
    build.composition -> build.class_definition -> stdlib + ollama
    app.tools.tools   -> build.composition
    app.agents.chat_bot_agent -> build.composition + build.class_definition

Public surface:
    model_store      ModelStore    (reads config/models.json)
    model_selector   ModelSelector (picks the winning model id)
    model_context    ModelContext  (safe num_ctx, capped)
    chat_backend     ChatBackend   (orchestrates the call to Ollama)
    ask_llm(prompt, model=None) -> str   (bound ChatBackend.ask_llm)
"""

from build.class_definition import (
    ChatBackend,
    ModelContext,
    ModelSelector,
    ModelStore,
)

# ModelStore has NO dependencies: it only reads config/models.json.
# Public surface: .config_model() -> str | None  (first configured model id).

model_store: ModelStore = ModelStore()

# ModelSelector needs a ModelStore to read the configured id when no explicit
# model was passed. Its ._resolve_model() is called once at the top of every
# ChatBackend.ask_llm() call (i.e. every POST /api/chat request).

model_selector: ModelSelector = ModelSelector(model_store=model_store)

# ModelContext has NO dependencies: it asks Ollama about the model's context
# window itself.
# Public surface: ._context_window(model: str) -> int | None  (capped num_ctx).

model_context: ModelContext = ModelContext()

# ChatBackend is the orchestrator / terminal step: it pulls the winning model
# id from the selector, the safe num_ctx from the context helper, then calls
# ollama.chat (retrying once on an empty reply).
# Public surface: .ask_llm(prompt: str, model: str | None) -> str.

chat_backend: ChatBackend = ChatBackend(
    selector=model_selector,
    context=model_context,
)

# ask_llm is the module-level backend the app imports. It is injected into
# LLMClient (see build/class_definition.py) and re-exported by
# app/tools/tools.py so the public name is unchanged. Signature:
#     ask_llm(prompt: str, model: str | None = None) -> str

ask_llm = chat_backend.ask_llm
