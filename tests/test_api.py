import os

import pytest
from loguru import logger

from srctag.collector import Collector
from srctag.storage import Storage
from srctag.tagger import Tagger, TagResult

all_tags = [
    "storage",
    "search",
    "tag",
    "test",
    "example"
]


@pytest.fixture(scope="session")
def setup_tagger():
    collector = Collector()
    collector.config.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ctx = collector.collect_metadata()
    storage = Storage()
    storage.embed_ctx(ctx)

    tagger = Tagger()
    tagger.config.tags = all_tags
    tag_result = tagger.tag(storage)

    return collector, storage, tagger, tag_result


def test_tag_result(setup_tagger):
    collector, storage, tagger, tag_result = setup_tagger

    assert tag_result.top_n_tags("srctag/storage.py", 1)
    assert tag_result.top_n_files("example", 1)


def test_tag_result_check(setup_tagger):
    collector, storage, tagger, tag_result = setup_tagger

    assert tag_result.top_n_tags("srctag/storage.py", 1)[0] == "storage"
    assert tag_result.top_n_tags("srctag/tagger.py", 1)[0] in ("tag", "search", "storage")


def test_io(setup_tagger):
    collector, storage, tagger, tag_result = setup_tagger

    csv_file = "tag_result.csv"
    tag_result.export_csv(csv_file)
    imported_tag_result = TagResult.import_csv(csv_file)

    assert imported_tag_result.top_n_tags("srctag/storage.py", 1)[0] == tag_result.top_n_tags("srctag/storage.py", 1)[0]
    assert imported_tag_result.top_n_tags("srctag/tagger.py", 1)[0] == tag_result.top_n_tags("srctag/tagger.py", 1)[0]

    dot_file = "dot.dot"
    tag_result.export_dot(dot_file)
    assert os.path.isfile(dot_file)


def test_index(setup_tagger):
    collector, storage, tagger, tag_result = setup_tagger

    assert len(tag_result.tags()) == len(all_tags)
    assert len(tag_result.files()) > 10

    for each in tag_result.files():
        each_tags = tag_result.top_n_tags(each, 3)
        assert len(each_tags) == 3


def test_query(setup_tagger):
    collector, storage, tagger, tag_result = setup_tagger

    tags_series = tag_result.tags_by_file("examples/write.py")
    assert len(tags_series) == len(all_tags)
    tags_series = tags_series[:5]
    assert len(tags_series) == 5
    for k, v in tags_series.items():
        normalize_score = tag_result.normalize_score(v)
        logger.info(f"tag: {k}, score: {normalize_score}")

    files_series = tag_result.files_by_tag("example")
    assert len(files_series) > 10
    for k, v in files_series.items():
        normalize_score = tag_result.normalize_score(v)
        logger.info(f"file: {k}, score: {normalize_score}")
