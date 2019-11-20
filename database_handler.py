from sqlalchemy import Table, Column, Integer, BigInteger, MetaData, Boolean, DateTime
metadata = MetaData()
members = Table("members", metadata,
                Column("user_id", BigInteger),
                Column("guild_id", BigInteger),
                Column("points", Integer),
                Column("join_date", DateTime),
                Column("verified", Boolean),
                Column("strikes", Integer),
                )
