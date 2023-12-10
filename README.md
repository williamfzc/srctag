# srctag

[![PyPI version](https://badge.fury.io/py/srctag.svg)](https://badge.fury.io/py/srctag)
[![Smoke Test](https://github.com/williamfzc/srctag/actions/workflows/python-package.yml/badge.svg)](https://github.com/williamfzc/srctag/actions/workflows/python-package.yml)

Tag source files with real-world stories.

## What' s it?

Based on user-provided tag lists, srctag associates files with relevant tags and provides a measure of relevance by
mining the commits.

For example, axios is a famous JavaScript library. We can extract some features (tags) it provides from the README and
pass them to srctag:

| File                                            | XMLHttpRequests | HTTP requests (Node.js) | Promise API support | Request/response interception | Request/response data transformation | Request cancellation | Automatic JSON data transforms | Automatic serialization of data objects | Client-side XSRF protection |
|-------------------------------------------------|-----------------|-------------------------|---------------------|-------------------------------|--------------------------------------|----------------------|--------------------------------|-----------------------------------------|-----------------------------|
| lib/adapters/http.js                            | 1               | 1                       | 1                   | 1                             | 1                                    | 1                    | 1                              | 1                                       | 1                           |
| lib/adapters/xhr.js                             | 0.980769231     | 0.981132075             | 0.980769231         | 0.979591837                   | 0.981132075                          | 0.98                 | 0.98                           | 0.960784314                             | 0.981132075                 |
| lib/utils.js                                    | 0.961538462     | 0.962264151             | 0.961538462         | 0.959183673                   | 0.962264151                          | 0.94                 | 0.96                           | 0.980392157                             | 0.962264151                 |
| lib/platform/browser/index.js                   | 0.942307692     | 0.924528302             | 0.846153846         | 0.795918367                   | 0.830188679                          | 0.72                 | 0.84                           | 0.705882353                             | 0.924528302                 |
| lib/helpers/buildURL.js                         | 0.923076923     | 0.867924528             | 0.884615385         | 0.836734694                   | 0.811320755                          | 0.88                 | 0.82                           | 0.843137255                             | 0.773584906                 |
| lib/core/dispatchRequest.js                     | 0.903846154     | 0.943396226             | 0.903846154         | 0.897959184                   | 0.905660377                          | 0.96                 | 0.86                           | 0.882352941                             | 0.886792453                 |
| lib/helpers/toFormData.js                       | 0.884615385     | 0.905660377             | 0.923076923         | 0.857142857                   | 0.943396226                          | 0.78                 | 0.94                           | 0.941176471                             | 0.867924528                 |
| lib/axios.js                                    | 0.865384615     | 0.773584906             | 0.942307692         | 0.918367347                   | 0.924528302                          | 0.9                  | 0.92                           | 0.901960784                             | 0.943396226                 |
| lib/defaults/index.js                           | 0.846153846     | 0.830188679             | 0.826923077         | 0.87755102                    | 0.886792453                          | 0.86                 | 0.9                            | 0.862745098                             | 0.849056604                 |
| lib/core/Axios.js                               | 0.826923077     | 0.886792453             | 0.865384615         | 0.93877551                    | 0.867924528                          | 0.92                 | 0.88                           | 0.921568627                             | 0.830188679                 |
| lib/core/AxiosError.js                          | 0.807692308     | 0.849056604             | 0.673076923         | 0.816326531                   | 0.773584906                          | 0.84                 | 0.78                           | 0.803921569                             | 0.811320755                 |
| lib/helpers/parseHeaders.js                     | 0.788461538     | 0.811320755             | 0.653846154         | 0.551020408                   | 0.452830189                          | 0.68                 | 0.4                            | 0.450980392                             | 0.339622642                 |
| lib/helpers/isURLSameOrigin.js                  | 0.769230769     | 0.698113208             | 0.403846154         | 0.571428571                   | 0.641509434                          | 0                    | 0.7                            | 0.352941176                             | 0.905660377                 |
| lib/platform/node/index.js                      | 0.75            | 0.735849057             | 0.788461538         | 0.653061224                   | 0.735849057                          | 0.44                 | 0.64                           | 0.529411765                             | 0.735849057                 |
| lib/platform/browser/classes/FormData.js        | 0.730769231     | 0.716981132             | 0.711538462         | 0.428571429                   | 0.716981132                          | 0                    | 0.56                           | 0.078431373                             | 0.698113208                 |
| lib/helpers/fromDataURI.js                      | 0.711538462     | 0.754716981             | 0.769230769         | 0.428571429                   | 0.509433962                          | 0.34                 | 0.42                           | 0.078431373                             | 0.679245283                 |
| lib/platform/index.js                           | 0.692307692     | 0.660377358             | 0.519230769         | 0.367346939                   | 0.566037736                          | 0.44                 | 0.5                            | 0.529411765                             | 0.641509434                 |
| lib/platform/browser/classes/URLSearchParams.js | 0.673076923     | 0.641509434             | 0.807692308         | 0.591836735                   | 0.698113208                          | 0.44                 | 0.74                           | 0.764705882                             | 0.509433962                 |
| lib/helpers/cookies.js                          | 0.653846154     | 0.679245283             | 0.692307692         | 0.306122449                   | 0.641509434                          | 0.42                 | 0.68                           | 0.352941176                             | 0.79245283                  |
| lib/core/transformData.js                       | 0.634615385     | 0.79245283              | 0.75                | 0.734693878                   |

Then we can obtain the relevance of each code file with these tags. You can choose your preferred format to process this
data: CSV, pandas, or even networkx with Graphviz.

![my_graph](https://github.com/williamfzc/srctx/assets/13421694/f6d239b4-a1cc-42f4-bfb0-38bf6421505f)

## How to use?

### Installation

Requires Python 3.8 or later and the sentence-transformers library.

```shell
# For full installation with dependencies
pip install "srctag[embedding]"

# For manual installation of sentence-transformers
pip install srctag
```

### Use as LIB

You can check the links below for more detailed information:

- [examples](./examples)
- [test cases](./tests)

```python
import pathlib
import sys
import warnings

import networkx

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

# dot file dump
graph = tag_result.export_networkx()
networkx.drawing.nx_pydot.write_dot(graph, sys.stdout)
```

### Use as CLI

```shell
➜  examples git:(main) ✗ srctag tag --help
Usage: srctag tag [OPTIONS]

  tag your repo

Options:
  --repo-root TEXT             Repository root directory
  --max-depth-limit INTEGER    Maximum depth limit
  --include-regex TEXT         File include regex pattern
  --tags-file FILENAME         Path to a text file containing tags
  --output-path TEXT           Output file path for CSV
  --file-level TEXT            Scan file level, FILE or DIR, default to FILE
  --st-model TEXT              Sentence Transformer Model
  --commit-include-regex TEXT  Commit message include regex pattern
  --help                       Show this message and exit.
```

## Goal & Motivation

### Diff Analysis

This project was initially created to address the following issue. In complex business projects, there are often
numerous modules with many contributors. The tight coupling between modules can easily lead to changes affecting each
other among developers. Detecting such issues through code review is time-consuming, labor-intensive, and prone to
oversights.

We aim to help evaluate the potential impact of a change on various functionalities, guiding subsequent testing efforts.

Also we have a WIP Github Actions project for supporting PR evaluations:
https://github.com/williamfzc/srctag-action

### API for LLM

With the rise of large language models (LLMs), many teams are considering how to make LLMs understand the entire
codebase.
From the current progress, LLMs can understand details at the code implementation level well, but their understanding of
the business functionalities they represent is limited.

We also hope to use this approach to enable LLMs to establish associations between code files and specific business
functionalities at a lower cost, enhancing their overall understanding of the code repository.

## How it actually works?

- Collector: Collects sufficient metadata from the code repository, such as commit messages.
- Storage: Organizes this metadata and embeds it into a vector database in an appropriate form.
- Tagger: Searches for relevant files based on the existing tag list and further establishes associations.

## License

[Apache 2.0](LICENSE)
