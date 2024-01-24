from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from MySQLdb import OperationalError

# Database
SQLALCHEMY_DATABASE_URL = "mysql://root:D3skT0p@127.0.0.1/dbapps"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
engine_auto = engine.execution_options(isolation_level="AUTOCOMMIT")

