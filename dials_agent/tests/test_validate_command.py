"""
Tests for dials.commands.validate_command, focused on the interpreter
fallback bug found live on dials.lbl.gov: dials.python was missing from
that install's conda_base/bin, so the agent (correctly, per its own
prompt guidance) tried libtbx.python then cctbx.python -- both of which
were rejected outright by validate_command before ever reaching the
executor, because it only accepted names starting with "dials.".
"""

from dials_agent.dials.commands import validate_command


def test_known_dials_command_is_valid():
    is_valid, msg = validate_command("dials.import foo.img")
    assert is_valid
    assert msg == ""


def test_unknown_dials_dot_command_is_valid_with_warning():
    is_valid, msg = validate_command("dials.python script.py foo.expt")
    assert is_valid
    assert "Warning" in msg


def test_libtbx_python_fallback_is_valid():
    is_valid, msg = validate_command("libtbx.python script.py foo.expt")
    assert is_valid
    assert msg == ""


def test_cctbx_python_fallback_is_valid():
    is_valid, msg = validate_command("cctbx.python script.py foo.expt")
    assert is_valid
    assert msg == ""


def test_arbitrary_non_dials_command_is_rejected():
    is_valid, msg = validate_command("rm -rf foo")
    assert not is_valid
    assert "Not a DIALS command" in msg


def test_python_bare_is_still_rejected():
    # Only the two documented fallbacks are allow-listed, not bare python.
    is_valid, msg = validate_command("python script.py")
    assert not is_valid
    assert "Not a DIALS command" in msg


def test_empty_command_is_rejected():
    is_valid, msg = validate_command("   ")
    assert not is_valid
    assert msg == "Empty command"
