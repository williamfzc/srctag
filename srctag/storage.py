import typing

import chromadb
from chromadb import API
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from tqdm import tqdm

from srctag.model import FileContext, RuntimeContext


class StorageDoc(BaseModel):
    document: str
    metadata: typing.Dict[str, str]
    id: str


class MetadataConstant(object):
    KEY_SOURCE = "source"
    KEY_COMMIT_SHA = "commit_sha"


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
            # dis range: [0, 1]
            metadata={"hnsw:space": "cosine"}
        )

    def process_file_ctx(self, file: FileContext, collection: Collection):
        """ can be overwritten for custom processing """

        targets = []
        for each in file.commits:
            # keep enough data in metadata for calc the final score
            item = StorageDoc(
                document=each.message,
                metadata={
                    MetadataConstant.KEY_SOURCE: file.name,
                    MetadataConstant.KEY_COMMIT_SHA: str(each.hexsha),
                },
                id=f"{file.name}|{each.hexsha}"
            )
            targets.append(item)

        for each in targets:
            collection.add(
                documents=[each.document],
                metadatas=[each.metadata],
                ids=[each.id],
            )

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
