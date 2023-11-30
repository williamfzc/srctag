import chromadb
import click

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger

from srctag.collector import Collector, FileLevelEnum
from srctag.storage import Storage
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
def tag(repo_root, max_depth_limit, include_regex, tags_file, output_path, file_level, st_model):
    """ tag your repo """
    collector = Collector()
    collector.config.repo_root = repo_root
    collector.config.max_depth_limit = max_depth_limit
    collector.config.include_regex = include_regex
    collector.config.file_level = file_level

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


if __name__ == '__main__':
    cli()
