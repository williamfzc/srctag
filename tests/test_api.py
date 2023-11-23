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
        "embedding",
        "search",
    ]
    tag_result = tagger.tag(storage)
    logger.info(f"tags: {tag_result.tags().array}")
    assert tag_result.tags().array
