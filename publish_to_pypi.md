# Publishing to PyPI

This document explains how to publish the `find-my-uri` package to PyPI.

## Prerequisites

1. Install twine for uploading to PyPI:
   ```bash
   pip install twine
   ```

2. Create accounts on:
   - [PyPI](https://pypi.org/account/register/) (for production)
   - [TestPyPI](https://test.pypi.org/account/register/) (for testing)

## Steps to Publish

### 1. Test on TestPyPI First

Upload to TestPyPI to verify everything works:

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ find-my-uri
```

### 2. Publish to PyPI

Once tested, upload to the main PyPI:

```bash
# Upload to PyPI
twine upload dist/*
```

### 3. Install from PyPI

After publishing, users can install with:

```bash
pip install find-my-uri
```

## Package Usage

After installation, users can:

1. Use the CLI tool:
   ```bash
   find-my-uri
   ```

2. Use as a Python module:
   ```bash
   python -m find_my_uri
   ```

3. Import in Python code:
   ```python
   from find_my_uri import URIFinder
   
   finder = URIFinder()
   results = finder.find_similar_uris("temperature", n_results=5)
   ```

## Version Management

To release a new version:

1. Update the version in `pyproject.toml`
2. Rebuild the package: `python -m build`
3. Upload the new version: `twine upload dist/*`

## Authentication

For automated publishing, you can use API tokens:

1. Generate an API token on PyPI
2. Create a `.pypirc` file in your home directory:
   ```ini
   [distutils]
   index-servers = pypi

   [pypi]
   username = __token__
   password = your-api-token-here
