<h1><code>init-provider</code></h1>

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/init-provider)
![PyPI - Status](https://img.shields.io/pypi/status/init-provider)
![PyPI - License](https://img.shields.io/pypi/l/init-provider)

Lazy just-in-time dependency-aware initialization and instance provider.
Async and thread-safe, with minimal overhead.

> Imagine a dataclass but there is only one instance of it.
> And it can depend on other providers. And you can directly
> access all of its methods and fields without creating an instance
> without having to initialize it first.
> Provider will take care of it for you.

Table of Contents:

- [Quick start example](#quick-start-example)
- [Installation](#installation)

# Quick start example

The example below can run as-is.

```python
{% include "basic.py" %}
```

If you close the project and run this example, you will see the same output:

```shell
$ uv run python examples/basic.py
{% include "basic.log" %}
```

# Installation

The package is available on PyPI. It has no dependencies and is implemented
in pure Python. Compatible with Python 3.10 and higher.

```bash
# Using pip
pip install init-provider

# Using uv
uv add init-provider
```
