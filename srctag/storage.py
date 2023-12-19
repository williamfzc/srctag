import json
import typing

import chromadb
import networkx as nx
from chromadb import API
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger
from networkx import Graph
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from tqdm import tqdm

from srctag.model import FileContext, RuntimeContext, SrcTagException


class StorageDoc(BaseModel):
    document: str
    metadata: typing.Dict[str, str]
    id: str


class MetadataConstant(object):
    KEY_SOURCE = "source"
    KEY_COMMIT_SHA = "commit_sha"
    KEY_DATA_TYPE = "data_type"
    KEY_ISSUE_ID = "issue_id"
    KEY_TAG = "tag"

    # use in chroma
    DATA_TYPE_COMMIT_MSG = "commit_msg"
    DATA_TYPE_ISSUE = "issue"


class StorageConfig(BaseSettings):
    db_path: str = ""
    collection_name: str = "default_collection"

    # English: paraphrase-MiniLM-L6-v2
    # Multi langs: paraphrase-multilingual-MiniLM-L12-v2
    st_model_name: str = "paraphrase-MiniLM-L6-v2"

    # content mapping for avoiding too much I/O
    # "#11" -> "content for #11"
    issue_mapping: typing.Dict[str, str] = dict()

    data_types: typing.Set[str] = {MetadataConstant.DATA_TYPE_COMMIT_MSG, MetadataConstant.DATA_TYPE_ISSUE}

    def load_issue_mapping_from_gh_json_file(self, gh_json_file: str):
        with open(gh_json_file) as f:
            content = json.load(f)
        assert isinstance(content, list), "not a valid issue dump"

        for each in content:
            sharp_id = f'#{each["number"]}'
            self.issue_mapping[sharp_id] = each["title"]
        logger.info(f"load {len(content)} issues from {gh_json_file}")


class Storage(object):
    def __init__(self, config: StorageConfig = None):
        if not config:
            config = StorageConfig()
        self.config = config

        self.chromadb: typing.Optional[API] = None
        self.chromadb_collection: typing.Optional[Collection] = None
        self.relations: Graph = nx.Graph()

    def init_chroma(self):
        if self.chromadb and self.chromadb_collection:
            return

        if self.config.db_path:
            self.chromadb = chromadb.PersistentClient(path=self.config.db_path)
        else:
            # by default, using in-memory db
            self.chromadb = chromadb.Client()

        self.chromadb_collection = self.chromadb.get_or_create_collection(
            self.config.collection_name,
            embedding_function=SentenceTransformerEmbeddingFunction(
                model_name=self.config.st_model_name
            ),
            # dis range: [0, 1]
            metadata={"hnsw:space": "l2"}
        )

    def process_commit_msg(self, file: FileContext, collection: Collection, _: RuntimeContext):
        """ can be overwritten for custom processing """
        targets = []
        for each in file.commits:
            # keep enough data in metadata for calc the final score
            item = StorageDoc(
                document=each.message,
                metadata={
                    MetadataConstant.KEY_SOURCE: file.name,
                    MetadataConstant.KEY_COMMIT_SHA: str(each.hexsha),
                    MetadataConstant.KEY_DATA_TYPE: MetadataConstant.DATA_TYPE_COMMIT_MSG,
                },
                id=f"{MetadataConstant.DATA_TYPE_COMMIT_MSG}|{file.name}|{each.hexsha}"
            )
            targets.append(item)

        for each in targets:
            collection.add(
                documents=[each.document],
                metadatas=[each.metadata],
                ids=[each.id],
            )

    def process_issue_id_to_title(self, issue_id: str) -> str:
        # easily reach the API limit if using server API here,
        # so we use issue_mapping, keep it simple
        return self.config.issue_mapping.get(issue_id, "")

    def process_issue(self, _: FileContext, collection: Collection, ctx: RuntimeContext):
        issue_id_list = [x for x, y in ctx.relations.nodes(data=True) if
                         y["node_type"] == MetadataConstant.KEY_ISSUE_ID]

        targets = []
        for each_issue_id in issue_id_list:
            each_issue_content = self.process_issue_id_to_title(each_issue_id)
            if not each_issue_content:
                continue

            item = StorageDoc(
                document=each_issue_content,
                metadata={
                    MetadataConstant.KEY_ISSUE_ID: each_issue_id,
                    MetadataConstant.KEY_DATA_TYPE: MetadataConstant.DATA_TYPE_ISSUE,
                },
                id=f"{MetadataConstant.DATA_TYPE_ISSUE}|{each_issue_id}"
            )
            targets.append(item)

            # END issue loop
        # END commit loop

        for each in targets:
            collection.upsert(
                documents=[each.document],
                metadatas=[each.metadata],
                ids=[each.id],
            )

    def process_file_ctx(self, file: FileContext, collection: Collection, ctx: RuntimeContext):
        process_dict = {
            MetadataConstant.DATA_TYPE_ISSUE: self.process_issue,
            MetadataConstant.DATA_TYPE_COMMIT_MSG: self.process_commit_msg
        }
        for each in self.config.data_types:
            if each not in process_dict:
                raise SrcTagException(f"invalid data type: {each}")
            process_dict[each](file, collection, ctx)

    def embed_file(self, file: FileContext, ctx: RuntimeContext):
        if not file.commits:
            logger.warning(f"no related commits found: {file.name}")
            return

        self.init_chroma()
        self.process_file_ctx(file, self.chromadb_collection, ctx)

    def embed_ctx(self, ctx: RuntimeContext):
        self.init_chroma()
        self.relations = ctx.relations
        logger.info("start embedding source files")
        for each_file in tqdm(ctx.files.values()):
            self.embed_file(each_file, ctx)
        logger.info("embedding finished")
