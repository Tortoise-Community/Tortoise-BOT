import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, BigInteger, Boolean, DateTime, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)
Base = declarative_base()


class DatabaseHandler:
    def __init__(self, connection_url: str):
        self.session = self._configure_session(connection_url)

    def _configure_session(self, connection_url: str):
        """
        Creates engine, creates all tables if don't exist and configures session based on new engine.
        """
        engine = create_engine(connection_url)
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)
        logger.info("Connection to database established.")
        return session()

    @staticmethod
    def construct_mysql_connection_url(username: str, password: str, host: str, database_name: str):
        """
        Docs: https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls
        :return: str mysql formatted connection url
        """
        return f"mysql+pymysql://{username}:{password}@{host}/{database_name}"

    def add_member(self, user_id, guild_id):
        if not self._does_member_exists(user_id, guild_id):
            self.session.add(Member(user_id, guild_id))
            self.session.commit()

    def _does_member_exists(self, user_id, guild_id):
        return self.session.query(Member).filter_by(user_id=user_id, guild_id=guild_id).first()


class Member(Base):
    __tablename__ = "members"

    user_id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger, primary_key=True)
    email = Column(Text)
    perks = Column(Integer, default=0)
    join_date = Column(DateTime, default=datetime.now)
    leave_date = Column(DateTime)
    verified = Column(Boolean, default=False)
    strikes = Column(Text)
    mod_mail = Column(Boolean, default=False)
    warnings = Column(Text)
    roles = Column(Text)

    def __init__(self, user_id: int, guild_id: int):
        self.user_id = user_id
        self.guild_id = guild_id


class Guild(Base):
    __tablename__ = "guilds"

    guild_id = Column(BigInteger, primary_key=True)
    welcome_channel_id = Column(BigInteger)
    reaction_channel_id = Column(BigInteger)
    reaction_roles = Column(Text)

    def __init__(self, guild_id: int):
        self.guild_id = guild_id


if __name__ == "__main__":
    url = DatabaseHandler.construct_mysql_connection_url("root", "", "localhost", "test")
    database_handler = DatabaseHandler(url)
    database_handler.add_member(170208380739256320, 109891165154738176)
