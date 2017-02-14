import json
from ikcms.orm import mappers


class Draft(mappers.Base):

    name = 'Draft'
    db_id = 'admin'

    async def get_new_item_draft(self, session, stream_id, user_id):
        return await self.query().filter_by(
            user_id=user_id,
            stream_id=stream_id,
            item_id=None,
        ).select_first_item(session)

    async def store_new_item_draft(self, session, stream_id, user_id, values):
        data = self.from_python(values)
        draft = await get_new_item_draft(session, stream_id, user_id)
        if draft:
            draft['data'] = data
            await self.query().update_item(session, draft['id'], draft)
        else:
            draft = {
                'stream_id': stream_id,
                'user_id': user_id,
                'data': data,
            }
            await self.query().insert_item(session, draft)

    async def get_edit_item_draft(self, session, stream_id, item_id):
        return await self.query().filter_by(
            stream_id=stream_id,
            item_id=item_id,
        ).select_first_item(session)

    async def store_edit_item_draft(self, session, stream_id, item_id, values):
        data = self.from_python(values)
        draft = await get_edit_item_draft(session, stream_id, item_id)
        if draft:
            draft['data'] = data
            await self.query().update_item(session, draft['id'], draft)
        else:
            draft = {
                'stream_id': stream_id,
                'item_id': item_id,
                'data': data,
            }
            await self.query().insert_item(session, draft)

    async def delete_draft(self, item_id):
        with self.app.db() as sesion:
            await self.query().delete_item(session, item_id)

    def to_python(self, raw_data):
        return json.loads(raw_data)

    def from_python(self, python_data):
        return json.dump(raw_data)


