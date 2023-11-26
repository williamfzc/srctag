import typing
from collections import OrderedDict

import pandas as pd
from chromadb import QueryResult, Metadata
from pandas import Index
from pydantic_settings import BaseSettings
from tqdm import tqdm
from loguru import logger

from srctag.storage import Storage, MetadataConstant


class TagResult(object):
    def __init__(self, scores_df: pd.DataFrame):
        self.scores_df = scores_df

    def export_csv(self, path: str = "srctag-output.csv") -> None:
        self.scores_df.to_csv(path)

    @classmethod
    def import_csv(cls, path: str) -> "TagResult":
        scores_df = pd.read_csv(path, index_col=0)
        return TagResult(scores_df=scores_df)

    def tags(self) -> Index:
        return self.scores_df.columns

    def top_n_tags(self, file_name, n) -> typing.List[str]:
        return self.scores_df.loc[file_name].nlargest(n).index.tolist()

    def top_n_files(self, tag_name, n) -> typing.List[str]:
        return self.scores_df.nlargest(n, tag_name).index.tolist()


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
        doc_count = storage.chromadb_collection.count()
        n_results = int(doc_count * self.config.n_percent)

        logger.info(f"start tagging source files ...")

        tag_results = []
        for each_tag in tqdm(self.config.tags):
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
                each_file_name = each_metadata[MetadataConstant.KEY_SOURCE]
                tag_results.append((each_tag, each_file_name, each_score))
            # END file loop
        # END tag loop

        ret = dict()
        for each_tag, each_file_name, each_score in tag_results:
            if each_file_name not in ret:
                # has not been touched by other tags
                # the score order is decreasing
                ret[each_file_name] = OrderedDict()
            each_file_tag_result = ret[each_file_name]

            if each_tag not in each_file_tag_result:
                each_file_tag_result[each_tag] = each_score
            else:
                # has been touched by other commits
                # merge these scores
                each_file_tag_result[each_tag] += each_score
        # END tag_results

        scores_df = pd.DataFrame.from_dict(ret, orient="index")
        # tag level normalization after merge
        scores_df = scores_df.apply(lambda x: (x - x.min()) / (x.max() - x.min()), axis=0)
        logger.info(f"tag finished")
        return TagResult(scores_df=scores_df)
