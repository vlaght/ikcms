from . import exc

class Session:

    def __init__(self, engines, binds, **kwargs):
        self.engines = engines
        self.binds = binds
        self.connections = {}
        self.transactions = {}
        self.__dict__.update(kwargs)

    def get_engine(self, query):
        if hasattr(query, 'table'):
            # Insert, Update, Delete
            table = query.table
        elif hasattr(query, '_froms'):
            # Select
            table = list(query._froms)[0]
        else:
            raise exc.OrmError("Can't get query table")
        return self.binds[table]

    async def execute(self, query):
        conn = await self.get_connection(self.get_engine(query))
        return await conn.execute(query)

    async def get_connection(self, engine):
        conn = self.connections.get(engine)
        if conn:
            return conn
        self.connections[engine] = await engine.acquire()
        await self._begin(engine)
        return self.connections[engine]

    async def close(self):
        for engine in list(self.transactions):
            await self._rollback(engine)
        for engine, conn in self.connections.items():
            engine.release(conn)

    async def commit(self):
        for engine in list(self.transactions):
            await self._commit(engine)
            await self._begin(engine)

    async def rollback(self):
        for engine in list(self.transactions):
            await self._rollback(engine)
            await self._begin(engine)

    async def _begin(self, engine):
        assert engine not in self.transactions
        self.transactions[engine] = await self.connections[engine].begin()

    async def _commit(self, engine):
        assert engine in self.transactions
        await self.transactions[engine].commit()
        del self.transactions[engine]

    async def _rollback(self, engine):
        assert engine in self.transactions
        await self.transactions[engine].rollback()
        del self.transactions[engine]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, e, tb):
        if exc_type:
            await self.close()
        else:
            for engine in list(self.transactions):
                await self._commit(engine)
            await self.close()

