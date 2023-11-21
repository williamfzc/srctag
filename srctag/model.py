import typing

from git import Commit


class FileContext(object):
    def __init__(self, name: str):
        self.name: str = name
        self.commits: typing.List[Commit] = []

        # todo: should contain float values for score
        self.tags: typing.Set[str] = set()


class RuntimeContext(object):
    def __init__(self):
        self.files: typing.Dict[str, FileContext] = dict()
        self.tags: typing.Set[str] = set()


class SrcTagException(BaseException):
    pass
