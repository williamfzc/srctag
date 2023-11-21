from srctag.collector import FileLevelEnum, Collector
from srctag.storage import StorageConfig, Storage
from tqdm import tqdm

collector = Collector()
collector.config.repo_root = ".."
collector.config.file_level = FileLevelEnum.DIR
collector.config.max_depth_limit = 16

ctx = collector.collect_metadata()
storage = Storage(StorageConfig(collection_name="aaa"))
for each_file in tqdm(ctx.files.values()):
    storage.embed_file(each_file)
