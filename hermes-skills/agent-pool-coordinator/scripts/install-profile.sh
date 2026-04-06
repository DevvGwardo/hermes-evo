#!/usr/bin/env bash
# install-profile.sh — copy a profile template to ~/.hermes/profiles/
# Usage: install-profile.sh <template_name> [destination_name]
# Example: install-profile.sh coder my-coder

set -e

TEMPLATE="${1:?Usage: $0 <template_name> [destination_name]}"
DEST="${2:-$TEMPLATE}"
TEMPLATE_DIR="$HOME/.hermes/skills/agent-pool-coordinator/references/profiles/$TEMPLATE"
DEST_DIR="$HOME/.hermes/profiles/$DEST"

if [[ ! -d "$TEMPLATE_DIR" ]]; then
    echo "Template '$TEMPLATE' not found. Available:"
    ls -1 "$HOME/.hermes/skills/agent-pool-coordinator/references/profiles/"
    exit 1
fi

if [[ -d "$DEST_DIR" ]]; then
    echo "Profile '$DEST' already exists at $DEST_DIR"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

cp -r "$TEMPLATE_DIR" "$DEST_DIR"
echo "Installed: $DEST_DIR"

# List what was copied
echo "Profile contents:"
ls -1 "$DEST_DIR"
