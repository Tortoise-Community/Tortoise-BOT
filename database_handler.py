import asyncio
import logging
from databases import Database
from sqlalchemy import Table, Column, Integer, BigInteger, MetaData, Boolean, DateTime

logger = logging.getLogger(__name__)


class DatabaseHandler:
    @classmethod
    async def create(cls):
        """"
        Can't use await in __init__ so we create a factory pattern.
        To correctly create this object you need to call :
            await DatabaseHandler.create()

        """
        self = DatabaseHandler()
        self.connection = await self._get_connection()
        logger.info("Connection to database established.")
        return self

    def __init__(self):
        self.connection = None

    async def _get_connection(self):
        """
        Returns a connection to the db, if db doesn't exist create new
        """
        database = Database("mysql://localhost/")
        await database.connect()

    async def _create_tables(self):
        metadata = MetaData()
        members = Table("members", metadata,
                        Column("user_id", BigInteger),
                        Column("guild_id", BigInteger),
                        Column("points", Integer),
                        Column("join_date", DateTime),
                        Column("verified", Boolean),
                        Column("strikes", Integer),
                        )


database_handler = asyncio.get_event_loop().run_until_complete(DatabaseHandler.create())