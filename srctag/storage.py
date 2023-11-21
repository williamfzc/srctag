import os

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pydantic_settings import BaseSettings
from tqdm import tqdm
from loguru import logger

from srctag.model import FileContext, RuntimeContext


class StorageConfig(BaseSettings):
    collection_name: str = "default_collection"

    # English: paraphrase-MiniLM-L6-v2
    # Multi langs: paraphrase-multilingual-MiniLM-L12-v2
    st_model_name: str = "paraphrase-MiniLM-L6-v2"


class Storage(object):
    def __init__(self, config: StorageConfig = None):
        if not config:
            config = StorageConfig()
        self.config = config

        self.chromadb = chromadb.PersistentClient()
        self.chromadb_collection = self.chromadb.get_or_create_collection(
            self.config.collection_name,
            embedding_function=SentenceTransformerEmbeddingFunction(model_name=self.config.st_model_name),
        )

    def embed_file(self, file: FileContext):
        sentences = [
            each.message.split(os.linesep)[0]
            for each in file.commits
        ]

        self.chromadb_collection.add(
            documents=[os.linesep.join(sentences)], metadatas=[{"source": file.name}], ids=[file.name]
        )

    def embed_ctx(self, ctx: RuntimeContext):
        logger.debug("start embedding source files")
        for each_file in tqdm(ctx.files.values()):
            self.embed_file(each_file)
        logger.debug("embedding finished")
