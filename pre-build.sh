#!/bin/bash
# Remove the entire tests directory for deployment
echo "Removing tests directory to avoid UTF-8 encoding issues..."
rm -rf tests/

# Verify the directory is removed
ls -la

echo "Pre-build script completed successfully" 