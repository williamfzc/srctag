from srctag.collector import FileLevelEnum, Collector
from srctag.storage import Storage
import os

collector = Collector()
collector.config.repo_root = os.path.dirname(os.path.dirname(__file__))
collector.config.file_level = FileLevelEnum.FILE
collector.config.max_depth_limit = 16

ctx = collector.collect_metadata()
storage = Storage()
storage.embed_ctx(ctx)
