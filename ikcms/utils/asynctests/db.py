import collections
from unittest.mock import MagicMock

import sqlalchemy as sa
import ikcms.ws_components.db


class TableState(dict):

    def __init__(self, table, primary_keys=None):
        super().__init__()
        self.table = table
        self.primary_keys = primary_keys or ['id']
        self.order_fields = [table.c[key] for key in self.primary_keys]

    def row_key(self, row):
        if len(self.primary_keys) == 1:
            return row[self.primary_keys[0]]
        else:
            return tuple([row[key] for key in self.primary_keys])

    async def set_db_state(self, session, rows=None):
        if rows is None:
            rows = self.get_state()
        else:
            self.set_state(rows)
        await session.execute(sa.sql.delete(self.table))
        if rows:
            await session.execute(sa.sql.insert(self.table).values(rows))
    syncdb = set_db_state

    async def get_db_state(self, session):
        q = sa.sql.select(self.table.c).order_by(*self.order_fields)
        result = await session.execute(q)
        return [dict(row) for row in result]

    def get_state(self):
        return [self[key] for key in sorted(self.keys())]

    def set_state(self, rows):
        self.clear()
        for row in rows:
            self.append(row.copy())

    def append(self, row):
        self[self.row_key(row)] = row

    async def assert_state(self, test, session):
        db_state = await self.get_db_state(session)
        state = self.get_state()
        test.assertEqual(db_state, state, self.table.name)

    def copy(self):
        state = self.__class__(self.table, self.primary_keys)
        state.set_state(self.get_state())
        return state


class DbState(collections.OrderedDict):

    def copy(self):
        return self.__class__(
            [(key, value.copy()) for key, value in self.items()])

    def add_table(self, key, table, primary_keys=None):
        self[key] = TableState(table, primary_keys or ['id'])

    async def syncdb(self, session):
        for table_state in self.values():
            await table_state.set_db_state(session)

    async def assert_state(self, test, session):
        for table_state in self.values():
            await table_state.assert_state(test, session)


    async def reset(self, db):
        async with await db() as session:
            tables = [state.table for state in self.values()]
            for table in tables[::-1]:
                conn = await session.get_connection(db.binds[table])
                try:
                    await conn.execute(sa.sql.ddl.DropTable(table))
                except Exception:
                    pass
            for table in tables:
                conn = await session.get_connection(db.binds[table])
                await conn.execute(sa.sql.ddl.CreateTable(table))


async def create_db_component(DATABASES, registry):
    app = MagicMock()
    del app.db
    app.cfg.DATABASES = DATABASES

    Component = ikcms.ws_components.db.component(mappers=registry)
    return await Component.create(app)


def assert_client_error(test, ctx, test_exc):
    exc = ctx.exception
    client_error = ClientError(test_exc)
    test.assertEqual(exc.error, client_error.error)
    test.assertEqual(exc.kwargs, client_error.kwargs)
