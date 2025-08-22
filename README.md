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
- **Persistent storage**: Stores commonly used ontologies for easy retrieval

## Supported Ontologies

This can be adjusted in the future - but is intended as a tool for a coupe projects I am working on 

- **S223**: ASHRAE Standard 223 (Building automation systems)
- **WATR**: Water ontology 
- **UNIT**: QUDT units vocabulary
- **QK**: QUDT quantity kinds
- **RDF/RDFS/OWL**: Standard semantic web vocabularies

## Installation

1. You don't even have to clone or install the repository! You can just run:
```bash
uvx --from 'find_my_uri @ git+https://github.com/lazlop/find_my_uri.git' find-my-uri
```
Be aware, it will take a little while to download the package (which includes the embedded URIs) and the embedding model

OR 

1. Clone the repository:
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
and run the package
3. 
```bash
. .venv/bin/activate
python -m find_my_uri
```

pip install from this repo (similarly done to uvx), or clone then build and install locally, as so:
```bash
python -m build
pip install dist/find_my_uri-0.1.0-py3-none-any.whl
```
there's almost too many options...

## Usage

### Interactive CLI

Run the interactive command-line interface:

```bash
find-my-uri
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
> terminal unit 

Searching for: 'terminal unit'
Showing top 3 results:
--------------------------------------------------
 1. TerminalUnit
    URI: http://data.ashrae.org/standard223#TerminalUnit
    Namespace: S223
    label: Terminal Unit
    Similarity: 0.824

 2. FanPoweredTerminal
    URI: http://data.ashrae.org/standard223#FanPoweredTerminal
    Namespace: S223
    label: Fan Powered Air Terminal
    Similarity: 0.427

 3. SingleDuctTerminal
    URI: http://data.ashrae.org/standard223#SingleDuctTerminal
    Namespace: S223
    label: Single Duct Terminal.
    Similarity: 0.425

# Limit results
> flow rate -n 1

Searching for: 'flow rate'
Showing top 1 results:
--------------------------------------------------
 1. MassFlowRate
    URI: http://qudt.org/vocab/quantitykind/MassFlowRate
    Namespace: QK
    label: Mass Flow Rate
    Similarity: 0.774

# Filter by namespace
> fahrenheit -ns UNIT

Searching for: 'fahrenheit'
Filtering by namespace: UNIT
Showing top 3 results:
--------------------------------------------------
 1. DEG_F
    URI: http://qudt.org/vocab/unit/DEG_F
    Namespace: UNIT
    label: Degree Fahrenheit
    Similarity: 0.691

 2. IN-PER-DEG_F
    URI: http://qudt.org/vocab/unit/IN-PER-DEG_F
    Namespace: UNIT
    label: Inch per Degree Fahrenheit
    Similarity: 0.660

 3. LB-DEG_F
    URI: http://qudt.org/vocab/unit/LB-DEG_F
    Namespace: UNIT
    label: Pound Degree Fahrenheit
    Similarity: 0.622

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
