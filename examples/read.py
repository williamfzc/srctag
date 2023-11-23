from srctag.storage import Storage
from srctag.tagger import Tagger

storage = Storage()
storage.config.db_path = "./chroma"
tagger = Tagger()
tagger.config.tags = ["storage"]
tag_dict = tagger.tag(storage)
print(tag_dict)
tag_dict.export_csv()
topics = tag_dict.top_n_tags("srctag/storage.py", 5)
print(topics)
