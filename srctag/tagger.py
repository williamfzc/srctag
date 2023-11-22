import csv
import typing

from chromadb import QueryResult, Metadata
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from srctag.storage import Storage

# tag name -> distance score
SingleTagResult = typing.Dict[str, float]


class TagResult(BaseModel):
    files: typing.Dict[str, SingleTagResult] = dict()

    def export_csv(self, path: str = "srctag-output.csv") -> None:
        file_list = self.files.keys()
        col_list = set().union(*[d.keys() for d in self.files.values()])
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)

            header = [""] + list(col_list)
            writer.writerow(header)

            for each_file in file_list:
                row = [each_file] + [
                    self.files[each_file].get(subkey, "-1") for subkey in col_list
                ]
                writer.writerow(row)


class TaggerConfig(BaseSettings):
    tags: typing.Set[str] = set()

    # eg: 0.3 == choosing the closest 30% results
    n_percent: float = 0.3


class Tagger(object):
    """load feature map, search related files, and tag them"""

    def __init__(self, config: TaggerConfig = None):
        if not config:
            config = TaggerConfig()
        self.config = config

    def tag(self, storage: Storage) -> TagResult:
        storage.init_chroma()
        file_count = storage.chromadb_collection.count()
        n_results = int(file_count * self.config.n_percent)

        ret = dict()
        for each_tag in self.config.tags:
            query_result: QueryResult = storage.chromadb_collection.query(
                query_texts=each_tag,
                n_results=n_results,
                include=["metadatas", "distances"],
            )
            files: typing.List[Metadata] = query_result["metadatas"][0]
            distances: typing.List[float] = query_result["distances"][0]

            minimum = min(distances)
            maximum = max(distances)
            normalized_scores = [
                1 - (x - minimum) / (maximum - minimum) for x in distances
            ]

            for each_file, each_score in zip(files, normalized_scores):
                each_file_name = each_file["source"]
                if each_file_name not in ret:
                    ret[each_file_name] = dict()
                ret[each_file_name][each_tag] = each_score

        return TagResult(files=ret)
