"""
Tests for auto-mode multi-dataset processing in cli.py.

`run_auto` should default to processing every subdirectory of the configured
data directory that looks like an independent dataset (contains recognized
diffraction data files), each into its own output subdirectory — unless the
user's request names one specifically, or there's only one dataset to begin
with (today's original single-dataset behavior, unchanged).
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dials_agent.cli import DIALSAgent
from dials_agent.config import Settings


def make_agent(working_directory: Path, data_directory: str = "") -> DIALSAgent:
    settings = Settings(
        llm_provider="anthropic",
        anthropic_api_key="sk-dummy-test-key",
        cborg_api_key="",
        openai_api_key="",
        gemini_api_key="",
        data_directory=data_directory,
    )
    return DIALSAgent(working_directory=str(working_directory), settings=settings)


def touch(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


@pytest.fixture
def agent(tmp_path) -> DIALSAgent:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return make_agent(output_dir)


class TestDirectoryHasDataFiles:
    def test_finds_direct_file(self, agent, tmp_path):
        d = tmp_path / "ds1"
        touch(d / "image_0001.cbf")
        assert agent._directory_has_data_files(d) is True

    def test_finds_nested_file_within_depth(self, agent, tmp_path):
        d = tmp_path / "ds2"
        touch(d / "sub" / "image_0001.h5")
        assert agent._directory_has_data_files(d, max_depth=2) is True

    def test_no_data_files(self, agent, tmp_path):
        d = tmp_path / "ds3"
        touch(d / "readme.txt")
        assert agent._directory_has_data_files(d) is False

    def test_empty_directory(self, agent, tmp_path):
        d = tmp_path / "ds4"
        d.mkdir()
        assert agent._directory_has_data_files(d) is False

    def test_finds_compressed_image_file(self, agent, tmp_path):
        """Regression test: a real live-testing bug had this diverge from
        core.tools.is_recognized_data_file, which already handled .bz2/.gz
        (v2.5.2) -- _directory_has_data_files checked item.suffix directly
        against DATA_FILE_EXTENSIONS, which only ever sees the LAST dotted
        component ('.bz2' for 't1.0001.img.bz2', not '.img'), so a directory
        containing only compressed images was invisible to multi-dataset
        discovery. Confirmed live: a real data directory with two
        subdirectories of .img.bz2 files silently discovered zero datasets,
        falling back to single-dataset mode and leaving the LLM to guess at
        paths with no directory-listing tool grounding it -- it then
        suggested a completely fabricated import path.
        """
        d = tmp_path / "ds5"
        touch(d / "t1.0001.img.bz2")
        assert agent._directory_has_data_files(d) is True


class TestDiscoverDatasetSubdirectories:
    def test_no_data_directory_configured(self, tmp_path):
        agent = make_agent(tmp_path, data_directory="")
        assert agent._discover_dataset_subdirectories() == []

    def test_single_dataset_subdirectory(self, tmp_path):
        data_root = tmp_path / "data"
        touch(data_root / "insulin" / "image_0001.cbf")
        agent = make_agent(tmp_path / "out", data_directory=str(data_root))
        found = agent._discover_dataset_subdirectories()
        assert [d.name for d in found] == ["insulin"]

    def test_multiple_dataset_subdirectories(self, tmp_path):
        data_root = tmp_path / "data"
        touch(data_root / "insulin" / "image_0001.cbf")
        touch(data_root / "lysozyme" / "image_0001.h5")
        agent = make_agent(tmp_path / "out", data_directory=str(data_root))
        found = agent._discover_dataset_subdirectories()
        assert sorted(d.name for d in found) == ["insulin", "lysozyme"]

    def test_multiple_dataset_subdirectories_with_compressed_images(self, tmp_path):
        """Regression test for the real DPF3 + Insulin case: both
        subdirectories contain only .img.bz2 files. Before the fix, this
        found zero datasets (see test_finds_compressed_image_file), silently
        falling back to single-dataset mode instead of the intended
        multi-dataset loop."""
        data_root = tmp_path / "data"
        for i in range(1, 4):
            touch(data_root / "DPF3" / f"t1.{i:04d}.img.bz2")
        for i in range(1, 4):
            touch(data_root / "Insulin" / f"ins_{i:04d}.img.bz2")
        agent = make_agent(tmp_path / "out", data_directory=str(data_root))
        found = agent._discover_dataset_subdirectories()
        assert sorted(d.name for d in found) == ["DPF3", "Insulin"]

    def test_ignores_subdirectory_without_data_files(self, tmp_path):
        data_root = tmp_path / "data"
        touch(data_root / "insulin" / "image_0001.cbf")
        (data_root / "notes").mkdir(parents=True)
        (data_root / "notes" / "readme.txt").touch()
        agent = make_agent(tmp_path / "out", data_directory=str(data_root))
        found = agent._discover_dataset_subdirectories()
        assert [d.name for d in found] == ["insulin"]

    def test_ignores_hidden_subdirectory(self, tmp_path):
        data_root = tmp_path / "data"
        touch(data_root / "insulin" / "image_0001.cbf")
        touch(data_root / ".hidden" / "image_0001.cbf")
        agent = make_agent(tmp_path / "out", data_directory=str(data_root))
        found = agent._discover_dataset_subdirectories()
        assert [d.name for d in found] == ["insulin"]

    def test_flat_data_directory_with_files_directly_not_subdirectories(self, tmp_path):
        # Files directly in the data directory (not in subdirectories) is the
        # single-dataset case -- no subdirectories to discover.
        data_root = tmp_path / "data"
        touch(data_root / "image_0001.cbf")
        agent = make_agent(tmp_path / "out", data_directory=str(data_root))
        assert agent._discover_dataset_subdirectories() == []


class TestSwitchToDataset:
    def test_creates_output_dir_and_updates_state(self, tmp_path):
        data_root = tmp_path / "data"
        touch(data_root / "insulin" / "image_0001.cbf")
        base_output = tmp_path / "out"
        base_output.mkdir()
        agent = make_agent(base_output, data_directory=str(data_root))

        dataset_dir = data_root / "insulin"
        output_dir = base_output / "insulin"
        assert not output_dir.exists()

        agent._switch_to_dataset(dataset_dir, output_dir)

        assert output_dir.exists()
        assert agent.working_directory == output_dir
        assert agent.settings.data_directory == str(dataset_dir)
        assert output_dir in agent.used_directories

    def test_clears_conversation_history(self, tmp_path):
        data_root = tmp_path / "data"
        touch(data_root / "insulin" / "image_0001.cbf")
        base_output = tmp_path / "out"
        base_output.mkdir()
        agent = make_agent(base_output, data_directory=str(data_root))

        agent.claude.conversation_history.append({"role": "user", "content": "leftover from a previous dataset"})
        assert agent.claude.conversation_history

        agent._switch_to_dataset(data_root / "insulin", base_output / "insulin")
        assert agent.claude.conversation_history == []


class TestRunAutoDispatch:
    """
    These patch `_run_auto_single` (the actual per-dataset LLM loop) so we
    only verify the *dispatch* logic -- which dataset(s) get processed, and
    that each gets its own output subdirectory -- without needing a real
    LLM call or DIALS installation.
    """

    def test_single_dataset_takes_original_path(self, tmp_path):
        data_root = tmp_path / "data"
        touch(data_root / "image_0001.cbf")  # flat, no subdirectories
        base_output = tmp_path / "out"
        base_output.mkdir()
        agent = make_agent(base_output, data_directory=str(data_root))

        with patch.object(agent, "_run_auto_single", return_value=True) as mock_run, \
             patch.object(agent.executor, "check_dials_available", return_value=(True, "DIALS 3.30")):
            agent.run_auto(initial_message="process my data", skip_dials_check=True)

        mock_run.assert_called_once_with("process my data")
        # Working directory should be untouched -- single-dataset path never
        # switches datasets.
        assert agent.working_directory == base_output

    def test_multiple_datasets_processes_all_with_separate_output_dirs(self, tmp_path):
        data_root = tmp_path / "data"
        touch(data_root / "insulin" / "image_0001.cbf")
        touch(data_root / "lysozyme" / "image_0001.h5")
        base_output = tmp_path / "out"
        base_output.mkdir()
        agent = make_agent(base_output, data_directory=str(data_root))

        with patch.object(agent, "_run_auto_single", return_value=True) as mock_run:
            agent.run_auto(initial_message=None, skip_dials_check=True)

        assert mock_run.call_count == 2
        assert (base_output / "insulin").is_dir()
        assert (base_output / "lysozyme").is_dir()
        # Restored to the base output directory afterward.
        assert agent.working_directory == base_output

    def test_naming_one_dataset_processes_only_that_one(self, tmp_path):
        data_root = tmp_path / "data"
        touch(data_root / "insulin" / "image_0001.cbf")
        touch(data_root / "lysozyme" / "image_0001.h5")
        base_output = tmp_path / "out"
        base_output.mkdir()
        agent = make_agent(base_output, data_directory=str(data_root))

        with patch.object(agent, "_run_auto_single", return_value=True) as mock_run:
            agent.run_auto(initial_message="please process the lysozyme dataset", skip_dials_check=True)

        mock_run.assert_called_once_with("please process the lysozyme dataset")
        assert (base_output / "lysozyme").is_dir()
        assert not (base_output / "insulin").exists()

    def test_keyboard_interrupt_stops_remaining_datasets(self, tmp_path):
        data_root = tmp_path / "data"
        touch(data_root / "insulin" / "image_0001.cbf")
        touch(data_root / "lysozyme" / "image_0001.h5")
        base_output = tmp_path / "out"
        base_output.mkdir()
        agent = make_agent(base_output, data_directory=str(data_root))

        with patch.object(agent, "_run_auto_single", side_effect=KeyboardInterrupt) as mock_run:
            agent.run_auto(initial_message=None, skip_dials_check=True)

        # Stopped after the first dataset's interrupt -- did not attempt the second.
        mock_run.assert_called_once()
