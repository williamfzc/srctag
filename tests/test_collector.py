import os

import networkx as nx
from matplotlib import pyplot as plt

from srctag.collector import Collector


def test_tagger_specific():
    collector = Collector()
    collector.config.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    collector.config.include_file_list = ["README.md"]
    ctx = collector.collect_metadata()
    assert len(ctx.files) == 1


def test_relations():
    collector = Collector()
    collector.config.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ctx = collector.collect_metadata()
    relations = ctx.relations
    assert relations
    assert relations.nodes
    assert relations.edges
    nx.draw(relations, with_labels=True, font_weight='bold', node_size=400,
            font_color='black', font_size=4, edge_color='gray', alpha=0.7)
    plt.savefig("my_graph.svg")
