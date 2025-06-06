"""
SPARQL-based URI finder using vector database for class name matching.

This module loads class names from TTL files using SPARQL queries and stores them
in a vector database for efficient URI lookup and similarity matching.
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import logging

# Core dependencies
from rdflib import Graph, Namespace, URIRef, Literal

import chromadb
from chromadb.utils import embedding_functions
# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


class URIEncoder:
    """
    A class to find URIs using SPARQL queries and vector similarity matching.
    """
    
    def __init__(self, 
                 ttl_directories: List[str],
                 vector_db_path: Optional[str],
                 embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize the URI finder.
        
        Args:
            ttl_directories: List of directories containing TTL files
            vector_db_path: Path to store the vector database
            embedding_model: Name of the sentence transformer model to use
        """
        self.ttl_directories = ttl_directories
        self.vector_db_path = vector_db_path
        self.embedding_model_name = embedding_model
        
        # Initialize components
        self.graph = Graph()
        self.class_data = []
        self.client = None
        self.collection = None
        self.embedding_model = embedding_model
        
        # Bind common namespaces
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        self.graph.bind("s223", S223)
        self.graph.bind("watr", WATR)
        
        # Initialize vector database and embedding model
        self._initialize_vector_db()
        self._initialize_embedding_model()
        
    def _initialize_vector_db(self):
        """Initialize ChromaDB client and collection."""
        try:
            if not self.vector_db_path:
                self.client = chromadb.Client()
            else:
                self.client = chromadb.PersistentClient(path=self.vector_db_path)
            self.collection = self.client.get_or_create_collection(
                name="ontology_classes",
                metadata={"description": "Ontology class names and URIs",
                          "hnsw:space": "cosine"} 
                # Don't have to use cosine, could use default. They have slightly different performance
            )
            logger.info(f"Vector database initialized at {self.vector_db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            
    def _initialize_embedding_model(self):
        """Initialize the sentence transformer model."""
        self.embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
            self.embedding_model_name
        )
    
    def load_ttl_files(self, file_patterns: List[str] = None) -> int:
        """
        Load TTL files from specified directories.
        
        Args:
            file_patterns: List of file patterns to match (e.g., ['*.ttl', '*.owl'])
            
        Returns:
            Number of files loaded
        """
        file_patterns = ['*.ttl']
            
        files_loaded = 0
        
        for directory in self.ttl_directories:
            if not os.path.exists(directory):
                logger.warning(f"Directory {directory} does not exist, skipping")
                continue
                
            for pattern in file_patterns:
                file_path = os.path.join(directory, "**", pattern)
                files = glob.glob(file_path, recursive=True)
                
                for file in files:
                    try:
                        logger.info(f"Loading {file}")
                        self.graph.parse(file, format="turtle")
                        files_loaded += 1
                    except Exception as e:
                        logger.error(f"Failed to load {file}: {e}")
                        
        logger.info(f"Loaded {files_loaded} TTL files into graph")
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
        # ?comment 
        # ?type 
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
                # comment = str(row.comment) if row.comment else ""
                # class_type = str(row.type) if row.type else "unknown"
                
                class_info = {
                    'uri': class_uri,
                    'label': label,
                    # 'comment': comment,
                    # 'type': class_type,
                    'local_name': self._extract_local_name(class_uri),
                    'namespace': self._extract_namespace(class_uri)
                }
                classes.append(class_info)
                
            logger.info(f"Extracted {len(classes)} classes from ontology")
            
        except Exception as e:
            logger.error(f"SPARQL query failed: {e}")
            
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
    
    def build_vector_database(self) -> int:
        """
        Build the vector database with class and property information.
        
        Args:
            include_properties: Whether to include properties in addition to classes
            
        Returns:
            Number of items added to the database
        """
        if not self.collection or not self.embedding_model:
            logger.error("Vector database or embedding model not initialized")
            return 0
        
        # Extract classes and properties
        classes = self.extract_classes_with_sparql()
        items = classes.copy()

        if not items:
            logger.warning("No classes or properties found to add to vector database")
            return 0
        
        # Prepare data for vector database
        documents = []
        metadatas = []
        ids = []
        all_ids = self.collection.get()['ids']
        for i, item in enumerate(items):
            # Create searchable text combining label, local name, and comment
            id = item['uri']
            if id in all_ids:
                # logger.info(f"Skipping {id} as it already exists in vector database")
                continue
            if id in ids:
                # logger.info(f"Skipping duplicate id {id}")
                continue
            # searchable_text = f"{item['local_name']}"
            searchable_text = f"{item['local_name']}: {item['label']}"
            print(searchable_text)
            documents.append(searchable_text)
            metadatas.append({
                'uri': item['uri'],
                'label': item['label'],
                # 'comment': item['comment'],
                # 'type': item['type'],
                'local_name': item['local_name'],
                'namespace': item['namespace']
            })
            # ids.append(f"{item['type']}_{i}")
            ids.append(item['uri'])
        
        if ids:
            logger.info(f"Adding {len(items)} items to vector database")       
            # Add to vector database
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            return len(items)
    def find_similar_uris(self, query: str, n_results: int = 5, print_results = True) -> List[Dict]:
        """
        Find URIs similar to the given query string.
        
        Args:
            query: Search query string
            n_results: Number of results to return
            
        Returns:
            List of dictionaries containing similar URIs and metadata
        """
        if not self.collection:
            logger.error("Vector database not initialized")
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            similar_uris = []
            if results['metadatas'] and results['distances']:
                for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                    result = metadata.copy()
                    result['similarity_score'] = 1 - distance  # Convert distance to similarity
                    similar_uris.append(result)
                    if print_results:
                        print(f"  {result['local_name']} ({result['uri']}) - Score: {result['similarity_score']:.3f}")
            
            return similar_uris
            
        except Exception as e:
            logger.error(f"Failed to find similar URIs: {e}")
            return []
    
