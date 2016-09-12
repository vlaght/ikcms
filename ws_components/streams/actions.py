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
        self.stream.component.app.auth.check_perms(env.user, self.require_perms)
        message = self.MessageForm().to_python(raw_message)
        return await self._handle(env, message)

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

    async def _handle(self, env, message):
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
            query = self.query(env, filters, [order])
            total = await query.count_items(session)

            query = self.page_query(query, page, page_size)
            list_items = await query.select_items(
                session, keys=set(list_form.keys()))

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

    def query(self, env, filters=None, order=None):
        filters = filters or {}
        order = order or ['+id']

        order_form = self.stream.get_order_form(env)
        filter_form = self.stream.get_filter_form(env)

        query = self.stream.query()

        for name, field in filter_form.items():
            query = field.filter(query, filters.get(name))

        for value in order:
            value, name = value[0], value[1:]
            assert name in order_form
            query = order_form[name].order(query, value)
        return query

    def page_query(self, query, page=1, page_size=1):
        assert page > 0
        assert 0 < page_size <= self.stream.max_limit
        query = query.limit(page_size)
        if page != 1:
            query = query.offset((page-1)*page_size)
        return query


class GetItem(Base):

    name = 'get_item'
    require_perms = 'r'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.item_id,
        ]

    async def _handle(self, env, message):
        item_id = message['item_id']
        async with await env.app.db() as session:
            items = await self.stream.query().id(item_id).select_items(session)
        if not items:
            raise exc.StreamItemNotFound(self.stream, item_id)
        assert len(items) == 1, \
               'There are {} items with id={}'.format(len(items), item_id)

        item_fields_form = self.stream.get_item_form(env, item=items[0])
        raw_item = item_fields_form.from_python(items[0])
        return {
            'item_fields': item_fields_form.get_cfg(),
            'item': raw_item,
        }


class NewItem(Base):

    name = 'new_item'
    require_perms = 'c'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.kwargs,
        ]

    async def _handle(self, env, message):
        item_fields_form = self.stream.get_item_form(
            env, kwargs=message['kwargs'])
        raw_item = item_fields_form.from_python(
            item_fields_form.get_initials(**message['kwargs']))
        return {
            'item_fields': item_fields_form.get_cfg(),
            'item': raw_item,
        }


class CreateItem(Base):

    name = 'create_item'
    require_perms = 'c'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.values,
            message_fields.kwargs,
        ]

    async def _handle(self, env, message):
        item_fields_form = self.stream.get_item_form(
            env, kwargs=message['kwargs'])
        raw_item = message['values']
        keys = list(item_fields_form)
        if 'id' not in raw_item:
            keys.remove('id')
        item, errors = item_fields_form.to_python(raw_item, keys=keys)
        if not errors:
            async with await env.app.db() as session:
                item = await self.stream.query().insert_item(
                    session,
                    item,
                )
            raw_item = item_fields_form.from_python(item)
        return {
            'item_fields': item_fields_form.get_cfg(),
            'item': raw_item,
            'errors': errors,
        }


class UpdateItem(Base):

    name = 'update_item'
    require_perms = 'e'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.item_id,
            message_fields.values,
        ]

    async def _handle(self, env, message):
        item_fields_form = self.stream.get_item_form(env)
        item_id = message['item_id']
        raw_values = message['values']
        values, errors = item_fields_form.to_python(raw_values,
                                                    keys=raw_values.keys())
        if not errors:
            async with await env.app.db() as session:
                try:
                    item = await self.stream.query().update_item(
                        session,
                        item_id,
                        values,
                        keys=list(values.keys()),
                    )
                except orm.exc.ItemNotFoundError:
                    raise exc.StreamItemNotFound(self, item_id)
        return {
            'item_fields': item_fields_form.get_cfg(),
            'item_id': raw_values.get('id', item_id),
            'values': raw_values,
            'errors': errors,
        }


class DeleteItem(Base):

    name = 'delete_item'
    require_perms = 'd'

    class MessageForm(MessageFormBase):
        fields = [
            message_fields.item_id,
        ]

    async def _handle(self, env, message):
        async with await env.app.db() as session:
            try:
                await self.stream.query().delete_item(
                    session,
                    message['item_id'],
                )
            except orm.exc.ItemNotFoundError:
                raise exc.StreamItemNotFound(self, message['item_id'])
        return {
            'item_id': message['item_id'],
        }

