#!/usr/bin/env python3
"""
Script to build vector database from TTL files.
This is separate from the main CLI to keep the pip-installable package clean.
"""

from .core import URIEncoder
import argparse
import os

def main():
    """Build vector database from TTL directories."""
    parser = argparse.ArgumentParser(description='Build vector database from TTL files')
    parser.add_argument('ttl_dirs', nargs='+', help='Directories containing TTL files')
    parser.add_argument('--vector-db', required=True, help='Path where to create the vector database')
    parser.add_argument('--embedding-model', default='all-MiniLM-L6-v2', 
                       help='Sentence transformer model to use (default: all-MiniLM-L6-v2)')
    
    args = parser.parse_args()
    
    # Validate TTL directories exist
    for ttl_dir in args.ttl_dirs:
        if not os.path.exists(ttl_dir):
            print(f"Error: TTL directory does not exist: {ttl_dir}")
            return 1
        if not os.path.isdir(ttl_dir):
            print(f"Error: Path is not a directory: {ttl_dir}")
            return 1
    
    print("=== Vector Database Builder ===")
    print(f"TTL directories: {', '.join(args.ttl_dirs)}")
    print(f"Vector database path: {args.vector_db}")
    print(f"Embedding model: {args.embedding_model}")
    print()
    
    try:
        encoder = URIEncoder(
            ttl_directories=args.ttl_dirs, 
            vector_db_path=args.vector_db,
            embedding_model=args.embedding_model
        )
        
        print("Loading TTL files...")
        files_loaded = encoder.load_ttl_files()
        print(f"✓ Loaded {files_loaded} TTL files")
        
        print("Building vector database...")
        items_added = encoder.build_vector_database()
        print(f"✓ Added {items_added} items to the vector database")
        
        print(f"\nVector database successfully created at: {args.vector_db}")
        print("You can now use the find-my-uri CLI tool to search URIs.")
        
    except Exception as e:
        print(f"Error building vector database: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
