from sentence_transformers import SentenceTransformer
from pathlib import Path
import pickle
import os
import glob
from typing import List, Dict, Tuple, Optional, Union
from rdflib import Graph, Namespace, URIRef, Literal
from dataclasses import dataclass
from pprint import pprint

DEFAULT_EMBEDDING_MODEL = "paraphrase-MiniLM-L3-v2" # or 'all-MiniLM-L6-v2'

"""
SPARQL-based URI finder using vector database for class name matching.

This module loads class names from TTL files using SPARQL queries and stores them
in a vector database for efficient URI lookup and similarity matching.
"""

# Common namespaces
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
S223 = Namespace("http://data.ashrae.org/standard223#")
WATR = Namespace("urn:nawi-water-ontology#")
UNIT = Namespace("http://qudt.org/vocab/unit/")
QK = Namespace("http://qudt.org/vocab/quantitykind/")

# Namespace mapping for abbreviations
NAMESPACE_MAP = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "RDF",
    "http://www.w3.org/2000/01/rdf-schema#": "RDFS", 
    "http://www.w3.org/2002/07/owl#": "OWL",
    "http://data.ashrae.org/standard223#": "S223",
    "urn:nawi-water-ontology#": "WATR",
    "http://qudt.org/vocab/unit/": "UNIT",
    "http://qudt.org/vocab/quantitykind/": "QK"
}

# Reverse mapping for lookup
ABBREV_TO_NAMESPACE = {v: k for k, v in NAMESPACE_MAP.items()}


@dataclass
class URIEncoderConfig:
    """Configuration for URIEncoder"""
    ttl_directories: List[Path]
    data_dir: Path = Path("data")
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    file_patterns: List[str] = None
    
    def __post_init__(self):
        if self.file_patterns is None:
            self.file_patterns = ['*.ttl']
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Convert string paths to Path objects
        self.ttl_directories = [Path(d) for d in self.ttl_directories]


