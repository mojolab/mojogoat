#!/bin/bash

# Help message
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  echo "MojoGOAT API - A Graph of All Things API"
  echo ""
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  --registry, -r PATH   Path to the registry file"
  echo "                        (default: \$MOJOGOAT_REGISTRY or /xpal-data/conf/goat_registry.json)"
  echo "  --port, -p PORT       Port to listen on (default: 5000)"
  echo "  --host HOST           Host to bind to (default: 0.0.0.0)"
  echo "  --debug, -d           Enable debug mode"
  echo "  --help, -h            Show this help message"
  echo ""
  echo "Example:"
  echo "  $0 -r /path/to/registry.json -p 8080 -d"
  exit 0
fi

# Run the API
python3 mojogoatapi.py "$@"