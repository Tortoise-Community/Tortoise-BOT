from __future__ import annotations

import asyncpg

class Database:

    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.dsn)

    async def close(self):
        if self.pool:
            await self.pool.close()

class ProgressionManager:

    def __init__(self, db: Database):
        self.db = db

    async def setup(self):

        await self.db.pool.execute(
            """
            CREATE TABLE IF NOT EXISTS activity (
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                messages INTEGER NOT NULL DEFAULT 0,
                active BOOLEAN NOT NULL DEFAULT FALSE,
                active_plus BOOLEAN NOT NULL DEFAULT FALSE,
                PRIMARY KEY (guild_id, user_id)
            )
            """
        )

        await self.db.pool.execute(
            """
            CREATE TABLE IF NOT EXISTS nominations (
                target_id BIGINT NOT NULL,
                nominator_id BIGINT NOT NULL,
                stage TEXT NOT NULL,
                nominator_role TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),

                PRIMARY KEY (target_id, nominator_id, stage, nominator_role)
            )
            """
        )


    async def add_messages_bulk(self, guild_id: int, cache: dict[int, int]):

        async with self.db.pool.acquire() as conn:

            for user_id, amount in cache.items():

                await conn.execute(
                    """
                    INSERT INTO activity (guild_id,user_id,messages)
                    VALUES ($1,$2,$3)
                    ON CONFLICT (guild_id,user_id)
                    DO UPDATE
                    SET messages = activity.messages + $3
                    """,
                    guild_id,
                    user_id,
                    amount
                )

    async def add_messages_bulkops(self, guild_id: int, cache: dict[int, int]):

        if not cache:
            return

        rows = [(guild_id, user_id, amount) for user_id, amount in cache.items()]

        async with self.db.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO activity (guild_id, user_id, messages)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, user_id)
                DO UPDATE
                SET messages = activity.messages + EXCLUDED.messages
                """,
                rows
            )

    async def add_messages_bulk_unnest(self, guild_id: int, cache: dict[int, int]):

        if not cache:
            return

        user_ids = list(cache.keys())
        amounts = list(cache.values())

        await self.db.pool.execute(
            """
            INSERT INTO activity (guild_id, user_id, messages)
            SELECT $1, u, m
            FROM UNNEST($2::BIGINT[], $3::INT[]) AS t(u, m)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE
            SET messages = activity.messages + EXCLUDED.messages
            """,
            guild_id,
            user_ids,
            amounts
        )


    async def mark_active(self, guild_id: int, user_id: int):
        await self.db.pool.execute(
            """
            UPDATE activity
            SET active = TRUE
            WHERE guild_id=$1 AND user_id=$2
            """,
            guild_id,
            user_id
        )

    async def mark_active_plus(self, guild_id: int, user_id: int):
        await self.db.pool.execute(
            """
            UPDATE activity
            SET active_plus = TRUE
            WHERE guild_id=$1 AND user_id=$2
            """,
            guild_id,
            user_id
        )


    async def get_messages(self, guild_id: int, user_id: int) -> int:

        return await self.db.pool.fetchval(
            """
            SELECT messages
            FROM activity
            WHERE guild_id=$1 AND user_id=$2
            """,
            guild_id,
            user_id
        ) or 0

    async def get_non_active_users(self, guild_id: int) -> list[int]:
        rows = await self.db.pool.fetch(
            """
            SELECT user_id
            FROM activity
            WHERE guild_id=$1
            AND active=FALSE
            AND messages >= 50
            """,
            guild_id
        )
        return [r["user_id"] for r in rows]

    async def get_non_active_plus_users(self, guild_id: int) -> list[int]:
         rows = await self.db.pool.fetch(
            """
            SELECT user_id
            FROM activity
            WHERE guild_id=$1
            AND active_plus=FALSE
            AND messages >= 500
            """,
            guild_id
         )
         return [r["user_id"] for r in rows]


    async def add_nomination(
        self,
        target_id: int,
        nominator_id: int,
        stage: str,
        nominator_role: str,
    ) -> bool:

        result = await self.db.pool.execute(
            """
            INSERT INTO nominations
            (target_id,nominator_id,stage,nominator_role)
            VALUES ($1,$2,$3,$4)
            ON CONFLICT DO NOTHING
            """,
            target_id,
            nominator_id,
            stage,
            nominator_role,
        )

        return result != "INSERT 0 0"

    async def get_stage_counts(self, target_id: int, stage: str):

        rows = await self.db.pool.fetch(
            """
            SELECT nominator_role
            FROM nominations
            WHERE target_id=$1 AND stage=$2
            """,
            target_id,
            stage
        )

        apprentices = 0
        fellows = 0
        moderators = 0

        for r in rows:

            role = r["nominator_role"]

            if role == "moderator":
                moderators += 1
            elif role == "fellow":
                fellows += 1
            elif role == "apprentice":
                apprentices += 1

        return apprentices, fellows, moderators

    async def clear_stage(self, target_id: int, stage: str):

        await self.db.pool.execute(
            """
            DELETE FROM nominations
            WHERE target_id=$1 AND stage=$2
            """,
            target_id,
            stage
        )
