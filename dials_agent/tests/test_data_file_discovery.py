"""
Tests for compressed diffraction-image discovery in core/tools.py.

Regression coverage for a real bug found live-testing the DPF3 tutorial: a
directory of `t1.NNNN.img.bz2` files wasn't recognized as diffraction data
at all (Path.suffix on a compressed file returns just `.bz2`), so the agent
never saw them in "Available diffraction data files" and, lacking that
context, tried to bunzip2 them into a new copy before importing -- entirely
unnecessary, since dxtbx/DIALS reads .bz2/.gz-compressed images directly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dials_agent.core.tools import (
    DATA_FILE_EXTENSIONS,
    COMPRESSED_EXTENSIONS,
    is_recognized_data_file,
    discover_data_files,
)


class TestIsRecognizedDataFile:
    def test_plain_recognized_extension(self, tmp_path):
        f = tmp_path / "image_0001.cbf"
        f.touch()
        assert is_recognized_data_file(f) is True

    def test_bz2_compressed_img(self, tmp_path):
        f = tmp_path / "t1.0001.img.bz2"
        f.touch()
        assert is_recognized_data_file(f) is True

    def test_gz_compressed_h5(self, tmp_path):
        f = tmp_path / "insulin_master.h5.gz"
        f.touch()
        assert is_recognized_data_file(f) is True

    def test_unrecognized_extension(self, tmp_path):
        f = tmp_path / "readme.txt"
        f.touch()
        assert is_recognized_data_file(f) is False

    def test_compressed_but_not_a_data_format(self, tmp_path):
        # A compressed non-data file (e.g. a compressed log) shouldn't be
        # swept in just because it ends in .bz2/.gz.
        f = tmp_path / "dials.import.log.gz"
        f.touch()
        assert is_recognized_data_file(f) is False

    def test_bare_compression_extension_alone_is_not_enough(self, tmp_path):
        f = tmp_path / "archive.bz2"  # no recognized format before the .bz2
        f.touch()
        assert is_recognized_data_file(f) is False


class TestDiscoverDataFilesWithCompression:
    def test_finds_bz2_images_in_subdirectory(self, tmp_path):
        images = tmp_path / "images"
        images.mkdir()
        for i in range(1, 6):
            (images / f"t1.{i:04d}.img.bz2").touch()
        (images / "readme.txt").touch()

        found = discover_data_files(working_directory=str(tmp_path))
        names = sorted(f["name"] for f in found)
        assert names == [f"t1.{i:04d}.img.bz2" for i in range(1, 6)]

    def test_compressed_file_gets_descriptive_type_label(self, tmp_path):
        (tmp_path / "t1.0001.img.bz2").touch()
        found = discover_data_files(working_directory=str(tmp_path))
        assert found[0]["type"] == "IMG.BZ2"

    def test_uncompressed_and_compressed_files_both_found(self, tmp_path):
        (tmp_path / "plain.cbf").touch()
        (tmp_path / "compressed.img.bz2").touch()
        found = discover_data_files(working_directory=str(tmp_path))
        names = {f["name"] for f in found}
        assert names == {"plain.cbf", "compressed.img.bz2"}

    def test_extensions_constants_are_consistent(self):
        # Sanity check the two module-level sets don't accidentally overlap
        # or drift (e.g. someone adding ".img.bz2" directly to
        # DATA_FILE_EXTENSIONS instead of relying on the compression check).
        assert DATA_FILE_EXTENSIONS.isdisjoint(COMPRESSED_EXTENSIONS)
