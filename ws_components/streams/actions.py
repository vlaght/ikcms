from ikcms.ws_apps.base.forms import MessageForm as MessageFormBase
from ikcms import orm

from .forms import message_fields
from . import exc



class Base:
    name = None
    require_perms = ''

    MessageForm = MessageFormBase

    def __init__(self, stream):
        assert self.name is not None
        self.stream = stream

    async def handle(self, env, raw_message):
        self.stream.check_perms(env, self.require_perms)
        message = self.MessageForm().to_python(raw_message)
        return await self(env, message)

    async def _handle(self, env, message):
        raise NotImplementedError

    def get_cfg(self, env):
        return {
            'name': self.name
        }



class List(Base):
    name = 'list'
    require_perms = 'x'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.filters,
            message_fields.order,
            message_fields.page,
            message_fields.page_size,
        ]

    async def list(self, env, message):
        list_form = self.stream.get_list_form(env)
        filter_form = self.stream.get_filter_form(env)
        order_form = self.stream.get_order_form(env)
        order = message['order']
        if order[1:] not in order_form:
            raise exc.StreamFieldNotFound(self.stream, order[1:])

        raw_filters = message['filters']
        filters, filters_errors = filter_form.to_python(raw_filters)
        page = message['page']
        page_size = message['page_size']

        if not 0 < page_size <= self.stream.max_limit:
            raise exc.MessageError('Page size error')
        async with await env.app.db() as session:
            list_items = await self.stream.list_items(
                env,
                session,
                filters,
                [order],
                page,
                page_size,
                keys=set(list_form.keys()),
            )
            total = await self.stream.count_items(env, session, filters)

        raw_list_items = list_form.values_from_python(list_items)

        return {
            'stream': self.stream.name,
            'title': self.stream.title,
            'action': self.name,
            'list_fields': list_form.get_cfg(),
            'items': raw_list_items,
            'total': total,
            'filters_fields': filter_form.get_cfg(),
            'filters_errors': filters_errors,
            'filters': raw_filters,
            'page_size': page_size,
            'page': page,
            'order': message['order'],
        }
    __call__ = list


class GetItem(Base):

    name = 'get_item'
    require_perms = 'r'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.item_id,
        ]

    async def get_item(self, env, message):
        item_id = message['item_id']
        async with await env.app.db() as session:
            item = await self.stream.get_item(env, session, item_id)
        if not item:
            raise exc.StreamItemNotFoundError(self.stream, item_id)

        item_fields_form = self.stream.get_item_form(env, item=item)
        raw_item = item_fields_form.from_python(item)
        return {
            'item_fields': item_fields_form.get_cfg(),
            'item': raw_item,
        }
    __call__ = get_item


class NewItem(Base):

    name = 'new_item'
    require_perms = 'c'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.kwargs,
        ]

    async def new_item(self, env, message):
        kwargs=message['kwargs']
        item_fields_form = self.stream.get_item_form(env, kwargs)
        item = await self.stream.new_item(env, kwargs)
        raw_item = item_fields_form.from_python(item)
        return {
            'item_fields': item_fields_form.get_cfg(),
            'item': raw_item,
        }
    __call__ = new_item


class CreateItem(Base):

    name = 'create_item'
    require_perms = 'c'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.values,
            message_fields.kwargs,
        ]

    async def create_item(self, env, message):
        item_fields_form = self.stream.get_item_form(
            env, kwargs=message['kwargs'])
        raw_item = message['values']
        keys = list(item_fields_form)
        if 'id' not in raw_item:
            keys.remove('id')
        item, errors = item_fields_form.to_python(raw_item, keys=keys)
        if not errors:
            async with await env.app.db() as session:
                item = await self.stream.insert_item(env, session, item)
            raw_item = item_fields_form.from_python(item)
        return {
            'item_fields': item_fields_form.get_cfg(),
            'item': raw_item,
            'errors': errors,
        }
    __call__ = create_item


class UpdateItem(Base):

    name = 'update_item'
    require_perms = 'e'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.item_id,
            message_fields.values,
        ]

    async def update_item(self, env, message):
        item_fields_form = self.stream.get_item_form(env)
        item_id = message['item_id']
        raw_values = message['values']
        values, errors = item_fields_form.to_python(raw_values,
                                                    keys=raw_values.keys())
        if not errors:
            async with await env.app.db() as session:
                item = await self.stream.update_item(
                        env,
                        session,
                        item_id,
                        values,
                )
        return {
            'item_fields': item_fields_form.get_cfg(),
            'item_id': raw_values.get('id', item_id),
            'values': raw_values,
            'errors': errors,
        }
    __call__ = update_item


class DeleteItem(Base):

    name = 'delete_item'
    require_perms = 'd'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.item_id,
        ]

    async def delete_item(self, env, message):
        async with await env.app.db() as session:
            await self.stream.delete_item(env, session, message['item_id'])
        return {
            'item_id': message['item_id'],
        }
    __call__ = delete_item
