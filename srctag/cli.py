import chromadb
import click

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from loguru import logger


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


if __name__ == '__main__':
    cli()
