import typing
from collections import OrderedDict

import networkx
import networkx as nx
import numpy as np
import pandas as pd
from chromadb import QueryResult, Metadata
from loguru import logger
from pandas import Index
from pydantic_settings import BaseSettings
from tqdm import tqdm

from srctag.storage import Storage, MetadataConstant


class TagResult(object):
    def __init__(self, scores_df: pd.DataFrame):
        self.scores_df = scores_df

    def export_csv(self, path: str = "srctag-output.csv") -> None:
        logger.info(f"dump result to csv: {path}")
        self.scores_df.to_csv(path)

    def export_networkx(self) -> nx.Graph:
        df = self.scores_df.fillna(0)

        g = nx.Graph()
        for col in df.columns:
            g.add_node(col, color='lightcoral')

        for row in df.index:
            g.add_node(row, color='lightblue')

        for col in df.columns:
            for row in df.index:
                g.add_edge(col, row, weight=df.loc[row, col])

        return g

    def export_dot(self, path: str):
        graph = self.export_networkx()
        logger.info(f"dump result to dot: {path}")
        networkx.drawing.nx_pydot.write_dot(graph, path)

    @classmethod
    def import_csv(cls, path: str) -> "TagResult":
        scores_df = pd.read_csv(path, index_col=0)
        return TagResult(scores_df=scores_df)

    def tags(self) -> Index:
        return self.scores_df.columns

    def files(self) -> Index:
        return self.scores_df.index

    def tags_by_file(self, file_name: str) -> typing.Optional[pd.Series]:
        if file_name not in self.scores_df.index:
            return None
        return self.scores_df.loc[file_name].sort_values(ascending=False)

    def files_by_tag(self, tag_name: str) -> typing.Optional[pd.Series]:
        if tag_name not in self.scores_df.columns:
            return None
        return self.scores_df.loc[:, tag_name].sort_values(ascending=False)

    def top_n_tags(self, file_name: str, n: int) -> typing.List[str]:
        return self.tags_by_file(file_name).nlargest(n).index.tolist()

    def top_n_files(self, tag_name: str, n: int) -> typing.List[str]:
        return self.files_by_tag(tag_name).nlargest(n).index.tolist()

    def normalize_score(self, origin: float) -> float:
        return origin / len(self.files())


class TaggerConfig(BaseSettings):
    tags: typing.Set[str] = set()

    # eg: 0.3 == choosing the closest 30% results
    n_percent: float = 0.3

    # use self.optimize or not
    optimize: bool = False

    # normalization or rank
    normalize: bool = True


