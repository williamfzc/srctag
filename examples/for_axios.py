import pathlib
import sys
import warnings

from srctag.collector import Collector
from srctag.storage import Storage
from srctag.tagger import Tagger

axios_repo = pathlib.Path(__file__).parent.parent / "axios"
if not axios_repo.is_dir():
    warnings.warn(f"clone axios to {axios_repo} first")
    sys.exit(0)

collector = Collector()
collector.config.repo_root = axios_repo
collector.config.max_depth_limit = -1
collector.config.include_regex = r"lib.*"

ctx = collector.collect_metadata()
storage = Storage()
storage.embed_ctx(ctx)
tagger = Tagger()
tagger.config.tags = [
    "XMLHttpRequests from browser",
    "HTTP requests from node.js",
    "Promise API support",
    "Request and response interception",
    "Request and response data transformation",
    "Request cancellation",
    "Automatic JSON data transforms",
    "Automatic serialization of data objects",
    "Client-side XSRF protection"
]
tag_dict = tagger.tag(storage)
print(tag_dict.scores_df.to_string(index=False))
