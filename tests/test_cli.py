import contextlib
import io
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from nes_pascal import __version__
from nes_pascal.cli import ToolchainError, compile_source, main


MINIMAL = """program Minimal;
begin
    nes.set_background_color($21);
    nes.run;
end.
"""


class ToolchainFailureTests(unittest.TestCase):
    def _write_source(self) -> tuple[Path, Path]:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        root = Path(temporary_directory.name)
        source_path = root / "main.nsp"
        source_path.write_text(MINIMAL, encoding="utf-8")
        return source_path, root / "main.nes"

    def test_missing_toolchain_component_is_reported(self) -> None:
        source_path, output_path = self._write_source()
        with patch("nes_pascal.cli.shutil.which", return_value=None):
            with self.assertRaises(ToolchainError) as context:
                compile_source(source_path, output_path)

        message = str(context.exception)
        self.assertIn("E5001", message)
        self.assertIn("missing toolchain component: ca65 and ld65", message)
        self.assertIn("Install the cc65 package and try again.", message)

    def test_missing_toolchain_is_reported_for_each_component(self) -> None:
        source_path, output_path = self._write_source()

        def only_ld65(name: str) -> str | None:
            return "/usr/bin/ld65" if name == "ld65" else None

        with patch("nes_pascal.cli.shutil.which", side_effect=only_ld65):
            with self.assertRaises(ToolchainError) as context:
                compile_source(source_path, output_path)

        message = str(context.exception)
        self.assertIn("E5001", message)
        self.assertIn("missing toolchain component: ca65", message)
        self.assertNotIn("ld65", message)

    def test_tool_execution_failure_reports_tool_and_stderr(self) -> None:
        source_path, output_path = self._write_source()
        result = SimpleNamespace(
            returncode=1,
            stderr="main.asm(5): Error: syntax error\nmain.asm(6): Error: syntax error",
            stdout="",
        )
        with patch("nes_pascal.cli.shutil.which", return_value="/usr/bin/ca65"), patch(
            "nes_pascal.cli.subprocess.run", return_value=result
        ) as run:
            with self.assertRaises(ToolchainError) as context:
                compile_source(source_path, output_path)

        message = str(context.exception)
        self.assertIn("E5002", message)
        self.assertIn("ca65 failed", message)
        self.assertIn("main.asm(5): Error: syntax error", message)
        self.assertNotIn("E5001", message)
        command = run.call_args.args[0]
        self.assertEqual(command[0], "/usr/bin/ca65")

    def test_ld65_execution_failure_is_reported_separately(self) -> None:
        source_path, output_path = self._write_source()
        results = [
            SimpleNamespace(returncode=0, stderr="", stdout=""),
            SimpleNamespace(
                returncode=1,
                stderr="ld65: Error: Memory area overflow",
                stdout="",
            ),
        ]

        def which(name: str) -> str | None:
            return f"/usr/bin/{name}"

        with patch("nes_pascal.cli.shutil.which", side_effect=which), patch(
            "nes_pascal.cli.subprocess.run", side_effect=results
        ) as run:
            with self.assertRaises(ToolchainError) as context:
                compile_source(source_path, output_path)

        message = str(context.exception)
        self.assertIn("E5002", message)
        self.assertIn("ld65 failed", message)
        self.assertIn("ld65: Error: Memory area overflow", message)
        self.assertEqual(
            [call.args[0][0] for call in run.call_args_list],
            ["/usr/bin/ca65", "/usr/bin/ld65"],
        )


class FileAccessFailureTests(unittest.TestCase):
    def test_unreadable_source_is_reported_as_file_access_failure(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        root = Path(temporary_directory.name)
        source_path = root / "main.nsp"
        source_path.write_text(MINIMAL, encoding="utf-8")

        stderr = io.StringIO()
        with patch.object(
            Path, "read_text", side_effect=OSError("permission denied")
        ), contextlib.redirect_stderr(stderr):
            exit_code = main([str(source_path), "-o", str(root / "main.nes")])

        self.assertEqual(exit_code, 1)
        rendered = stderr.getvalue()
        self.assertIn("E6001", rendered)
        self.assertIn("could not access a file: permission denied", rendered)


class PackagingMetadataTests(unittest.TestCase):
    def _pyproject(self) -> dict:
        repository_root = Path(__file__).resolve().parent.parent
        with (repository_root / "pyproject.toml").open("rb") as handle:
            return tomllib.load(handle)

    def test_pyproject_declares_nes_pascal_console_script(self) -> None:
        scripts = self._pyproject()["project"]["scripts"]
        self.assertEqual(scripts, {"nes-pascal": "nes_pascal.cli:main"})

    def test_package_version_matches_pyproject(self) -> None:
        self.assertEqual(__version__, self._pyproject()["project"]["version"])


if __name__ == "__main__":
    unittest.main()
