import typing

import networkx
from git import Commit


class FileContext(object):
    def __init__(self, name: str):
        self.name: str = name
        self.commits: typing.List[Commit] = []


class RuntimeContext(object):
    """ shared data between components """
    def __init__(self):
        self.files: typing.Dict[str, FileContext] = dict()
        self.relations = networkx.Graph()


class SrcTagException(BaseException):
    pass
