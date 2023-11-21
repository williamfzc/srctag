from srctag.storage import Storage
from srctag.tagger import Tagger

storage = Storage()
tagger = Tagger()
tagger.config.tags = ["storage"]
tag_dict = tagger.tag(storage)
print(tag_dict)
