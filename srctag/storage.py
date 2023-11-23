import os
import typing

import chromadb
from chromadb import API
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pydantic_settings import BaseSettings
from tqdm import tqdm
from loguru import logger

from srctag.model import FileContext, RuntimeContext


class StorageConfig(BaseSettings):
    db_path: str = ""
    collection_name: str = "default_collection"

    # English: paraphrase-MiniLM-L6-v2
    # Multi langs: paraphrase-multilingual-MiniLM-L12-v2
    st_model_name: str = "paraphrase-MiniLM-L6-v2"


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
        )

    def process_file_ctx_to_doc(self, file: FileContext) -> str:
        """ can be overwritten for custom processing """
        sentences = [each.message.split(os.linesep)[0] for each in file.commits]
        doc = os.linesep.join(sentences)
        return doc

    def embed_file(self, file: FileContext):
        if not file.commits:
            logger.warning(f"no related commits found: {file.name}")
            return

        doc = self.process_file_ctx_to_doc(file)
        self.init_chroma()
        self.chromadb_collection.add(
            documents=[doc],
            metadatas=[{"source": file.name}],
            ids=[file.name],
        )

    def embed_ctx(self, ctx: RuntimeContext):
        self.init_chroma()
        logger.debug("start embedding source files")
        for each_file in tqdm(ctx.files.values()):
            self.embed_file(each_file)
        logger.debug("embedding finished")
