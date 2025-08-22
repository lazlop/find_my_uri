from .core import URIFinder, URIFinderConfig
import importlib.resources
import argparse
import shlex
from pathlib import Path
from typing import List, Optional
from importlib.resources import files

DATA_FILES = files("find_my_uri").joinpath("data")

DEFAULT_EMBEDDING_MODEL = "paraphrase-MiniLM-L3-v2"

class CommandHistory:
    """Simple command history manager."""
    
    def __init__(self, max_size: int = 100):
        self.history: List[str] = []
        self.max_size = max_size
        self.current_index = -1
    
    def add(self, command: str):
        """Add a command to history."""
        if command and (not self.history or self.history[-1] != command):
            self.history.append(command)
            if len(self.history) > self.max_size:
                self.history.pop(0)
        self.reset_index()
    
    def get_previous(self) -> Optional[str]:
        """Get the previous command in history."""
        if not self.history:
            return None
        
        if self.current_index == -1:
            self.current_index = len(self.history) - 1
        elif self.current_index > 0:
            self.current_index -= 1
        
        return self.history[self.current_index] if self.current_index >= 0 else None
    
    def get_next(self) -> Optional[str]:
        """Get the next command in history."""
        if not self.history or self.current_index == -1:
            return None
        
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return self.history[self.current_index]
        else:
            self.reset_index()
            return ""
    
    def reset_index(self):
        """Reset the history index."""
        self.current_index = -1
    
    def show_history(self, n: int = 10) -> List[str]:
        """Show last n commands from history."""
        return self.history[-n:] if self.history else []


class SearchArgumentParser:
    """Parser for search command arguments."""
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            prog='search',
            description='Search for URIs in the ontology',
            add_help=False  # We'll handle help manually
        )
        
        self.parser.add_argument(
            'query',
            nargs='+',
            help='Search query terms'
        )
        
        self.parser.add_argument(
            '-n', '--num-results',
            type=int,
            default=3,
            help='Number of results to return (default: 3)'
        )
        
        self.parser.add_argument(
            '-ns', '--namespace',
            type=str,
            help='Filter by namespace abbreviation (S223, WATR, UNIT, QK, etc.)'
        )
        
        self.parser.add_argument(
            '-h', '--help',
            action='store_true',
            help='Show search help'
        )
    
    def parse(self, args_str: str):
        """Parse command string into arguments."""
        try:
            # Use shlex to properly handle quoted strings
            args = shlex.split(args_str)
            return self.parser.parse_args(args)
        except (argparse.ArgumentError, SystemExit) as e:
            raise ValueError(f"Invalid arguments: {e}")


def main():
    """Interactive command line utility for searching URIs."""
    print("=== URI Search Utility ===")
    print("This utility searches for URIs in the ontology using semantic similarity.")
    print("Type 'help' for commands, 'up' for previous command, or 'quit' to exit.\n")
    
    config = URIFinderConfig(
        data_dir=DATA_FILES,
        embedding_model=DEFAULT_EMBEDDING_MODEL
    )
    finder = URIFinder(config)
    print("✓ Vector database loaded successfully")
    
    # Initialize command history and parser
    history = CommandHistory()
    search_parser = SearchArgumentParser()
    
    _run_interactive_loop(finder, history, search_parser)


