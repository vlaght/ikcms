import asyncio
import collections
import sqlalchemy as sa


def asynctest(coroutine):
    """ Asynctest decorator """
    def wrapper(self):
        async def awrapper(self):
            asetup = getattr(self, 'asetup', None)
            kwargs = asetup and await asetup() or {}
            await coroutine(self, **kwargs)
            aclose = getattr(self, 'aclose', None)
            if aclose:
                await aclose(**kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(awrapper(self))
    wrapper.__name__ = coroutine.__name__
    return wrapper



class TableState(dict):

    def __init__(self, table, primary_keys=['id']):
        self.table = table
        self.primary_keys = primary_keys
        self.order_fields = [table.c[key] for key in primary_keys]

    def row_key(self, row):
        if len(self.primary_keys)==1:
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
        test.assertEqual(db_state, state)

    def copy(self):
        state = self.__class__(self.table, self.primary_keys)
        state.set_state(self.get_state())
        return state


class DbState(collections.OrderedDict):

    def copy(self):
        return self.__class__(
            [(key, value.copy()) for key, value in self.items()])

    async def syncdb(self, session):
        for table_state in self.values():
            await table_state.set_db_state(session)

    async def assert_state(self, test, session):
        for table_state in self.values():
            await table_state.assert_state(test, session)

