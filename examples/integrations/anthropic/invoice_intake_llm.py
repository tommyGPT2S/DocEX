"""
Claude adapter for the DocEX invoice intake (copy-adapt example).

The intake's LLM tier (:class:`docex.intake.extractors.llm.LLMExtractor`) takes a
provider-neutral ``llm_fn`` - a callable that maps a prompt string to a JSON
string. This module builds that callable on top of the Anthropic SDK so the
intake stays free of any hard provider dependency.

It is intentionally an example, not core API. Copy it into your project and
adapt the model, credentials, and error handling to your needs.

    from docex.intake import InvoiceIntakePipeline
    from examples.integrations.anthropic.invoice_intake_llm import make_claude_llm_fn

    pipeline = InvoiceIntakePipeline(llm_fn=make_claude_llm_fn())
    outcome = await pipeline.process_pdf("invoice.pdf", ground_truth_store)

Install the SDK first: ``pip install anthropic``.
"""

from __future__ import annotations

from typing import Optional

try:
    import anthropic
except ImportError as exc:  # pragma: no cover - example module
    raise ImportError("This example requires the 'anthropic' package: pip install anthropic") from exc

from docex.intake.extractors.llm import LLMFn

# The intake calls the LLM only as a last resort, on a handful of unresolved or
# disputed fields, so the request is small. Opus 4.8 is the default for accuracy
# on messy layouts; switch to "claude-haiku-4-5" or "claude-sonnet-4-6" if you
# would rather trade a little accuracy for lower cost on this fallback path.
_DEFAULT_MODEL = "claude-opus-4-8"
_MAX_TOKENS = 4096


def make_claude_llm_fn(
    model: str = _DEFAULT_MODEL,
    client: Optional["anthropic.Anthropic"] = None,
) -> LLMFn:
    """Build an ``llm_fn`` for the intake backed by the Anthropic Messages API.

    Args:
        model: The Claude model id. Defaults to ``claude-opus-4-8``.
        client: An existing ``anthropic.Anthropic`` client, or ``None`` to build
            one from the ``ANTHROPIC_API_KEY`` environment variable.

    Returns:
        A callable suitable for ``InvoiceIntakePipeline(llm_fn=...)``.
    """
    client = client or anthropic.Anthropic()

    def llm_fn(prompt: str) -> str:
        message = client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if block.type == "text")

    return llm_fn
