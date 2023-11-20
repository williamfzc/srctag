import os
import re
import typing

import chromadb
import git
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from git import Commit, Repo
from loguru import logger
from pydantic_settings import BaseSettings


class FileContext(object):
    def __init__(self, name: str):
        self.name: str = name
        self.commits: typing.List[Commit] = []


class RuntimeContext(object):
    def __init__(self):
        self.files: typing.Dict[str, FileContext] = dict()


class SrcTagConfig(BaseSettings):
    repo_root: str = "."

    # file scope
    include_regex: str = ""
    max_depth_limit: int = 128


class SrcTagException(BaseException):
    pass


class CollectorLayer(object):
    def __init__(self, config: SrcTagConfig = None):
        if not config:
            config = SrcTagConfig()
        self.config = config

    def collect_metadata(self) -> RuntimeContext:
        exc = self._check_env()
        if exc:
            raise SrcTagException() from exc

        logger.debug("git metadata collecting ...")
        ctx = RuntimeContext()
        self._collect_files(ctx)
        self._collect_histories(ctx)

        logger.debug("metadata ready")
        return ctx

    def _check_env(self) -> typing.Optional[BaseException]:
        try:
            repo = git.Repo(self.config.repo_root, search_parent_directories=True)
            # if changed after search
            self.config.repo_root = repo.git_dir
        except BaseException as e:
            return e
        return None

    def _collect_files(self, ctx: RuntimeContext):
        """collect all files which tracked by git"""
        git_repo = git.Repo(self.config.repo_root)
        git_track_files = set([each[1].path for each in git_repo.index.iter_blobs()])

        include_regex = None
        if self.config.include_regex:
            include_regex = re.compile(self.config.include_regex)

        for each in git_track_files:
            if include_regex:
                if not include_regex.match(each):
                    continue

            ctx.files[each] = FileContext(each)

        logger.debug(f"file {len(ctx.files)} collected")

    def _collect_history(self, repo: Repo, file_path: str) -> typing.List[Commit]:
        kwargs = {
            "paths": file_path,
        }
        if self.config.max_depth_limit != -1:
            kwargs["max_count"] = self.config.max_depth_limit

        result = []
        for commit in repo.iter_commits(**kwargs):
            result.append(commit)
        return result

    def _collect_histories(self, ctx: RuntimeContext):
        git_repo = git.Repo(self.config.repo_root)

        for each_file, each_file_ctx in ctx.files.items():
            commits = self._collect_history(git_repo, each_file)
            each_file_ctx.commits = commits
            logger.debug(f"file {each_file} ready")


class Storage(object):
    def __init__(self):
        self.chromadb = chromadb.PersistentClient()
        self.chromadb_collection = self.chromadb.get_or_create_collection(
            "commits",
            embedding_function=SentenceTransformerEmbeddingFunction(),
        )

    def embed_file(self, file: FileContext):
        sentences = [
            each.message.split(os.linesep)[0]
            for each in file.commits
        ]

        self.chromadb_collection.add(
            documents=[os.linesep.join(sentences)], metadatas=[{"source": file.name}], ids=[file.name]
        )
