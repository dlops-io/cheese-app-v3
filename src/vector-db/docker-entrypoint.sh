#!/bin/bash

echo "Container is running!!!"
echo "Architecture: $(uname -m)"
echo "Python version: $(python --version)"
echo "UV version: $(uv --version)"

# With arguments, run them as a command and stop. A cluster's Job works this way.
if [[ $# -gt 0 ]]; then
    exec python "$@"
fi

echo -en "\033[92m
The following commands are available:
    python cli.py --download --load --chunk_type recursive-split
        Load the cheese books into Chroma, using the embeddings we made for you
    python cli.py --chunk --embed --load --chunk_type recursive-split
        Do the same from scratch (calls the embedding model many times)
    python cli.py --chat --chunk_type recursive-split
        Ask one question through retrieval and Gemini
\033[0m
"

exec /bin/bash
