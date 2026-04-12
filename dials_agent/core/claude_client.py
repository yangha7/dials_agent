"""
Claude API client for the DIALS AI Agent.

This module provides a wrapper around the Anthropic API and OpenAI-compatible
APIs (like CBORG) for interacting with Claude, including tool/function calling support.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..config import Settings, get_settings
from .prompts import get_system_prompt, get_system_prompt_with_context
from .tools import get_tools, discover_data_files

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
    """Represents a tool call from Claude."""
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class AgentResponse:
    """Response from the agent."""
    message: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    raw_response: Optional[dict] = None


class ClaudeClient:
    """
    Client for interacting with Claude API.
    
    Supports both native Anthropic API and OpenAI-compatible APIs (like CBORG).
    Handles conversation management, tool calling, and error handling.
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        working_directory: str = ".",
        existing_files: Optional[list[str]] = None
    ):
        """
        Initialize the Claude client.
        
        Args:
            settings: Application settings (uses global settings if not provided)
            working_directory: Current working directory for context
            existing_files: List of existing DIALS files for context
        """
        self.settings = settings or get_settings()
        self.working_directory = working_directory
        self.existing_files = existing_files or []
        self.api_provider = self.settings.api_provider
        
        if not self.settings.validate_api_key():
            if self.api_provider == "openai":
                raise ValueError(
                    "OpenAI-compatible API key not configured. "
                    "Set OPENAI_API_KEY environment variable or in .env file."
                )
            else:
                raise ValueError(
                    "Anthropic API key not configured. "
                    "Set ANTHROPIC_API_KEY environment variable or in .env file."
                )
        
        # Initialize the appropriate client
        if self.api_provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Run: pip install openai")
            self.client = OpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url
            )
            logger.info(f"Using OpenAI-compatible API at {self.settings.openai_base_url}")
        else:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            self.client = Anthropic(api_key=self.settings.anthropic_api_key)
            logger.info("Using native Anthropic API")
        
        self.conversation_history: list[dict] = []
        self.tools = get_tools()
        self.openai_tools = self._convert_tools_to_openai_format()
        
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
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt with current context, including discovered data files."""
        # Always discover data files to provide context for import commands
        data_files = discover_data_files(self.working_directory)
        
        # Always use context version to include data files info
        return get_system_prompt_with_context(
            self.working_directory,
            self.existing_files,
            data_files
        )
    
    def update_context(
        self,
        working_directory: Optional[str] = None,
        existing_files: Optional[list[str]] = None
    ):
        """
        Update the context for the conversation.
        
        Args:
            working_directory: New working directory
            existing_files: Updated list of existing files
        """
        if working_directory is not None:
            self.working_directory = working_directory
        if existing_files is not None:
            self.existing_files = existing_files
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
    
    def send_message(
        self,
        user_message: str,
        tool_handler: Optional[Callable[[ToolCall], dict]] = None
    ) -> AgentResponse:
        """
        Send a message to Claude and get a response.
        
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
            
            # If there are tool calls and a handler is provided, process them
            if agent_response.tool_calls and tool_handler:
                agent_response = self._handle_tool_calls(
                    agent_response,
                    tool_handler
                )
            
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
        """Make the API call to Claude (supports both Anthropic and OpenAI-compatible APIs)."""
        if self.api_provider == "openai":
            return self._call_openai_api()
        else:
            return self._call_anthropic_api()
    
    def _call_anthropic_api(self) -> Any:
        """Make API call using native Anthropic API."""
        return self.client.messages.create(
            model=self.settings.model,
            max_tokens=self.settings.max_tokens,
            system=self._get_system_prompt(),
            tools=self.tools,
            messages=self.conversation_history
        )
    
    def _call_openai_api(self) -> Any:
        """Make API call using OpenAI-compatible API."""
        # Convert conversation history to OpenAI format
        messages = [{"role": "system", "content": self._get_system_prompt()}]
        
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
            model=self.settings.model,
            max_tokens=self.settings.max_tokens,
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
        if self.api_provider == "openai":
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
        
        # Add assistant message to history
        self.conversation_history.append({
            "role": "assistant",
            "content": response.content
        })
        
        return AgentResponse(
            message=message_content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            raw_response=response
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
        
        return AgentResponse(
            message=message_content,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            raw_response=response
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
        
        # Get Claude's response after tool execution
        response = self._call_api()
        return self._process_response(response)
    
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
    existing_files: Optional[list[str]] = None
) -> ClaudeClient:
    """
    Create a new Claude client instance.
    
    Args:
        working_directory: Current working directory
        existing_files: List of existing DIALS files
        
    Returns:
        Configured ClaudeClient instance
    """
    return ClaudeClient(
        working_directory=working_directory,
        existing_files=existing_files
    )
