import subprocess
import typing

import chromadb
import click
import networkx
import networkx as nx
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger

from srctag.collector import Collector, FileLevelEnum
from srctag.storage import Storage, MetadataConstant
from srctag.tagger import Tagger


@click.group()
def cli():
    pass


@cli.command()
def prepare():
    """ usually used for pre-downloading sentence-transformer models """

    logger.info("Start checking env. It may takes a few minutes for downloading models ...")
    # try to embed
    chromadb_cli = chromadb.Client()
    collection = chromadb_cli.get_or_create_collection(
        "testonly",
        embedding_function=SentenceTransformerEmbeddingFunction(),
    )
    collection.add(
        documents=["doc"],
        ids=["id"],
    )
    assert collection.count() == 1
    click.echo("ok.")


@cli.command()
@click.option("--repo-root", default=".", help="Repository root directory")
@click.option("--max-depth-limit", default=-1, help="Maximum depth limit")
@click.option("--include-regex", default="", help="File include regex pattern")
@click.option("--tags-file", type=click.File("r"), default="./srctag.txt", help="Path to a text file containing tags")
@click.option("--output-path", default="", help="Output file path for CSV")
@click.option("--file-level", default=FileLevelEnum.FILE.value, help="Scan file level, FILE or DIR, default to FILE")
@click.option("--st-model", default="", help="Sentence Transformer Model")
@click.option("--commit-include-regex", default="", help="Commit message include regex pattern")
def tag(repo_root, max_depth_limit, include_regex, tags_file, output_path, file_level, st_model, commit_include_regex):
    """ tag your repo """
    collector = Collector()
    collector.config.repo_root = repo_root
    collector.config.max_depth_limit = max_depth_limit
    collector.config.include_regex = include_regex
    collector.config.file_level = file_level
    collector.config.commit_include_regex = commit_include_regex

    ctx = collector.collect_metadata()
    storage = Storage()
    if st_model:
        storage.config.st_model_name = st_model
    storage.embed_ctx(ctx)
    tagger = Tagger()

    assert tags_file, "no tag file provided"
    tags = [each.strip() for each in tags_file.read().splitlines()]

    tagger.config.tags = tags
    tag_dict = tagger.tag(storage)

    if output_path:
        tag_dict.export_csv(path=output_path)
    else:
        tag_dict.export_csv()


@cli.command()
@click.option("--repo-root", default=".", help="Repository root directory")
@click.option("--max-depth-limit", default=-1, help="Maximum depth limit")
@click.option("--include-regex", default="", help="File include regex pattern")
@click.option("--file-level", default=FileLevelEnum.FILE.value, help="Scan file level, FILE or DIR, default to FILE")
@click.option("--output-path", default="srctag.dot", help="Output file path for DOT")
@click.option("--issue-regex", default="", help="Issue regex")
def graph(repo_root, max_depth_limit, include_regex, file_level, output_path, issue_regex):
    """ create relations graph from your repo """
    collector = Collector()
    collector.config.repo_root = repo_root
    collector.config.max_depth_limit = max_depth_limit
    collector.config.include_regex = include_regex
    collector.config.file_level = file_level
    if issue_regex:
        collector.config.issue_regex = issue_regex

    ctx = collector.collect_metadata()
    relation_graph = ctx.relations
    render_dot(relation_graph, output_path)


@cli.command()
@click.option("--repo-root", default=".", help="Repository root directory")
@click.option("--max-depth-limit", default=-1, help="Maximum depth limit")
@click.option("--diff-target", default="HEAD~1", help="diff target rev")
@click.option("--file-level", default=FileLevelEnum.FILE.value, help="Scan file level, FILE or DIR, default to FILE")
@click.option("--output-path", default="srctag.dot", help="Output file path for DOT")
@click.option("--batch", default=1, help="")
@click.option("--issue-regex", default="", help="Issue regex")
def diff(repo_root, max_depth_limit, diff_target, file_level, output_path, batch, issue_regex):
    """ create relations graph from your repo, with diff """
    base_file_set = get_git_diff_files(diff_target)
    total_file_set = base_file_set
    logger.info(f"base file set: {base_file_set}")

    for i in range(batch):
        collector = Collector()
        collector.config.repo_root = repo_root
        collector.config.max_depth_limit = max_depth_limit
        collector.config.file_level = file_level
        collector.config.include_file_list = base_file_set
        if issue_regex:
            collector.config.issue_regex = issue_regex

        ctx = collector.collect_metadata()

        # enlarge this file set
        file_set = set(ctx.files.keys())
        # network graph
        for each in file_set:
            if not ctx.relations.has_node(each):
                logger.warning(f"node {each} not in graph")
                continue

            issues = set()
            for each_node in ctx.relations.neighbors(each):
                if ctx.relations.nodes[each_node]["node_type"] != MetadataConstant.KEY_ISSUE_ID:
                    continue
                issues.add(each_node)
            # END issue query

            for each_issue in issues:
                related_files = ctx.relations.neighbors(each_issue)
                file_set = file_set.union(related_files)

        # END file query

        logger.info(f"batch {i} end, files: {len(base_file_set)} -> {len(file_set)}")
        new_file_set = file_set - total_file_set
        if not new_file_set:
            logger.info(f"file range search ready: {len(total_file_set)}")
            break
        # update base scope, and run again
        total_file_set = file_set
        base_file_set = new_file_set
    # END loop batch

    collector = Collector()
    collector.config.repo_root = repo_root
    collector.config.max_depth_limit = max_depth_limit
    collector.config.file_level = file_level
    collector.config.include_file_list = total_file_set
    if issue_regex:
        collector.config.issue_regex = issue_regex
    ctx = collector.collect_metadata()
    relation_graph = ctx.relations
    render_dot(relation_graph, output_path)


def get_git_diff_files(target: str) -> typing.Set[str]:
    result = subprocess.check_output(['git', 'diff', target, '--name-only'], text=True)
    diff_files = result.splitlines()
    return set(diff_files)


def render_dot(relation_graph: networkx.Graph, output: str):
    node_colors = {
        MetadataConstant.KEY_SOURCE: 'tomato',
        MetadataConstant.KEY_ISSUE_ID: 'lightgreen',
        MetadataConstant.KEY_COMMIT_SHA: 'lightblue',
    }
    node_color_mapping = {node: node_colors.get(data.get('node_type', 'default'), 'lightgray') for node, data in
                          relation_graph.nodes(data=True)}
    for node, color in node_color_mapping.items():
        relation_graph.nodes[node]['color'] = color

    nx.drawing.nx_pydot.write_dot(relation_graph, output)
    logger.info("rendered graph to %s", output)


if __name__ == '__main__':
    cli()
