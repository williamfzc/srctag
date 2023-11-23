import os

from loguru import logger

from srctag.collector import Collector
from srctag.storage import Storage
from srctag.tagger import Tagger


def test_api():
    collector = Collector()
    collector.config.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ctx = collector.collect_metadata()
    storage = Storage()
    storage.embed_ctx(ctx)

    tagger = Tagger()
    tagger.config.tags = [
        "storage",
        "search",
        "tag",
        "test",
        "example"
    ]
    tag_result = tagger.tag(storage)

    assert tag_result.top_n_tags("srctag/storage.py", 1)
    assert tag_result.top_n_files("example", 1)

    # result check
    assert tag_result.top_n_tags("srctag/storage.py", 1)[0] == "storage"
    assert tag_result.top_n_tags("srctag/tagger.py", 1)[0] == "tag"
