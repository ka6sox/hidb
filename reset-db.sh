#!/bin/bash
# Reset the database by running the Flask init-db command in the Docker container

echo "⚠️  WARNING: This will delete all data in the database!"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    echo "Resetting database..."
    docker compose exec web flask init-db
    echo "✓ Database reset complete!"
else
    echo "Operation cancelled."
fi
