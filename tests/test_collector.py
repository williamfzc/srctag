import os

from srctag.collector import Collector


def test_tagger_specific():
    collector = Collector()
    collector.config.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    collector.config.include_file_list = ["README.md"]
    ctx = collector.collect_metadata()
    assert len(ctx.files) == 1
