from click.testing import CliRunner
import pathlib

from srctag.cli import diff, graph


def test_diff():
    runner = CliRunner()
    path = pathlib.Path(__file__).parent.parent.as_posix()
    runner.invoke(diff, ["--repo-root", path, "--batch", 2], catch_exceptions=False)


def test_graph():
    runner = CliRunner()
    path = pathlib.Path(__file__).parent.parent.as_posix()
    runner.invoke(graph, ["--repo-root", path], catch_exceptions=False)
