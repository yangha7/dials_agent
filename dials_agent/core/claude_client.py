"""
Claude API client for the DIALS AI Agent.

This module provides a wrapper around multiple LLM APIs for interacting with
language models, including tool/function calling support.

Supported providers:
  - CBORG (Claude at Berkeley) — OpenAI-compatible
  - OpenAI — native OpenAI API
  - Google Gemini — OpenAI-compatible
  - Anthropic Claude — native Anthropic API
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..config import Settings, get_settings
from ..skills import SkillRegistry, create_default_registry
from .base_tools import get_base_tools
from .prompts import get_system_prompt, get_dynamic_context, get_system_prompt_with_context
from .tools import discover_data_files

logger = logging.getLogger(__name__)

# Import API clients conditionally
try:
    from anthropic import Anthropic, APIError as AnthropicAPIError, APIConnectionError as AnthropicConnectionError, RateLimitError as AnthropicRateLimitError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AnthropicAPIError = Exception
    AnthropicConnectionError = Exception
    AnthropicRateLimitError = Exception

try:
    from openai import OpenAI, APIError as OpenAIAPIError, APIConnectionError as OpenAIConnectionError, RateLimitError as OpenAIRateLimitError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAIAPIError = Exception
    OpenAIConnectionError = Exception
    OpenAIRateLimitError = Exception


@dataclass
class Message:
    """Represents a message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class TokenUsage:
    """Token counts for one API call or an accumulated session total."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0  # tokens written to cache (Anthropic only)
    cache_read_tokens: int = 0      # tokens served from cache (Anthropic only)

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    def __iadd__(self, other: "TokenUsage") -> "TokenUsage":
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.cache_creation_tokens += other.cache_creation_tokens
        self.cache_read_tokens += other.cache_read_tokens
        return self


@dataclass
class AgentResponse:
    """Response from the agent."""
    message: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    raw_response: Optional[dict] = None
    usage: Optional[TokenUsage] = None  # per-turn usage (all rounds combined)


class ClaudeClient:
    """
    Client for interacting with LLM APIs.
    
    Supports both native Anthropic API and OpenAI-compatible APIs
    (CBORG, OpenAI, Gemini). Handles conversation management, tool
    calling, and error handling.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        working_directory: str = ".",
        existing_files: Optional[list[str]] = None,
        registry: Optional[SkillRegistry] = None,
    ):
        """
        Initialize the LLM client.

        Args:
            settings: Application settings (uses global settings if not provided)
            working_directory: Current working directory for context
            existing_files: List of existing DIALS files for context
            registry: Skill registry to compose the system prompt and tools
                from. Defaults to a registry with every skill registered;
                each skill's full guidance is still loaded on demand via
                the `load_skill` tool rather than injected up front.
        """
        self.settings = settings or get_settings()
        self.working_directory = working_directory
        self.existing_files = existing_files or []
        self.registry = registry or create_default_registry()
        
        # Resolve provider using auto-detection
        self.provider = self.settings.get_resolved_provider()
        self.api_type = self.settings.get_api_type()
        self.model = self.settings.get_resolved_model()
        
        if not self.settings.validate_api_key():
            provider_name = self.settings.get_provider_display_name()
            raise ValueError(
                f"No API key configured for {provider_name}. "
                f"Set the appropriate API key in your .env file. "
                f"See .env.example for configuration options."
            )
        
        # Initialize the appropriate client
        if self.api_type == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Run: pip install openai")
            
            api_key = self.settings.get_resolved_api_key()
            base_url = self.settings.get_resolved_base_url()
            
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
            logger.info(
                f"Using {self.settings.get_provider_display_name()} "
                f"(OpenAI-compatible) at {base_url} with model {self.model}"
            )
        else:
            # Native Anthropic API
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            self.client = Anthropic(api_key=self.settings.get_resolved_api_key())
            logger.info(f"Using native Anthropic API with model {self.model}")
        
        self.conversation_history: list[dict] = []
        self.tools = get_base_tools() + self.registry.get_all_tools()
        self.openai_tools = self._convert_tools_to_openai_format()

        # Cache the static system prompt — computed once; only changes if tutorials change
        self._static_system_prompt: str = get_system_prompt(self.registry)

        # Cached data file discovery — refreshed in update_context()
        self._data_files: list[dict] = discover_data_files(
            self.working_directory,
            data_directory=self.settings.data_directory
        )

        # Cumulative token usage for the whole session
        self.session_usage: TokenUsage = TokenUsage()

        # Keep backward compatibility
        self.api_provider = self.api_type
        
    def _convert_tools_to_openai_format(self) -> list[dict]:
        """Convert Anthropic tool format to OpenAI function format."""
        openai_tools = []
        for tool in self.tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools
    
    def _get_dynamic_context(self) -> str:
        """Return the small dynamic context block (working dir, files). Not cached."""
        return get_dynamic_context(
            self.working_directory,
            self.existing_files,
            self._data_files,
            data_directory=self.settings.data_directory,
        )

    def update_context(
        self,
        working_directory: Optional[str] = None,
        existing_files: Optional[list[str]] = None
    ):
        """
        Update the context for the conversation.

        Also refreshes the data-file discovery cache so the next API call
        sees the latest files without paying discovery cost on every turn.
        """
        if working_directory is not None:
            self.working_directory = working_directory
        if existing_files is not None:
            self.existing_files = existing_files
        # Refresh data file cache whenever context changes
        self._data_files = discover_data_files(
            self.working_directory,
            data_directory=self.settings.data_directory,
        )
    
    def clear_history(self):
        """Clear the conversation history and reset session token counters."""
        self.conversation_history = []
        self.session_usage = TokenUsage()

    # Maximum chars kept per tool result in history after Claude has responded.
    # Large log files are trimmed to this size so they don't balloon the context
    # on every subsequent turn.  The current turn always gets the full content.
    TOOL_RESULT_HISTORY_LIMIT = 2000

    def _trim_history_tool_results(self) -> None:
        """
        Trim large tool results already stored in conversation history.

        Called after each tool-call round, once Claude has processed the full
        results and we no longer need them verbatim.  Keeps the most recent
        tool-result message intact (Claude may still need it) and truncates
        any earlier ones that exceed TOOL_RESULT_HISTORY_LIMIT chars.
        """
        # Find indices of all user messages that contain tool results
        tool_result_indices = [
            i for i, msg in enumerate(self.conversation_history)
            if msg.get("role") == "user"
            and isinstance(msg.get("content"), list)
            and any(
                isinstance(item, dict) and item.get("type") == "tool_result"
                for item in msg["content"]
            )
        ]

        # Leave the most recent one untouched — trim all earlier ones
        for idx in tool_result_indices[:-1]:
            msg = self.conversation_history[idx]
            for item in msg["content"]:
                if not isinstance(item, dict) or item.get("type") != "tool_result":
                    continue
                content = item.get("content", "")
                if isinstance(content, str) and len(content) > self.TOOL_RESULT_HISTORY_LIMIT:
                    kept = content[:self.TOOL_RESULT_HISTORY_LIMIT]
                    dropped = len(content) - self.TOOL_RESULT_HISTORY_LIMIT
                    item["content"] = kept + f"\n[…{dropped} chars trimmed from history]"
    
    def send_message(
        self,
        user_message: str,
        tool_handler: Optional[Callable[[ToolCall], dict]] = None
    ) -> AgentResponse:
        """
        Send a message to the LLM and get a response.
        
        Args:
            user_message: The user's message
            tool_handler: Optional callback to handle tool calls
            
        Returns:
            AgentResponse containing the assistant's response and any tool calls
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            response = self._call_api()

            # Process the response
            agent_response = self._process_response(response)

            # Accumulate usage across all tool-call rounds so the caller
            # sees the total cost of the whole turn, not just the last call.
            turn_usage = TokenUsage()
            if agent_response.usage:
                turn_usage += agent_response.usage

            # Loop to handle multiple rounds of tool calls (e.g., Claude calls
            # check_workflow_status, then wants to call run_shell_command)
            max_tool_rounds = 30
            rounds = 0
            while agent_response.tool_calls and tool_handler and rounds < max_tool_rounds:
                agent_response = self._handle_tool_calls(
                    agent_response,
                    tool_handler
                )
                if agent_response.usage:
                    turn_usage += agent_response.usage
                rounds += 1

            if rounds >= max_tool_rounds:
                logger.warning(f"Reached maximum tool call rounds ({max_tool_rounds})")

            # Attach combined turn usage and update the session total
            agent_response.usage = turn_usage
            self.session_usage += turn_usage

            return agent_response
            
        except (AnthropicRateLimitError, OpenAIRateLimitError) as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise
        except (AnthropicConnectionError, OpenAIConnectionError) as e:
            logger.error(f"API connection error: {e}")
            raise
        except (AnthropicAPIError, OpenAIAPIError) as e:
            logger.error(f"API error: {e}")
            raise
    
    def _call_api(self) -> Any:
        """Make the API call (supports both Anthropic and OpenAI-compatible APIs)."""
        if self.api_type == "openai":
            return self._call_openai_api()
        else:
            return self._call_anthropic_api()
    
    def _call_anthropic_api(self) -> Any:
        """Make API call using native Anthropic API with prompt caching.

        The large static system prompt is marked with cache_control so it is
        cached after the first call (~5-minute TTL, ~10x cheaper on reads).
        Only the small dynamic context block (working dir, file list) is sent
        uncached, since it changes as the user navigates the workflow.
        """
        return self.client.messages.create(
            model=self.model,
            max_tokens=self.settings.get_resolved_max_tokens(),
            system=[
                {
                    "type": "text",
                    "text": self._static_system_prompt,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": self._get_dynamic_context(),
                },
            ],
            tools=self.tools,
            messages=self.conversation_history,
        )

    def _call_openai_api(self) -> Any:
        """Make API call using OpenAI-compatible API."""
        # OpenAI-compat APIs don't support list-form system with cache_control,
        # so concatenate static + dynamic into a single string.
        system_prompt = self._static_system_prompt + self._get_dynamic_context()
        messages = [{"role": "system", "content": system_prompt}]
        
        # Process messages in pairs to ensure tool_use/tool_result ordering
        i = 0
        while i < len(self.conversation_history):
            msg = self.conversation_history[i]
            
            if msg["role"] == "user":
                content = msg["content"]
                if isinstance(content, list):
                    # Tool results - convert to OpenAI format
                    # These must come immediately after an assistant message with tool_calls
                    for item in content:
                        if item.get("type") == "tool_result":
                            messages.append({
                                "role": "tool",
                                "tool_call_id": item["tool_use_id"],
                                "content": item["content"] if item["content"] else ""
                            })
                else:
                    messages.append({"role": "user", "content": content})
            elif msg["role"] == "assistant":
                content = msg["content"]
                tool_calls_list = []
                text_content = ""
                
                # Check if this is an OpenAI-style message with tool_calls stored
                if "_openai_tool_calls" in msg and msg["_openai_tool_calls"]:
                    # Reconstruct the assistant message with tool_calls
                    text_content = content or ""
                    for tc in msg["_openai_tool_calls"]:
                        tool_calls_list.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })
                elif isinstance(content, list):
                    # Anthropic format - convert to OpenAI
                    for block in content:
                        if hasattr(block, 'type'):
                            if block.type == "text":
                                text_content += block.text
                            elif block.type == "tool_use":
                                tool_calls_list.append({
                                    "id": block.id,
                                    "type": "function",
                                    "function": {
                                        "name": block.name,
                                        "arguments": json.dumps(block.input)
                                    }
                                })
                        elif isinstance(block, dict):
                            if block.get("type") == "text":
                                text_content += block.get("text", "")
                            elif block.get("type") == "tool_use":
                                tool_calls_list.append({
                                    "id": block["id"],
                                    "type": "function",
                                    "function": {
                                        "name": block["name"],
                                        "arguments": json.dumps(block.get("input", {}))
                                    }
                                })
                else:
                    text_content = content or ""
                
                # Build the assistant message
                msg_dict = {"role": "assistant", "content": text_content if text_content else None}
                if tool_calls_list:
                    msg_dict["tool_calls"] = tool_calls_list
                messages.append(msg_dict)
                
                # If this assistant message has tool_calls, verify the next message has tool_results
                if tool_calls_list and i + 1 < len(self.conversation_history):
                    next_msg = self.conversation_history[i + 1]
                    if next_msg["role"] == "user" and isinstance(next_msg["content"], list):
                        # Good - tool results follow, they'll be processed in next iteration
                        pass
                    else:
                        # Missing tool results - this would cause the API error
                        # Add placeholder tool results to prevent the error
                        logger.warning(f"Missing tool results after assistant tool_calls at message {i}")
                        for tc in tool_calls_list:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": json.dumps({"error": "Tool result was not recorded"})
                            })
                elif tool_calls_list and i + 1 >= len(self.conversation_history):
                    # Tool calls at end of history without results - add placeholders
                    logger.warning(f"Tool calls at end of history without results at message {i}")
                    for tc in tool_calls_list:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps({"error": "Tool result was not recorded"})
                        })
            
            i += 1
        
        return self.client.chat.completions.create(
            model=self.model,
            max_tokens=self.settings.get_resolved_max_tokens(),
            tools=self.openai_tools if self.openai_tools else None,
            messages=messages
        )
    
    def _process_response(self, response: Any) -> AgentResponse:
        """
        Process the API response into an AgentResponse.
        
        Args:
            response: Raw API response
            
        Returns:
            Processed AgentResponse
        """
        if self.api_type == "openai":
            return self._process_openai_response(response)
        else:
            return self._process_anthropic_response(response)
    
    def _process_anthropic_response(self, response: Any) -> AgentResponse:
        """Process native Anthropic API response."""
        message_content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                message_content += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    input=block.input
                ))

        # Capture token usage from the response
        usage = None
        if hasattr(response, "usage") and response.usage is not None:
            u = response.usage
            usage = TokenUsage(
                input_tokens=getattr(u, "input_tokens", 0) or 0,
                output_tokens=getattr(u, "output_tokens", 0) or 0,
                cache_creation_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
                cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            )

        # Add assistant message to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response.content
        })

        return AgentResponse(
            message=message_content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            raw_response=response,
            usage=usage,
        )
    
    def _process_openai_response(self, response: Any) -> AgentResponse:
        """Process OpenAI-compatible API response."""
        choice = response.choices[0]
        message = choice.message
        
        message_content = message.content or ""
        tool_calls = []
        
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments) if tc.function.arguments else {}
                ))
        
        # Add assistant message to history (store in a format we can convert later)
        self.conversation_history.append({
            "role": "assistant",
            "content": message_content,
            "_openai_tool_calls": message.tool_calls
        })
        
        stop_reason = "end_turn" if choice.finish_reason == "stop" else choice.finish_reason

        # Capture token usage (OpenAI-compat; no cache fields)
        usage = None
        if hasattr(response, "usage") and response.usage is not None:
            u = response.usage
            usage = TokenUsage(
                input_tokens=getattr(u, "prompt_tokens", 0) or 0,
                output_tokens=getattr(u, "completion_tokens", 0) or 0,
            )

        return AgentResponse(
            message=message_content,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            raw_response=response,
            usage=usage,
        )
    
    def _handle_tool_calls(
        self,
        agent_response: AgentResponse,
        tool_handler: Callable[[ToolCall], dict]
    ) -> AgentResponse:
        """
        Handle tool calls by executing them and continuing the conversation.
        
        Args:
            agent_response: The response containing tool calls
            tool_handler: Callback to execute tool calls
            
        Returns:
            Updated AgentResponse after tool execution
        """
        tool_results = []
        
        for tool_call in agent_response.tool_calls:
            logger.info(f"Executing tool: {tool_call.name}")
            try:
                result = tool_handler(tool_call)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps(result) if isinstance(result, dict) else str(result)
                })
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": json.dumps({"error": str(e)}),
                    "is_error": True
                })
        
        # Add tool results to history
        self.conversation_history.append({
            "role": "user",
            "content": tool_results
        })

        # Get LLM's response after tool execution
        response = self._call_api()
        result = self._process_response(response)

        # After Claude has seen the full tool results and responded, trim any
        # large results in history — they don't need to live at full size for
        # the rest of the session.
        self._trim_history_tool_results()

        return result
    
    def send_message_with_auto_tool_handling(
        self,
        user_message: str,
        tool_handler: Callable[[ToolCall], dict],
        max_iterations: int = 10
    ) -> AgentResponse:
        """
        Send a message and automatically handle all tool calls until completion.
        
        Args:
            user_message: The user's message
            tool_handler: Callback to execute tool calls
            max_iterations: Maximum number of tool call iterations
            
        Returns:
            Final AgentResponse after all tool calls are processed
        """
        response = self.send_message(user_message)
        iterations = 0
        
        while response.tool_calls and iterations < max_iterations:
            response = self._handle_tool_calls(response, tool_handler)
            iterations += 1
        
        if iterations >= max_iterations:
            logger.warning(f"Reached maximum tool call iterations ({max_iterations})")
        
        return response


def create_client(
    working_directory: str = ".",
    existing_files: Optional[list[str]] = None,
    registry: Optional[SkillRegistry] = None,
    settings: Optional[Settings] = None,
) -> ClaudeClient:
    """
    Create a new LLM client instance.

    Args:
        working_directory: Current working directory
        existing_files: List of existing DIALS files
        registry: Skill registry to use (defaults to all skills loaded)
        settings: Application settings (uses global settings if not provided)

    Returns:
        Configured ClaudeClient instance
    """
    return ClaudeClient(
        working_directory=working_directory,
        existing_files=existing_files,
        registry=registry,
        settings=settings,
    )