class URIEncoder:
    """
    A class to find URIs using SPARQL queries and vector similarity matching.
    """
    
    def __init__(self, config: URIEncoderConfig):
        """
        Initialize the URI finder.
        
        Args:
            config: Configuration object containing all necessary parameters
        """
        self.config = config
        
        # Initialize components
        self.graph = Graph('Oxigraph')
        self.class_data = []
        self.client = None
        self.collection = None
        
        # Bind common namespaces
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        self.graph.bind("s223", S223)
        self.graph.bind("watr", WATR)
        
        self.embedding_model = SentenceTransformer(self.config.embedding_model)
    
    def load_ttl_files(self) -> int:
        """
        Load TTL files from specified directories.
            
        Returns:
            Number of files loaded
        """
        files_loaded = 0
        
        for directory in self.config.ttl_directories:
            if not directory.exists():
                print(f"Directory {directory} does not exist, skipping")
                continue
                
            for pattern in self.config.file_patterns:
                # Use pathlib's glob for recursive search
                files = list(directory.rglob(pattern))
                
                for file_path in files:
                    try:
                        print(f"Loading {file_path}")
                        self.graph.parse(str(file_path), format="turtle")
                        files_loaded += 1
                    except Exception as e:
                        print(f"Failed to load {file_path}: {e}")
                        
        print(f"Loaded {files_loaded} TTL files into graph")
        return files_loaded
    
    def extract_classes_with_sparql(self) -> List[Dict]:
        """
        Extract class information using SPARQL queries.
        
        Returns:
            List of dictionaries containing class information
        """
        # SPARQL query to extract classes with labels and comments
        query = """
        SELECT DISTINCT 
        ?klass 
        ?label 
        WHERE {
            { ?klass a s223:Class ;
                rdfs:label ?label } 
            UNION 
            { ?klass a watr:Class ;
                rdfs:label ?label }
            UNION 
            { ?klass a qudt:Unit ;
                rdfs:label ?label 
                FILTER (lang(?label) = "en")} 
            UNION 
            { ?klass a qudt:QuantityKind ;
                rdfs:label ?label 
                FILTER (lang(?label) = "en") }

            BIND("rdfs:Class" as ?type)
            
            OPTIONAL { ?klass rdfs:label ?label }
        }
        ORDER BY ?klass
        """
        
        classes = []
        try:
            results = self.graph.query(query)
            
            for row in results:
                class_uri = str(row.klass)
                label = str(row.label) if row.label else self._extract_local_name(class_uri)
                
                class_info = {
                    'uri': class_uri,
                    'label': label,
                    'local_name': self._extract_local_name(class_uri),
                    'namespace': self._extract_namespace(class_uri)
                }
                classes.append(class_info)
                
            print(f"Extracted {len(classes)} classes from ontology")
            
        except Exception as e:
            print(f"SPARQL query failed: {e}")
            
        return classes
    
    def _extract_local_name(self, uri: str) -> str:
        """Extract the local name from a URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    def _extract_namespace(self, uri: str) -> str:
        """Extract the namespace from a URI."""
        if '#' in uri:
            return uri.split('#')[0] + '#'
        elif '/' in uri:
            parts = uri.split('/')
            return '/'.join(parts[:-1]) + '/'
        return uri
    
    def _get_namespace_abbrev(self, namespace: str) -> str:
        """Get namespace abbreviation from full namespace URI."""
        return NAMESPACE_MAP.get(namespace, namespace)
    
    def store_vectors(self, save: bool = True) -> int:
        """
        Build the vector database with class and property information.
        
        Args:
            save: Whether to save the vectors to disk
            
        Returns:
            Number of items added to the database
        """
        # Extract classes and properties
        classes = self.extract_classes_with_sparql()
        items = classes.copy()

        if not items:
            print("No classes or properties found to add to vector database")
            return 0
        
        # Prepare data for vector database
        documents = []
        metadatas = []
        ids = []
        
        for i, item in enumerate(items):
            # Create searchable text combining label, local name, and comment
            id = item['uri']
            if id in ids:
                continue
                
            searchable_text = f"{item['local_name']}: {item['label']}"
            print(searchable_text)
            documents.append(searchable_text)
            
            # Some redundancy in documents and metadatas, just so I don't have to merge data later. 
            metadatas.append({
                'uri': item['uri'],
                'label': item['label'],
                'local_name': item['local_name'],
                'namespace': item['namespace']
            })
            ids.append(item['uri'])
            
        self.metadatas = metadatas
        self.documents = documents
        self.embeddings = self.embedding_model.encode(documents)

        if save:
            metadata_path = self.config.data_dir / 'document_metadata.pickle'
            embeddings_path = self.config.data_dir / 'embeddings.pickle'
            
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.metadatas, f)
            with open(embeddings_path, 'wb') as f:
                pickle.dump(self.embeddings, f)

        return len(items)


@dataclass
class URIFinderConfig:
    """Configuration for URIFinder"""
    data_dir: Path = Path("data")
    embedding_model: str = DEFAULT_EMBEDDING_MODEL


class URIFinder:
    def __init__(self, config: URIFinderConfig):
        self.config = config
        self.client = None
        self.collection = None
        self.embedding_model = SentenceTransformer(self.config.embedding_model)
        
        self._init_store()
        
    def _init_store(self):
        """Initialize the store by loading saved data."""
        metadata_path = self.config.data_dir / 'document_metadata.pickle'
        embeddings_path = self.config.data_dir / 'embeddings.pickle'
        
        if not metadata_path.exists() or not embeddings_path.exists():
            raise FileNotFoundError(
                f"Required data files not found in {self.config.data_dir}. "
                "Please run URIEncoder.store_vectors() first."
            )
        
        with open(metadata_path, 'rb') as f:
            self.metadatas = pickle.load(f)
        with open(embeddings_path, 'rb') as f:
            self.embeddings = pickle.load(f)
    
    def _resolve_namespace_filter(self, namespace_input: str) -> str:
        """Resolve namespace input to full namespace URI."""
        # If it's an abbreviation, convert to full namespace
        if namespace_input in ABBREV_TO_NAMESPACE:
            return ABBREV_TO_NAMESPACE[namespace_input]
        # If it's already a full namespace, return as is
        return namespace_input
    
    def filter_embeddings_ns(self, desired_namespace: str):
        matching_indices = [i for i, d in enumerate(self.metadatas) if d['namespace'] == desired_namespace]
        if len(matching_indices) == 0:
            raise Exception(f'No documents in this namespace {desired_namespace}')
        return self.embeddings[matching_indices], matching_indices
    
    def _get_namespace_abbrev(self, namespace: str) -> str:
        """Get namespace abbreviation from full namespace URI."""
        return NAMESPACE_MAP.get(namespace, namespace)

    def find_similar_uris(self, query: str, namespace: str = None, n_results: int = 5) -> List[Dict]:
        """
        Find URIs similar to the given query string.
        
        Args:
            query: Search query string
            namespace: Namespace filter (can be abbreviation like 'S223' or full URI)
            n_results: Number of results to return
            
        Returns:
            List of dictionaries containing similar URIs and metadata
        """
        
        try:
            if namespace:
                # Resolve namespace abbreviation to full URI
                if namespace not in ABBREV_TO_NAMESPACE.keys():
                    raise ValueError(f"Namespace not known: {namespace}")
                resolved_namespace = self._resolve_namespace_filter(namespace)
                embeddings, filtered_indices = self.filter_embeddings_ns(str(resolved_namespace)) 
            else:
                embeddings = self.embeddings
                filtered_indices = None

            similarities = self.embedding_model.similarity(embeddings, self.embedding_model.encode(query)).squeeze(1)
            topk_indices = similarities.topk(n_results).indices
            if filtered_indices:
                indices = [filtered_indices[i] for i in topk_indices.tolist()]
            else:
                indices = topk_indices.tolist()
            metadata_matches = [self.metadatas[i] for i in indices]
            return metadata_matches
            
        except Exception as e:
            print(f"Failed to find similar URIs: {e}")
            return []


# Example usage
def create_encoder_from_env() -> URIEncoder:
    """Create URIEncoder using environment variables for configuration."""
    ttl_dirs_str = os.getenv("TTL_DIRECTORIES", "")
    if not ttl_dirs_str:
        raise ValueError("TTL_DIRECTORIES environment variable not set")
    
    ttl_directories = [Path(d.strip()) for d in ttl_dirs_str.split(",")]
    
    config = URIEncoderConfig(
        ttl_directories=ttl_directories,
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        embedding_model=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    )
    
    return URIEncoder(config)


def create_finder_from_env() -> URIFinder:
    """Create URIFinder using environment variables for configuration."""
    config = URIFinderConfig(
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        embedding_model=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    )
    
    return URIFinder(config)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    e = create_encoder_from_env()
    e.load_ttl_files()
    e.store_vectors()