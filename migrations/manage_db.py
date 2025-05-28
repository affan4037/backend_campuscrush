import logging
import argparse
from alembic.config import Config
from alembic import command
from backup_db import backup_database
from verify_schema import verify_migration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration(args):
    """Run database migrations"""
    try:
        if not args.no_backup:
            backup_file = backup_database()
            logger.info(f"Database backed up to {backup_file}")
        
        alembic_cfg = Config("alembic.ini")
        if args.verify:
            verify_migration()
        else:
            if args.downgrade:
                command.downgrade(alembic_cfg, args.revision)
            else:
                command.upgrade(alembic_cfg, args.revision)
            logger.info(f"Migration {'downgrade' if args.downgrade else 'upgrade'} completed")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

def create_migration(args):
    """Create a new migration"""
    try:
        alembic_cfg = Config("alembic.ini")
        command.revision(
            alembic_cfg,
            message=args.message,
            autogenerate=True
        )
        logger.info("Migration created successfully")
    except Exception as e:
        logger.error(f"Failed to create migration: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Database management commands")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Migration command
    migrate_parser = subparsers.add_parser("migrate", help="Run migrations")
    migrate_parser.add_argument("--downgrade", action="store_true", help="Downgrade instead of upgrade")
    migrate_parser.add_argument("--no-backup", action="store_true", help="Skip database backup")
    migrate_parser.add_argument("--verify", action="store_true", help="Verify schema changes")
    migrate_parser.add_argument("revision", nargs="?", default="head", help="Revision to migrate to")
    migrate_parser.set_defaults(func=run_migration)

    # Create migration command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    create_parser.set_defaults(func=create_migration)

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 