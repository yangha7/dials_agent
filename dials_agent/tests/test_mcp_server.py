"""
Tests for the MCP server that exposes DIALS agent tools to other agents.

Tool registration is checked synchronously via the server's internal
ToolManager (no need to spin up a real stdio/asyncio client for that).
Host dispatch logic is tested directly against DIALSMCPHost, since it's
plain sync code with no MCP machinery involved.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dials_agent.mcp_server import DIALSMCPHost, build_server, _EXCLUDED_TOOLS


EXPECTED_MCP_TOOL_NAMES = {
    "execute_dials_command", "analyze_dials_output", "change_data_directory",
    "select_dataset", "diagnose_problem", "check_workflow_status", "list_available_commands",
    "read_file", "open_file", "change_working_directory", "calculate",
    "get_timing_report", "create_markdown_file", "create_html_file",
    "lookup_phil_params", "load_skill",
}


@pytest.fixture
def host(tmp_path) -> DIALSMCPHost:
    return DIALSMCPHost(working_directory=str(tmp_path))


def test_server_exposes_exactly_the_expected_tools(host):
    server = build_server(host)
    registered = {t.name for t in server._tool_manager.list_tools()}
    assert registered == EXPECTED_MCP_TOOL_NAMES


def test_excluded_tools_are_not_exposed(host):
    server = build_server(host)
    registered = {t.name for t in server._tool_manager.list_tools()}
    assert registered.isdisjoint(_EXCLUDED_TOOLS)


def test_registered_tool_descriptions_match_the_shared_schema(host):
    from dials_agent.core.base_tools import get_base_tools

    shared = {t["name"]: t["description"] for t in get_base_tools() + host.registry.get_all_tools()}
    server = build_server(host)
    for tool in server._tool_manager.list_tools():
        if tool.name == "execute_dials_command":
            continue  # new tool, no shared-schema description to match
        assert tool.description == shared[tool.name]


def test_execute_dials_command_rejects_non_dials_commands(host):
    result = host.execute_dials_command("rm -rf /")
    assert result["success"] is False
    assert "Not a DIALS command" in result["stderr"]


def test_execute_dials_command_records_timing_and_workflow(host):
    host.execute_dials_command("dials.nonexistent_but_dials_prefixed some.expt")
    assert len(host.command_timings) == 1
    assert host.command_timings[0]["command_name"] == "dials.nonexistent_but_dials_prefixed"
    timing_log = host.working_directory / "dials_agent_timing.log"
    assert timing_log.exists()


def test_analyze_dials_output_parses_without_running_anything(host):
    result = host.analyze_dials_output("dials.index", "Indexed 95% of spots", return_code=0)
    assert "summary" in result and "metrics" in result


def test_dispatch_change_working_directory_updates_host_state(host, tmp_path):
    subdir = tmp_path / "newdir"
    subdir.mkdir()
    result = host.dispatch("change_working_directory", {"path": "newdir"})
    assert result["status"] == "success"
    assert host.working_directory == subdir.resolve() or str(host.working_directory) == str(subdir)


def test_dispatch_change_data_directory_updates_host_settings(host, tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    result = host.dispatch("change_data_directory", {"path": str(data_dir)})
    assert result["status"] == "success"
    assert host.settings.data_directory == str(data_dir)


def test_dispatch_strips_host_only_keys(host, tmp_path):
    subdir = tmp_path / "sub2"
    subdir.mkdir()
    result = host.dispatch("change_working_directory", {"path": "sub2"})
    assert not any(k.startswith("_") for k in result)


def test_dispatch_load_skill_returns_full_guidance(host):
    result = host.dispatch("load_skill", {"skill_name": "troubleshooting"})
    assert result["skill"] == "troubleshooting"
    assert len(result["guidance"]) > 0


def test_build_server_raises_if_a_new_registry_tool_is_unaccounted_for(host, monkeypatch):
    from dials_agent.skills.base import BaseSkill

    class FakeSkill(BaseSkill):
        @property
        def name(self) -> str:
            return "fake_for_test"

        @property
        def description(self) -> str:
            return "fake"

        def get_prompt_fragment(self) -> str:
            return "fake"

        def get_tools(self) -> list[dict]:
            return [{
                "name": "brand_new_unhandled_tool",
                "description": "x",
                "input_schema": {"type": "object", "properties": {}},
            }]

    host.registry.register(FakeSkill())
    with pytest.raises(RuntimeError, match="brand_new_unhandled_tool"):
        build_server(host)
