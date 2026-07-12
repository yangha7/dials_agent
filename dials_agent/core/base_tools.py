"""
Base tools shared across all skills.

These three tools aren't owned by any single skill: `suggest_dials_command`
is the shared mechanism every workflow skill uses to propose a command,
and `explain_dials_concept` / `analyze_dials_output` just ask the LLM to
use its own knowledge / the shared output parser rather than dispatching
to skill-specific logic. They're handled directly by the CLI (or other
host) rather than through the `SkillRegistry`.
"""

BASE_TOOLS: list[dict] = [
    {
        "name": "suggest_dials_command",
        "description": "Suggest a DIALS command to execute based on the user's request. Use this when the user wants to perform a data processing step.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The complete DIALS command to execute, including all arguments and parameters"
                },
                "explanation": {
                    "type": "string",
                    "description": "A clear, user-friendly explanation of what this command does and why it's appropriate"
                },
                "expected_output": {
                    "type": "string",
                    "description": "Description of the expected output files and what they contain"
                },
                "warnings": {
                    "type": "string",
                    "description": "Any warnings or considerations the user should be aware of (optional)"
                }
            },
            "required": ["command", "explanation", "expected_output"]
        }
    },
    {
        "name": "explain_dials_concept",
        "description": "Explain a DIALS concept, parameter, or crystallography term to the user. Use this when the user asks questions about terminology or needs clarification.",
        "input_schema": {
            "type": "object",
            "properties": {
                "concept": {
                    "type": "string",
                    "description": "The concept, term, or parameter to explain"
                },
                "context": {
                    "type": "string",
                    "description": "Additional context about why this concept is relevant (optional)"
                }
            },
            "required": ["concept"]
        }
    },
    {
        "name": "analyze_dials_output",
        "description": "Analyze the output from a DIALS command and provide a summary. Use this after a command has been executed to help the user understand the results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The DIALS command that was executed"
                },
                "output": {
                    "type": "string",
                    "description": "The output text from the command"
                },
                "return_code": {
                    "type": "integer",
                    "description": "The return code from the command (0 = success)"
                }
            },
            "required": ["command", "output"]
        }
    },
]


def get_base_tools() -> list[dict]:
    """Get the list of tool definitions that are shared across all skills."""
    return BASE_TOOLS
