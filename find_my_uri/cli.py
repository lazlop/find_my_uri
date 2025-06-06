from .core import URIFinder
import importlib.resources

DEFAULT_VECTOR_DB_PATH = str(importlib.resources.path('find_my_uri', 'vector_db'))

def main():
    """Interactive command line utility for searching URIs."""
    print("=== URI Search Utility ===")
    print("This utility searches for URIs in the ontology using semantic similarity.")
    print("Type 'help' for commands or 'quit' to exit.\n")

    finder = URIFinder(vector_db_path=DEFAULT_VECTOR_DB_PATH)
    print("✓ Vector database loaded successfully")
    
    # Interactive search loop
    while True:
        try:
            # Get user input
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
                
            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
                
            elif user_input.lower() == 'help':
                print("\nCommands:")
                print("  help                   - Show this help message")
                print("  quit/exit/q            - Exit the utility")
                print("  <search_term>          - Search for URIs similar to the term")
                print("  <search_term> -n <num> - Limit results to <num> items (default: 3)")
                print("  <search_term> -ns <ns> - Filter by namespace abbreviation")
                print("\nAvailable namespace abbreviations:")
                print("  S223  - ASHRAE Standard 223")
                print("  WATR  - Water ontology")
                print("  UNIT  - QUDT units")
                print("  QK    - QUDT quantity kinds")
                print("  RDF   - RDF namespace")
                print("  RDFS  - RDF Schema")
                print("  OWL   - OWL ontology")
                print("\nExamples:")
                print("  temperature")
                print("  flow rate -n 10")
                print("  pump -ns S223")
                print("  meter -ns UNIT")
                continue
            
            # Parse search parameters
            parts = user_input.split()
            query = parts[0]
            n_results = 3
            namespace = None
            
            # Parse optional parameters
            i = 1
            while i < len(parts):
                if parts[i] == '-n' and i + 1 < len(parts):
                    try:
                        n_results = int(parts[i + 1])
                        i += 2
                    except ValueError:
                        print("Invalid number for -n parameter")
                        break
                elif parts[i] == '-ns' and i + 1 < len(parts):
                    namespace = parts[i + 1]
                    i += 2
                else:
                    # Add remaining parts to query
                    query = ' '.join(parts[:i+1])
                    i += 1
            
            # Perform search
            print(f"\nSearching for: '{query}'")
            if namespace:
                print(f"Filtering by namespace: {namespace}")
            print(f"Showing top {n_results} results:")
            print("-" * 50)
            
            results = finder.find_similar_uris(
                query=query, 
                namespace=namespace, 
                n_results=n_results, 
                print_results=False
            )
            
            if results:
                for i, result in enumerate(results, 1):
                    score = result['similarity_score']
                    local_name = result['local_name']
                    uri = result['uri']
                    namespace_abbrev = result.get('namespace_abbrev', result['namespace'])
                    
                    print(f"{i:2d}. {local_name}")
                    print(f"    URI: {uri}")
                    print(f"    Namespace: {namespace_abbrev}")
                    print(f"    label: {result['label']}")
                    print(f"    Similarity: {score:.3f}")
                    print()
            else:
                print("No results found.")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            print("Type 'help' for usage information.")

if __name__ == "__main__":
    main()
