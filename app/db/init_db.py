import logging
from sqlalchemy.orm import Session

from app.db.session import engine
from alembic.config import Config
from alembic import command
from sqlalchemy import inspect
from app.db.session import engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db() -> None:
    """
    Initialize the database by running Alembic migrations.
    """
    try:
        # Create Alembic configuration
        alembic_cfg = Config("alembic.ini")
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully")
    except Exception as e:
        logger.error(f"Error applying database migrations: {e}")
        raise


def create_all_tables():
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        Base.metadata.create_all(bind=engine)
        
        new_tables = set(inspect(engine).get_table_names()) - set(existing_tables)
        if new_tables:
            logger.info(f"Created new tables: {new_tables}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        return False


if __name__ == "__main__":
    logger.info("Creating database tables")
    init_db()
    logger.info("Database tables created") 