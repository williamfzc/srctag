import os
import re
import typing

import chromadb
from chromadb import API
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger
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

    DATA_TYPE_COMMIT_MSG = "commit_msg"
    DATA_TYPE_ISSUE = "issue"


class StorageConfig(BaseSettings):
    db_path: str = ""
    collection_name: str = "default_collection"

    # English: paraphrase-MiniLM-L6-v2
    # Multi langs: paraphrase-multilingual-MiniLM-L12-v2
    st_model_name: str = "paraphrase-MiniLM-L6-v2"

    # issue regex for matching issue grammar
    # by default, we use GitHub standard
    issue_regex: str = r"(#\d+)"
    issue_mapping: typing.Dict[str, str] = dict()

    data_types: typing.Set[str] = {MetadataConstant.DATA_TYPE_COMMIT_MSG, MetadataConstant.DATA_TYPE_ISSUE}


class Storage(object):
    def __init__(self, config: StorageConfig = None):
        if not config:
            config = StorageConfig()
        self.config = config

        self.chromadb: typing.Optional[API] = None
        self.chromadb_collection: typing.Optional[Collection] = None

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

    def process_commit_msg(self, file: FileContext, collection: Collection):
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
                id=f"{file.name}|{each.hexsha}|{MetadataConstant.DATA_TYPE_COMMIT_MSG}"
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

    def process_issue(self, file: FileContext, collection: Collection):
        regex = re.compile(self.config.issue_regex)

        targets = []
        for each in file.commits:
            issue_id_list = regex.findall(each.message)
            issue_contents = []
            for each_issue in issue_id_list:
                each_issue_content = self.process_issue_id_to_title(each_issue)
                if not each_issue_content:
                    continue
                issue_contents.append(each_issue_content)
            # END issue loop

            if not issue_contents:
                continue
            item = StorageDoc(
                document=os.sep.join(issue_contents),
                metadata={
                    MetadataConstant.KEY_SOURCE: file.name,
                    MetadataConstant.KEY_COMMIT_SHA: str(each.hexsha),
                    MetadataConstant.KEY_DATA_TYPE: MetadataConstant.DATA_TYPE_ISSUE,
                },
                id=f"{file.name}|{each.hexsha}|{MetadataConstant.DATA_TYPE_ISSUE}"
            )
            targets.append(item)
        # END commit loop

        for each in targets:
            collection.add(
                documents=[each.document],
                metadatas=[each.metadata],
                ids=[each.id],
            )

    def process_file_ctx(self, file: FileContext, collection: Collection):
        process_dict = {
            MetadataConstant.DATA_TYPE_ISSUE: self.process_issue,
            MetadataConstant.DATA_TYPE_COMMIT_MSG: self.process_commit_msg
        }
        for each in self.config.data_types:
            if each not in process_dict:
                raise SrcTagException(f"invalid data type: {each}")
            process_dict[each](file, collection)

    def embed_file(self, file: FileContext):
        if not file.commits:
            logger.warning(f"no related commits found: {file.name}")
            return

        self.init_chroma()
        self.process_file_ctx(file, self.chromadb_collection)

    def embed_ctx(self, ctx: RuntimeContext):
        self.init_chroma()
        logger.info("start embedding source files")
        for each_file in tqdm(ctx.files.values()):
            self.embed_file(each_file)
        logger.info("embedding finished")
