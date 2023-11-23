import typing
from collections import OrderedDict

import pandas as pd
from chromadb import QueryResult, Metadata
from pandas import Index, DataFrame
from pydantic_settings import BaseSettings

from srctag.storage import Storage


class TagResult(object):
    def __init__(self, scores_df: pd.DataFrame):
        self.scores_df = scores_df

    def export_csv(self, path: str = "srctag-output.csv") -> None:
        self.scores_df.to_csv(path)

    def tags(self) -> Index:
        return self.scores_df.columns

    def top_n(self, path: str, n: int) -> DataFrame:
        row = self.scores_df.loc[path]
        return row.nlargest(n)


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

            metadatas: typing.List[Metadata] = query_result["metadatas"][0]
            distances: typing.List[float] = query_result["distances"][0]

            minimum = min(distances)
            maximum = max(distances)
            if maximum == minimum:
                # all values are the same
                normalized_scores = [1 for _ in distances]
            else:
                normalized_scores = [
                    1 - ((x - minimum) / (maximum - minimum)) for x in distances
                ]

            for each_metadata, each_score in zip(metadatas, normalized_scores):
                each_file_name = each_metadata["source"]
                if each_file_name not in ret:
                    ret[each_file_name] = OrderedDict()
                ret[each_file_name][each_tag] = each_score
            # END file loop
        # END tag loop

        scores_df = pd.DataFrame.from_dict(ret, orient="index")
        return TagResult(scores_df=scores_df)
