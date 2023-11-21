import typing

from chromadb import QueryResult, Metadata
from pydantic_settings import BaseSettings

from srctag.storage import Storage


class TaggerConfig(BaseSettings):
    tags: typing.Set[str] = set()
    n_results: int = 10


class Tagger(object):
    """ load feature map, search related files, and tag them """

    def __init__(self, config: TaggerConfig = None):
        if not config:
            config = TaggerConfig()
        self.config = config

    def tag(self, storage: Storage) -> typing.Dict[str, typing.Set[str]]:
        ret = dict()
        for each_tag in self.config.tags:
            query_result: QueryResult = storage.chromadb_collection.query(
                query_texts=each_tag,
                n_results=self.config.n_results,
            )
            files: typing.List[Metadata] = query_result["metadatas"][0]

            for each_file in files:
                each_file_name = each_file["source"]
                if each_file_name not in ret:
                    ret[each_file_name] = set()
                ret[each_file_name].add(each_tag)
        return ret
