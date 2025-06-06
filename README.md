# Find My URI

URI finder that uses a vector database for semantic similarity matching of ontology classes. This tool helps users discover relevant URIs from water and building ontologies by searching with natural language terms. Currently just uses URIs and labels of some ontologies retrieved via SPARQL.

If you can't remember if the QUDT unit for Fahrenheit is DEG_F, TemperatureFahrenheit, F, or if you can't even spell Fahrenheit correctly - this will help a little bit. 

## Overview

Find My URI loads class definitions from TTL (Turtle) ontology files, extracts class information using SPARQL queries, and stores them in a ChromaDB vector database for efficient semantic search. Users can then search for URIs using natural language terms and get ranked results based on semantic similarity.

## Features

- **SPARQL-based extraction**: Extracts class information from TTL files using SPARQL queries
- **Vector similarity search**: Uses sentence transformers for semantic matching
- **Multiple ontology support**: Supports ASHRAE Standard 223, water ontology, QUDT units, and more
- **Interactive CLI**: Command-line interface for easy searching
- **Namespace filtering**: Filter results by specific ontology namespaces
- **Persistent storage**: Uses ChromaDB for efficient vector storage and retrieval

## Supported Ontologies

This can be adjusted in the future - but is intended as a tool for a coupe projects I am working on 

- **S223**: ASHRAE Standard 223 (Building automation systems)
- **WATR**: Water ontology 
- **UNIT**: QUDT units vocabulary
- **QK**: QUDT quantity kinds
- **RDF/RDFS/OWL**: Standard semantic web vocabularies

## Installation

0. You don't even have to clone the repository! You can just run:
```bash
uvx --from 'find_my_uri @ git+https://github.com/lazlop/find_my_uri.git' find-my-uri
```

2. Clone the repository:
```bash
git clone <repository-url>
cd find_my_uri
```

2. Install dependencies using uv (recommended) or pip:
```bash
# Using uv
uv sync

# Or using pip
pip install -e .
```

## Usage

### Interactive CLI

Run the interactive command-line interface:

```bash
python uricli.py
```

The CLI provides several commands:

- `help` - Show available commands and examples
- `build` - Build/update the vector database from TTL files
- `quit`/`exit`/`q` - Exit the utility
- `<search_term>` - Search for URIs similar to the term
- `<search_term> -n <num>` - Limit results to specified number
- `<search_term> -ns <namespace>` - Filter by namespace abbreviation

### Example Searches

```bash
# Basic search
> temperature

# Limit results
> flow rate -n 10

# Filter by namespace
> pump -ns S223
> meter -ns UNIT
```

### Programmatic Usage

```python
from find_my_uri import URIFinder

# Initialize finder with existing vector database
finder = URIFinder(vector_db_path="./vector_db")

# Search for similar URIs
results = finder.find_similar_uris("temperature sensor", n_results=5)

for result in results:
    print(f"URI: {result['uri']}")
    print(f"Label: {result['label']}")
    print(f"Similarity: {result['similarity_score']:.3f}")
```

## Project Structure

```
find_my_uri/
├── find_my_uri.py      # Main module with URIEncoder and URIFinder classes
├── uricli.py           # Interactive command-line interface
├── pyproject.toml      # Project configuration and dependencies
├── vector_db/          # ChromaDB vector database storage
└── README.md           # This file
```

## Dependencies

Key dependencies include:

- **rdflib**: RDF graph manipulation and SPARQL queries
- **chromadb**: Vector database for similarity search
- **sentence-transformers**: Semantic embeddings
- **buildingmotif**: Building ontology framework
- **pyontoenv**: Ontology environment management

## Configuration

Provide file paths for loading ontologies using the .env file. 

The default configuration in `uricli.py` expects TTL files in:
- `../water_ontology/water/`
- `../water_ontology/s223`

Vector database is stored in `./vector_db/`

## How It Works

1. **Loading**: TTL files are loaded into an RDF graph using rdflib
2. **Extraction**: SPARQL queries extract class information (URI, label, namespace)
3. **Embedding**: Class names and labels are converted to vector embeddings
4. **Storage**: Embeddings and metadata are stored in ChromaDB
5. **Search**: User queries are embedded and matched against stored vectors
6. **Ranking**: Results are ranked by cosine similarity and returned

## License

see LICENSE

## AI Disclaimer 

Mostly created using various LLMs and Cline

## TODO Items

Constituents and Media have very similar names in 223. I will have to pull in more than the label information to let you distinguish between them. There may be some possible performance improvements. 
