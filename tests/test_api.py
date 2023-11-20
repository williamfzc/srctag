from srctag import CollectorLayer, Storage

def test_abc():
    collector = CollectorLayer()
    collector.config.repo_root = "."
    collector.config.max_depth_limit = 1
    ctx = collector.collect_metadata()
    storage = Storage()
    for each_file in ctx.files.values():
        storage.embed_file(each_file)

    result = storage.chromadb_collection.query(query_texts=["docs"])
    print(result)
