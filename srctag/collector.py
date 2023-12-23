import functools
import os
import re
import typing
from enum import Enum

import git
from git import Repo, Commit
from loguru import logger
from pydantic_settings import BaseSettings
from tqdm import tqdm

from srctag.model import FileContext, RuntimeContext, SrcTagException
from srctag.storage import MetadataConstant


class FileLevelEnum(str, Enum):
    FILE: str = "FILE"
    DIR: str = "DIR"


class ScanRuleEnum(str, Enum):
    DFS: str = "DFS"
    BFS: str = "BFS"


class CollectorConfig(BaseSettings):
    repo_root: str = "."

    # file name include regex
    include_regex: str = ""
    include_file_list: typing.List[str] = []

    # commit msg include regex
    commit_include_regex: str = ""

    # set -1 to break the limit
    max_depth_limit: int = 16
    file_level: FileLevelEnum = FileLevelEnum.FILE

    # DFS: git log
    # BFS: walk the commits and get each diff files
    scan_rule: ScanRuleEnum = ScanRuleEnum.DFS

    # issue regex for matching issue grammar
    # by default, we use GitHub standard
    issue_regex: str = r"(#\d+)"


class Collector(object):
    def __init__(self, config: CollectorConfig = None):
        if not config:
            config = CollectorConfig()
        self.config = config

    def collect_metadata(self) -> RuntimeContext:
        exc = self._check_env()
        if exc:
            raise SrcTagException() from exc

        logger.info("git metadata collecting ...")
        ctx = RuntimeContext()
        self._collect_files(ctx)

        if self.config.scan_rule == ScanRuleEnum.DFS:
            self._collect_histories(ctx)
        else:
            self._collect_histories_globally(ctx)

        # issue processing and network building
        self._process_relations(ctx)

        logger.info("metadata ready")
        return ctx

    @functools.lru_cache(maxsize=None)
    def _process_diff_from_commit(self, commit: Commit) -> typing.Set[str]:
        ret = set()
        for each_diff in commit.diff():
            each_b_path = each_diff.b_path
            ret.add(each_b_path)
        return ret

    def _process_relations(self, ctx: RuntimeContext):
        """
        collect different relations from metadata

        1. files - issues
        2. files - commits
        """
        regex = re.compile(self.config.issue_regex)

        for each_file in tqdm(ctx.files.values()):
            ctx.relations.add_node(each_file.name, node_type=MetadataConstant.KEY_SOURCE)

            # and the related files
            for each_commit in each_file.commits:
                related_files = self._process_diff_from_commit(each_commit)
                ctx.relations.add_node(each_commit.hexsha, node_type=MetadataConstant.KEY_COMMIT_SHA)
                ctx.relations.add_edge(each_commit.hexsha, each_file.name)

                for each_related in related_files:
                    # commit -> related files
                    ctx.relations.add_node(each_related, node_type=MetadataConstant.KEY_SOURCE)
                    ctx.relations.add_edge(each_commit.hexsha, each_related)
                # END commit -> file

                issue_id_list = regex.findall(each_commit.message)
                for each_issue in issue_id_list:
                    # issue -> file
                    ctx.relations.add_node(each_issue, node_type=MetadataConstant.KEY_ISSUE_ID)
                    ctx.relations.add_edge(each_issue, each_file.name)

                    for each_related in related_files:
                        ctx.relations.add_edge(each_issue, each_related)
                    # END issue -> related files
                # END issue -> file

            # END each file added
        # END file added

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
        if self.config.include_file_list:
            logger.info("use specific file list")
            for each in self.config.include_file_list:
                if each not in git_track_files:
                    logger.warning(f"specific file {each} not in git track, ignored")
                    continue
                ctx.files[each] = FileContext(each)
            # END file list loop
            return
        # END check file list

        include_regex = None
        if self.config.include_regex:
            include_regex = re.compile(self.config.include_regex)

        for each in git_track_files:
            if include_regex:
                if not include_regex.match(each):
                    continue

            if self.config.file_level == FileLevelEnum.FILE:
                ctx.files[each] = FileContext(each)
            elif self.config.file_level == FileLevelEnum.DIR:
                each_dir = os.path.dirname(each)
                ctx.files[each_dir] = FileContext(each_dir)
            else:
                raise SrcTagException(f"invalid file level: {self.config.file_level}")

        logger.info(f"file {len(ctx.files)} collected")

    def _collect_history(self, repo: Repo, file_path: str) -> typing.List[Commit]:
        kwargs = {
            "paths": file_path,
            "no-merges": True,
            "no-walk": True,
            "single-worktree": True,
            "max-count": self.config.max_depth_limit,
        }
        if self.config.commit_include_regex:
            kwargs["grep"] = self.config.commit_include_regex

        result = []
        for commit in repo.iter_commits(**kwargs):
            result.append(commit)
        return result

    def _collect_histories(self, ctx: RuntimeContext):
        git_repo = git.Repo(self.config.repo_root)

        for each_file, each_file_ctx in tqdm(ctx.files.items()):
            commits = self._collect_history(git_repo, each_file)
            each_file_ctx.commits = commits

    def _collect_histories_globally(self, ctx: RuntimeContext):
        git_repo = git.Repo(self.config.repo_root)

        include_regex = None
        if self.config.include_regex:
            include_regex = re.compile(self.config.include_regex)

        commit_include_regex = None
        if self.config.commit_include_regex:
            commit_include_regex = re.compile(self.config.commit_include_regex)

        kwargs = dict()
        if self.config.max_depth_limit != -1:
            kwargs["max_count"] = self.config.max_depth_limit

        for commit in tqdm(list(git_repo.iter_commits(**kwargs))):
            if commit_include_regex:
                if not commit_include_regex.match(commit.message):
                    continue

            for new_file in git_repo.git.show(commit.hexsha, name_only=True).split(
                    os.linesep
            ):
                if include_regex:
                    if not include_regex.match(new_file):
                        continue

                if self.config.file_level == FileLevelEnum.DIR:
                    new_file = os.path.dirname(new_file)

                each_file_ctx = ctx.files.get(new_file, None)
                if each_file_ctx:
                    each_file_ctx.commits.append(commit)
