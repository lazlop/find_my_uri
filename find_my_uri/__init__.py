"""
Find My URI - A SPARQL-based URI finder using vector database for semantic similarity matching.

This package provides tools for loading ontology classes from TTL files and searching
for URIs using semantic similarity matching with vector databases.
"""

from .core import URIEncoder, URIFinder

__version__ = "0.1.0"
__author__ = "lazlop"
__email__ = "your-email@example.com"

__all__ = ["URIEncoder", "URIFinder"]
