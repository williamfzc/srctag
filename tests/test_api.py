import os

import pytest

from srctag.collector import Collector
from srctag.storage import Storage
from srctag.tagger import Tagger, TagResult


@pytest.fixture
def setup_tagger():
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

    return collector, storage, tagger, tag_result


def test_tag_result(setup_tagger):
    collector, storage, tagger, tag_result = setup_tagger

    assert tag_result.top_n_tags("srctag/storage.py", 1)
    assert tag_result.top_n_files("example", 1)


def test_tag_result_check(setup_tagger):
    collector, storage, tagger, tag_result = setup_tagger

    assert tag_result.top_n_tags("srctag/storage.py", 1)[0] == "storage"
    assert tag_result.top_n_tags("srctag/tagger.py", 1)[0] in ("tag", "search")


def test_io(setup_tagger):
    collector, storage, tagger, tag_result = setup_tagger

    csv_file = "tag_result.csv"
    tag_result.export_csv(csv_file)
    imported_tag_result = TagResult.import_csv(csv_file)

    assert imported_tag_result.top_n_tags("srctag/storage.py", 1)[0] == tag_result.top_n_tags("srctag/storage.py", 1)[0]
    assert imported_tag_result.top_n_tags("srctag/tagger.py", 1)[0] == tag_result.top_n_tags("srctag/tagger.py", 1)[0]


def test_index(setup_tagger):
    collector, storage, tagger, tag_result = setup_tagger

    assert len(tag_result.files()) > 10

    for each in tag_result.files():
        tags = tag_result.top_n_tags(each, 3)
        assert len(tags) == 3