class Tagger(object):
    """load feature map, search related files, and tag them"""

    def __init__(self, config: TaggerConfig = None):
        if not config:
            config = TaggerConfig()
        self.config = config

    def tag_with_commit(self, storage: Storage) -> TagResult:
        doc_count = storage.chromadb_collection.count()
        n_results = int(doc_count * self.config.n_percent)

        tag_results = []
        relation_graph = storage.relation_graph.copy()
        for each_tag in tqdm(self.config.tags):
            query_result: QueryResult = storage.chromadb_collection.query(
                query_texts=each_tag,
                n_results=n_results,
                include=["metadatas", "distances"],
                where={MetadataConstant.KEY_DATA_TYPE: MetadataConstant.DATA_TYPE_COMMIT_MSG}
            )

            metadatas: typing.List[Metadata] = query_result["metadatas"][0]
            # https://github.com/langchain-ai/langchain/blob/master/libs/langchain/langchain/vectorstores/chroma.py
            # https://stats.stackexchange.com/questions/158279/how-i-can-convert-distance-euclidean-to-similarity-score
            distances: typing.List[float] = query_result["distances"][0]
            normalized_scores = [
                1.0 / (1.0 + x) for x in distances
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
                # has been touched by other commits, merge
                each_file_tag_result[each_tag] += each_score

            # update graph
            relation_graph.add_node(each_tag, node_type=MetadataConstant.KEY_TAG)
            relation_graph.add_edge(each_tag, each_file_name)
        # END tag_results

        scores_df = pd.DataFrame.from_dict(ret, orient="index")
        if self.config.optimize:
            scores_df = self.optimize(scores_df)

        # convert score matrix into rank (use reversed rank as score). because:
        # 1. score/distance is meaningless to users
        # 2. can not be evaluated both rows and cols
        scores_df = scores_df.rank(axis=0, method='min')

        if self.config.normalize:
            scores_df = (scores_df - scores_df.min()) / (scores_df.max() - scores_df.min())

        logger.info(f"tag finished")
        # update relation graph in storage
        storage.relation_graph = relation_graph

        return TagResult(scores_df=scores_df)

    def tag_with_issue(self, storage: Storage) -> TagResult:
        doc_count = storage.chromadb_collection.count()
        n_results = int(doc_count * self.config.n_percent)

        tag_results = []
        relation_graph = storage.relation_graph.copy()
        for each_tag in tqdm(self.config.tags):
            query_result: QueryResult = storage.chromadb_collection.query(
                query_texts=each_tag,
                n_results=n_results,
                include=["metadatas", "distances"],
                where={MetadataConstant.KEY_DATA_TYPE: MetadataConstant.DATA_TYPE_ISSUE}
            )

            metadatas: typing.List[Metadata] = query_result["metadatas"][0]
            # https://github.com/langchain-ai/langchain/blob/master/libs/langchain/langchain/vectorstores/chroma.py
            # https://stats.stackexchange.com/questions/158279/how-i-can-convert-distance-euclidean-to-similarity-score
            distances: typing.List[float] = query_result["distances"][0]
            normalized_scores = [
                1.0 / (1.0 + x) for x in distances
            ]

            for each_metadata, each_score in zip(metadatas, normalized_scores):
                each_issue_id = each_metadata[MetadataConstant.KEY_ISSUE_ID]
                tag_results.append((each_tag, each_issue_id, each_score))
            # END file loop
        # END tag loop

        ret = dict()
        for each_tag, each_issue_id, each_score in tag_results:
            files = storage.relation_graph.neighbors(each_issue_id)
            for each_file in files:
                if each_file not in ret:
                    # has not been touched by other tags
                    # the score order is decreasing
                    ret[each_file] = OrderedDict()
                each_file_tag_result = ret[each_file]

                if each_tag not in each_file_tag_result:
                    each_file_tag_result[each_tag] = each_score
                else:
                    # has been touched by other commits, merge
                    each_file_tag_result[each_tag] += each_score

                # update graph
                relation_graph.add_node(each_tag, node_type=MetadataConstant.KEY_TAG)
                relation_graph.add_edge(each_tag, each_issue_id)
        # END tag_results

        scores_df = pd.DataFrame.from_dict(ret, orient="index")
        if self.config.optimize:
            scores_df = self.optimize(scores_df)

        # convert score matrix into rank (use reversed rank as score). because:
        # 1. score/distance is meaningless to users
        # 2. can not be evaluated both rows and cols
        scores_df = scores_df.rank(axis=0, method='min')

        if self.config.normalize:
            scores_df = (scores_df - scores_df.min()) / (scores_df.max() - scores_df.min())

        logger.info(f"tag finished")
        # update relation graph in storage
        storage.relation_graph = relation_graph
        return TagResult(scores_df=scores_df)

    def tag(self, storage: Storage) -> TagResult:
        logger.info(f"start tagging source files ...")
        storage.init_chroma()

        if storage.relation_graph.number_of_nodes():
            logger.info("tag with issue")
            return self.tag_with_issue(storage)
        else:
            logger.info("tag with commit")
            return self.tag_with_commit(storage)

    def optimize(self, df: pd.DataFrame) -> pd.DataFrame:
        scale_factor = 2.0
        df = np.exp(df * scale_factor)

        # reduce the impacts of common files
        row_variances = df.var(axis=1)
        max_variance = row_variances.max()
        weights = 1.0 - row_variances / max_variance
        df = df.multiply(weights, axis=0)
        return df
