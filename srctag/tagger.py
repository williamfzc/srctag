import typing

from pydantic_settings import BaseSettings


class TaggerConfig(BaseSettings):
    tags: typing.Set[str] = set()


class Tagger(object):
    """ load feature map, search related files, and tag them """

    def __init__(self, config: TaggerConfig = None):
        if not config:
            config = TaggerConfig()
        self.config = config

    def tag(self):
        pass
