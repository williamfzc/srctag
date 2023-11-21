from srctag.collector import FileLevelEnum, Collector
from srctag.storage import Storage

collector = Collector()
collector.config.repo_root = ".."
collector.config.file_level = FileLevelEnum.DIR
collector.config.max_depth_limit = 16

ctx = collector.collect_metadata()
storage = Storage()
storage.embed_ctx(ctx)
