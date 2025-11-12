"""Message history with token tracking and prompt caching."""

from typing import Any


class MessageHistory:
    """Manages chat history with token tracking and context management."""

    def __init__(
        self,
        model: str,
        system: str,
        context_window_tokens: int,
        client: Any,
        enable_caching: bool = True,
    ):
        self.model = model
        self.system = system
        self.context_window_tokens = context_window_tokens
        self.messages: list[dict[str, Any]] = []
        self.total_tokens = 0
        self.enable_caching = enable_caching
        self.message_tokens: list[tuple[int, int]] = (
            []
        )  # List of (input_tokens, output_tokens) tuples
        self.client = client

        # set initial total tokens to system prompt
        try:
            system_token = (
                self.client.messages.count_tokens(
                    model=self.model,
                    system=self.system,
                    messages=[{"role": "user", "content": "test"}],
                ).input_tokens
                - 1
            )

        except Exception:
            system_token = len(self.system) / 4

        self.total_tokens = system_token

    async def add_message(
        self,
        role: str,
        content: str | list[dict[str, Any]],
        usage: Any | None = None,
    ):
        """Add a message to the history and track token usage."""
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        elif isinstance(content, list):
            # Convert Pydantic objects to dicts if necessary
            converted_content = []
            for block in content:
                if isinstance(block, dict):
                    converted_content.append(block)
                elif hasattr(block, "model_dump"):
                    converted_content.append(block.model_dump())
                elif hasattr(block, "dict"):
                    converted_content.append(block.dict())
                else:
                    converted_content.append(block)
            content = converted_content

        message = {"role": role, "content": content}
        self.messages.append(message)

        if role == "assistant" and usage:
            total_input = (
                usage.input_tokens
                + getattr(usage, "cache_read_input_tokens", 0)
                + getattr(usage, "cache_creation_input_tokens", 0)
            )
            output_tokens = usage.output_tokens

            current_turn_input = total_input - self.total_tokens
            self.message_tokens.append((current_turn_input, output_tokens))
            self.total_tokens += current_turn_input + output_tokens

    def truncate(self) -> None:
        """Remove oldest messages when context window limit is exceeded."""
        if self.total_tokens <= self.context_window_tokens:
            return

        TRUNCATION_NOTICE_TOKENS = 25
        TRUNCATION_MESSAGE = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "[Earlier history has been truncated.]",
                }
            ],
        }

        def remove_message_pair():
            self.messages.pop(0)
            self.messages.pop(0)

            if self.message_tokens:
                input_tokens, output_tokens = self.message_tokens.pop(0)
                self.total_tokens -= input_tokens + output_tokens

        while (
            self.message_tokens
            and len(self.messages) >= 2
            and self.total_tokens > self.context_window_tokens
        ):
            remove_message_pair()

            if self.messages and self.message_tokens:
                original_input_tokens, original_output_tokens = (
                    self.message_tokens[0]
                )
                self.messages[0] = TRUNCATION_MESSAGE
                self.message_tokens[0] = (
                    TRUNCATION_NOTICE_TOKENS,
                    original_output_tokens,
                )
                self.total_tokens += (
                    TRUNCATION_NOTICE_TOKENS - original_input_tokens
                )

    def format_for_api(self) -> list[dict[str, Any]]:
        """Format messages for Claude API with optional caching."""
        result = []
        
        for m in self.messages:
            # Always include messages that have content
            # This includes tool_use blocks which are required for proper API calls
            if m["content"]:
                result.append({"role": m["role"], "content": m["content"]})
        
        # Apply caching to the last message if enabled
        if self.enable_caching and result:
            last_message = result[-1]
            if last_message["role"] == "user":
                cached_content = []
                for block in last_message["content"]:
                    if isinstance(block, dict):
                        cached_content.append({**block, "cache_control": {"type": "ephemeral"}})
                    else:
                        # For Pydantic objects, convert to dict first
                        block_dict = block.model_dump() if hasattr(block, "model_dump") else block.dict()
                        cached_content.append({**block_dict, "cache_control": {"type": "ephemeral"}})
                last_message["content"] = cached_content
        
        return result
