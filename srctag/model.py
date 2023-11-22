import typing

from git import Commit


class FileContext(object):
    def __init__(self, name: str):
        self.name: str = name
        self.commits: typing.List[Commit] = []


class RuntimeContext(object):
    def __init__(self):
        self.files: typing.Dict[str, FileContext] = dict()


class SrcTagException(BaseException):
    pass