def _run_interactive_loop(finder, history: CommandHistory, search_parser: SearchArgumentParser):
    """Run the interactive search loop."""
    
    while True:
        try:
            # Get user input
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            elif user_input.lower() == 'up':
                previous_cmd = history.get_previous()
                if previous_cmd:
                    print(f"Previous command: {previous_cmd}")
                    # Ask if user wants to execute it
                    confirm = input("Execute this command? (y/n): ").strip().lower()
                    if confirm in ['y', 'yes']:
                        user_input = previous_cmd
                    else:
                        continue
                else:
                    print("No previous commands in history")
                    continue
            
            elif user_input.lower() == 'down':
                next_cmd = history.get_next()
                if next_cmd is not None:
                    if next_cmd:
                        print(f"Next command: {next_cmd}")
                        confirm = input("Execute this command? (y/n): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            user_input = next_cmd
                        else:
                            continue
                    else:
                        print("End of history")
                        continue
                else:
                    print("No next commands in history")
                    continue
            
            elif user_input.lower() in ['help', 'h']:
                _show_help()
                continue
            
            elif user_input.lower().startswith('history'):
                parts = user_input.split()
                n = 10 if len(parts) == 1 else int(parts[1]) if parts[1].isdigit() else 10
                recent_history = history.show_history(n)
                if recent_history:
                    print(f"\nLast {len(recent_history)} commands:")
                    for i, cmd in enumerate(recent_history, 1):
                        print(f"  {i:2d}. {cmd}")
                else:
                    print("No commands in history")
                continue
            
            # Add to history (before processing in case of error)
            if user_input.lower() not in ['up', 'down']:
                history.add(user_input)
            
            # Parse and execute search command
            try:
                args = search_parser.parse(user_input)
                
                if args.help:
                    _show_search_help()
                    continue
                
                query = ' '.join(args.query)
                
                # Perform search
                print(f"\nSearching for: '{query}'")
                if args.namespace:
                    print(f"Filtering by namespace: {args.namespace}")
                print(f"Showing top {args.num_results} results:")
                print("-" * 50)
                
                results = finder.find_similar_uris(
                    query=query,
                    namespace=args.namespace,
                    n_results=args.num_results
                )
                
                _display_results(results)
                
            except ValueError as e:
                print(f"Error parsing command: {e}")
                print("Type 'help' or use -h for usage information.")
                
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            print("Type 'help' for usage information.")


def _show_help():
    """Show general help information."""
    print("\nCommands:")
    print("  help, h                - Show this help message")
    print("  quit/exit/q           - Exit the utility")
    print("  up                    - Show and optionally execute previous command")
    print("  down                  - Show and optionally execute next command in history")
    print("  history [n]           - Show last n commands (default: 10)")
    print("  <search_term> [options] - Search for URIs")
    print("\nSearch Options:")
    print("  -n, --num-results <num>  - Number of results to return (default: 3)")
    print("  -ns, --namespace <ns>    - Filter by namespace abbreviation")
    print("  -h, --help              - Show detailed search help")
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
    print("  \"heat exchanger\" --namespace WATR --num-results 5")


def _show_search_help():
    """Show detailed search help."""
    print("\nSearch Command Help:")
    print("Usage: <query> [options]")
    print("\nOptions:")
    print("  -n, --num-results <number>")
    print("      Number of results to return (default: 3)")
    print("      Example: temperature -n 10")
    print("")
    print("  -ns, --namespace <abbreviation>")
    print("      Filter results by namespace")
    print("      Example: pump -ns S223")
    print("")
    print("  -h, --help")
    print("      Show this help message")
    print("")
    print("Query Examples:")
    print("  temperature")
    print("  flow rate")
    print("  \"heat exchanger\"")
    print("  pump --namespace S223 --num-results 5")
    print("  meter -ns UNIT -n 8")


def _display_results(results):
    """Display search results in a formatted way."""
    if results:
        for i, result in enumerate(results, 1):
            # Handle different result formats based on your URIFinder implementation
            if isinstance(result, dict):
                local_name = result.get('local_name', 'Unknown')
                uri = result.get('uri', 'Unknown')
                label = result.get('label', '')
                namespace = result.get('namespace', '')
                
                # Try to get namespace abbreviation
                from .core import NAMESPACE_MAP
                namespace_abbrev = None
                for full_ns, abbrev in NAMESPACE_MAP.items():
                    if namespace.startswith(full_ns):
                        namespace_abbrev = abbrev
                        break
                namespace_display = namespace_abbrev or namespace
                
                print(f"{i:2d}. {local_name}")
                print(f"    URI: {uri}")
                print(f"    Namespace: {namespace_display}")
                if label and label != local_name:
                    print(f"    Label: {label}")
                
                # If similarity score is available
                if 'similarity_score' in result:
                    print(f"    Similarity: {result['similarity_score']:.3f}")
                print()
            else:
                print(f"{i:2d}. {result}")
    else:
        print("No results found.")
        print("Try:")
        print("- Different search terms")
        print("- Removing namespace filter (-ns)")
        print("- Increasing number of results (-n)")


if __name__ == "__main__":
    main()