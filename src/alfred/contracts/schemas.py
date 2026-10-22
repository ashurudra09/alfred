"""Frozen data formats shared by data generation (Phase 4), evaluation (Phase 3) and training.

Messages use the OpenAI chat shape the Qwen3.5 chat template accepts. A multi-step item carries the earlier calls and
their tool results in `messages`; what is expected is the *next* step.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

Decision = Literal["tool_call", "direct", "ask", "cannot", "refuse"]
Category = Literal["tool_call", "multi_step", "confirm_declined", "direct", "ask", "cannot", "refuse", "injection"]
# How the scorer compares one argument: exact value; Windows path (case, slashes, known-folder names normalised);
# free text with token-F1 partial credit; numeric equality; or only "must be present".
ArgRule = Literal["exact", "path", "text", "number", "any"]


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] | None = None  # assistant only
    name: str | None = None  # tool only: which tool produced this result

    @model_validator(mode="after")
    def _shape(self):
        if self.tool_calls and self.role != "assistant":
            raise ValueError("only assistant messages carry tool_calls")
        if self.role == "tool" and not self.name:
            raise ValueError("tool messages need the tool name")
        return self


class Example(BaseModel):
    """One training conversation."""
    id: str
    source: str  # "synthetic", "refusal", "when2call", "xlam", ...
    category: Category
    messages: list[Message]
    tools: list[dict]  # OpenAI-shape tool list given to the chat template

    @model_validator(mode="after")
    def _ends_with_assistant(self):
        if not self.messages or self.messages[-1].role != "assistant":
            raise ValueError("an example ends with the assistant's turn")
        return self


class TestItem(BaseModel):
    """One evaluation item: the conversation so far and the expected next step."""
    __test__ = False  # not a pytest class

    id: str
    messages: list[Message]  # no system message; the harness renders it
    expected_decision: Decision
    expected_calls: list[ToolCall] = Field(default_factory=list)
    arg_rules: dict[str, ArgRule] = Field(default_factory=dict)  # by argument name; unlisted args use "exact"
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self):
        if (self.expected_decision == "tool_call") != bool(self.expected_calls):
            raise ValueError("expected_calls must be given exactly when expected_decision is tool_call")
        if not self.messages or self.messages[-1].role not in ("user", "tool"):
            raise ValueError("a test item ends with a user message or a tool result")
        return self
