import sqlalchemy as sa

class Query(sa.sql.Select):

    def __init__(self, mapper, *args, **kwargs):
        self.mapper = self.m = mapper
        super().__init__([self.mapper.c['id']], *args, **kwargs)

    def id(self, *ids):
        if len(ids) == 1:
            return self.where(self.mapper.c['id'] == ids[0])
        else:
            return self.where(self.mapper.c['id'].in_(ids))

    def filter_by(self, **kwargs):
        q = self
        for key, value in kwargs.items():
            q = q.where(self.mapper.c[key] == value)
        return q

    async def select_items(self, session, keys=None):
        return await self.mapper.select_items(
            session,
            self,
            keys=keys,
        )

    async def select_first_item(self, session, keys=None):
        return await self.mapper.select_first_item(
            session,
            self,
            keys=keys,
        )

    async def insert_item(self, session, values, keys=None): #XXX
        return await self.mapper.insert_item(
            session,
            values=values,
            keys=keys,
        )

    async def update_item(self, session, item_id, values, keys=None):
        return await self.mapper.update_item(
            session,
            self,
            item_id=item_id,
            values=values,
            keys=keys,
        )

    async def delete_item(self, session, item_id):
        return await self.mapper.delete_item(
            session,
            self,
            item_id,
        )

    async def count_items(self, session):
        return await self.mapper.count_items(
            session,
            self,
        )

    async def fill(self, session, data, path):
        return await self.mapper.fill(
            session,
            self,
            data,
            path,
        )



class PubQuery(Query):

    async def publish(self, session, item_id):
        return await self.mapper.publish(session, self, item_id)