class URIFinder:
    def __init__(self, vector_db_path: str, 
                 embedding_model: str = "all-MiniLM-L6-v2"):
        self.vector_db_path = vector_db_path
        self.client = None
        self.collection = None
        self.embedding_model = None
        self.embedding_model_name = embedding_model
        
        self._initialize_vector_db()
        self._initialize_embedding_model()
        
    def _initialize_vector_db(self):
        """Initialize ChromaDB client and collection."""
        self.client = chromadb.PersistentClient(path=self.vector_db_path)
        self.collection = self.client.get_or_create_collection(
                name="ontology_classes",
                metadata={"description": "Ontology class names and URIs",
                          "hnsw:space": "cosine"} 
            )
    def _initialize_embedding_model(self):
        """Initialize the sentence transformer model."""
        self.embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
            self.embedding_model_name
        )
    
    def _resolve_namespace_filter(self, namespace_input: str) -> str:
        """Resolve namespace input to full namespace URI."""
        # If it's an abbreviation, convert to full namespace
        if namespace_input in ABBREV_TO_NAMESPACE:
            return ABBREV_TO_NAMESPACE[namespace_input]
        # If it's already a full namespace, return as is
        return namespace_input
    
    def _get_namespace_abbrev(self, namespace: str) -> str:
        """Get namespace abbreviation from full namespace URI."""
        return NAMESPACE_MAP.get(namespace, namespace)

    def find_similar_uris(self, query: str,namespace: str = None, n_results: int = 5, print_results = False) -> List[Dict]:
        """
        Find URIs similar to the given query string.
        
        Args:
            query: Search query string
            namespace: Namespace filter (can be abbreviation like 'S223' or full URI)
            n_results: Number of results to return
            
        Returns:
            List of dictionaries containing similar URIs and metadata
        """
        if not self.collection:
            logger.error("Vector database not initialized")
            return []
        
        try:
            if namespace:
                # Resolve namespace abbreviation to full URI
                resolved_namespace = self._resolve_namespace_filter(namespace)
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where={"namespace": str(resolved_namespace)}
                )
            else:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
            
            similar_uris = []
            if results['metadatas'] and results['distances']:
                for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                    result = metadata.copy()
                    result['similarity_score'] = 1 - distance  # Convert distance to similarity
                    # Add namespace abbreviation for display
                    result['namespace_abbrev'] = self._get_namespace_abbrev(result['namespace'])
                    similar_uris.append(result)
                    if print_results:
                        print(f"  {result['local_name']} ({result['uri']}) - Score: {result['similarity_score']:.3f}")
                    
            return similar_uris
            
        except Exception as e:
            logger.error(f"Failed to find similar URIs: {e}")
            return []