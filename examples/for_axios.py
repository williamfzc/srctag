import pathlib
import sys
import warnings

import networkx as nx
from matplotlib import pyplot as plt

from srctag.collector import Collector
from srctag.storage import Storage
from srctag.tagger import Tagger

axios_repo = pathlib.Path(__file__).parent.parent / "axios"
if not axios_repo.is_dir():
    warnings.warn(f"clone axios to {axios_repo} first")
    sys.exit(0)

collector = Collector()
collector.config.repo_root = axios_repo
collector.config.max_depth_limit = -1
collector.config.include_regex = r"lib.*"

ctx = collector.collect_metadata()
storage = Storage()
storage.embed_ctx(ctx)
tagger = Tagger()
tagger.config.tags = [
    "XMLHttpRequests from browser",
    "HTTP requests from node.js",
    "Promise API support",
    "Request and response interception",
    "Request and response data transformation",
    "Request cancellation",
    "Automatic JSON data transforms",
    "Automatic serialization of data objects",
    "Client-side XSRF protection"
]
tag_result = tagger.tag(storage)

# access the pandas.DataFrame
print(tag_result.scores_df)

# csv dump
tag_result.export_csv()

# networkx analysis
graph = tag_result.export_networkx()

# sample code for drawing
pos = nx.spring_layout(graph)
node_colors = [graph.nodes[n]['color'] for n in graph.nodes]
edge_weights = [graph.edges[e]['weight'] for e in graph.edges]
nx.draw(graph, pos, with_labels=True, font_weight='bold', node_size=400, node_color=node_colors,
        font_color='black', font_size=4, edge_color='gray', width=edge_weights, alpha=0.7)
plt.savefig("my_graph.svg")
