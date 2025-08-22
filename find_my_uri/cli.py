from .core import URIFinder, URIFinderConfig
import importlib.resources
import argparse
import shlex
from pathlib import Path
from typing import List, Optional
from importlib.resources import files

DATA_FILES = files("find_my_uri").joinpath("data")

DEFAULT_EMBEDDING_MODEL = "paraphrase-MiniLM-L3-v2"
from .core import URIFinder, URIFinderConfig
import importlib.resources
import argparse
import shlex
from pathlib import Path
from typing import List, Optional
import sys
import readline

DEFAULT_EMBEDDING_MODEL = "paraphrase-MiniLM-L3-v2"

class CommandHistory:
    """Command history manager with readline integration."""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.setup_readline()
    
    def setup_readline(self):
        """Setup readline for command history and completion."""
        
        # Enable history
        readline.set_history_length(self.max_size)
        
        # Set up key bindings for better experience
        readline.parse_and_bind('tab: complete')
        
        # Enable history search
        readline.parse_and_bind('"\e[A": history-search-backward')  # Up arrow
        readline.parse_and_bind('"\e[B": history-search-forward')   # Down arrow
        
        # Set up completion for common commands
        readline.set_completer(self._completer)
        readline.set_completer_delims(' \t\n')
    
    def _completer(self, text, state):
        """Auto-completion function for commands and options."""
        commands = [
            'help', 'quit', 'exit', 'history', 
            '-n', '--num-results', '-ns', '--namespace', '-h', '--help'
        ]
        
        namespaces = ['S223', 'WATR', 'UNIT', 'QK', 'RDF', 'RDFS', 'OWL']
        
        # Combine all possible completions
        options = commands + namespaces
        
        matches = [cmd for cmd in options if cmd.startswith(text)]
        
        if state < len(matches):
            return matches[state]
        return None
    
    def add(self, command: str):
        """Add a command to readline history."""
        readline.add_history(command)
    
    def get_history(self, n: int = 10) -> List[str]:
        """Get last n commands from history."""
        
        history_length = readline.get_current_history_length()
        start = max(1, history_length - n + 1)
        
        return [
            readline.get_history_item(i) 
            for i in range(start, history_length + 1)
            if readline.get_history_item(i)
        ]
    
    def clear_history(self):
        """Clear command history."""
        readline.clear_history()
    
    def save_history(self, filename: str):
        """Save history to file."""
        try:
            readline.write_history_file(filename)
        except Exception as e:
            print(f"Warning: Could not save history to {filename}: {e}")
    
    def load_history(self, filename: str):
        """Load history from file."""
        try:
            readline.read_history_file(filename)
        except FileNotFoundError:
            pass  # No history file exists yet
        except Exception as e:
            print(f"Warning: Could not load history from {filename}: {e}")


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
    print("Type 'help' for commands or 'quit' to exit.\n")

    # Initialize finder
    try:
        # Try to use the data directory approach first
        config = URIFinderConfig(
            data_dir=Path("data"),
            embedding_model=DEFAULT_EMBEDDING_MODEL
        )
        finder = URIFinder(config)
        print("✓ Vector database loaded successfully")
    except FileNotFoundError:
        # Fallback to importlib.resources approach
        try:
            with importlib.resources.path('find_my_uri', 'vector_db') as vector_db_path:
                config = URIFinderConfig(
                    data_dir=vector_db_path,
                    embedding_model=DEFAULT_EMBEDDING_MODEL
                )
                finder = URIFinder(config)
                print("✓ Vector database loaded successfully")
        except Exception as e:
            print(f"Error loading vector database: {e}")
            return
    
    # Initialize command history and parser
    history = CommandHistory()
    search_parser = SearchArgumentParser()
    
    # Load command history from file
    history_file = Path.home() / '.uri_search_history'
    history.load_history(str(history_file))
    
    try:
        _run_interactive_loop(finder, history, search_parser)
    finally:
        # Save command history on exit
        history.save_history(str(history_file))


def _get_input_with_readline(prompt: str) -> str:
    """Get input with readline support if available."""
    return input(prompt)


def _run_interactive_loop(finder, history: CommandHistory, search_parser: SearchArgumentParser):
    """Run the interactive search loop."""
    
    while True:
        try:
            # Get user input with readline support
            user_input = _get_input_with_readline("\n> ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            elif user_input.lower() in ['help', 'h']:
                _show_help()
                continue
            
            elif user_input.lower().startswith('history'):
                parts = user_input.split()
                n = 10 if len(parts) == 1 else int(parts[1]) if parts[1].isdigit() else 10
                recent_history = history.get_history(n)
                if recent_history:
                    print(f"\nLast {len(recent_history)} commands:")
                    for i, cmd in enumerate(recent_history, 1):
                        print(f"  {i:2d}. {cmd}")
                else:
                    print("No commands in history")
                continue
            
            elif user_input.lower() == 'clear-history':
                history.clear_history()
                print("Command history cleared")
                continue
            
            # Add to history
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
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            print("Type 'help' for usage information.")


def _show_help():
    """Show general help information."""
    print("\nCommands:")
    print("  help, h               - Show this help message")
    print("  quit/exit/q          - Exit the utility")
    print("  history [n]          - Show last n commands (default: 10)")
    print("  clear-history        - Clear command history")
    print("  <search_term> [options] - Search for URIs")
    
    print("\nNavigation:")
    print("  ↑ / ↓                - Navigate command history")
    print("  Tab                  - Auto-complete commands and options")
    print("  Ctrl+R               - Search command history")
    
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