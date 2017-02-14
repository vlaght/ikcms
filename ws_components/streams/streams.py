from iktomi.utils import cached_property

from .forms import Form
from . import actions
from . import exceptions


__all__ = (
    'Base',
    'I18nMixin',
    'PublicationMixin',
    'Stream',
    'I18nStream',
    'PubI18nStream',
)


class Base:
    name = None
    title = u'Название потока'
    actions = []

    def __init__(self, component):
        assert self.name is not None
        self.component = component
        self.streams = component.streams
        self.actions = [action(self) for action in self.actions]
        self.id = self.get_id()

    @classmethod
    def create(cls, component, registry, **kwargs):
        assert cls.name is not None
        stream = cls(component, **kwargs)
        registry[stream.id] = stream

    def get_id(self, **kwargs):
        return kwargs.get('name', self.name)

    def h_action(self, env, message):
        action_name = message.get('action')
        action = self.get_action(action_name)
        if action:
            return action.handle(env, message)
        else:
            raise exceptions.StreamActionNotFoundError(self, action_name)

    def get_action(self, name):
        for action in self.actions:
            if action.name == name:
                return action

    def get_cfg(self, env):
        return {
            'name': self.name,
            'title': self.title,
            'actions': [action.get_cfg(env) for action in  self.actions],
        }


class Stream(Base):
    mapper_name = None
    db_id = 'main'

    widget = 'Stream'
    max_limit = 100

    ListForm = Form
    FilterForm = Form
    ItemForm = Form

    list_fields = []
    filter_fields = []
    item_fields = []

    permissions = {
        'streams.read': 'rx',
        'streams.edit': 'rxwcd',
    }

    default_order = ['+id']

    actions = [
        actions.List,
        actions.GetItem,
        actions.NewItem,
        actions.CreateItem,
        actions.UpdateItem,
        actions.DeleteItem,
        #actions.create_draft,
        #actions.delete_draft,
        #actions.create_new_item,
        #actions.edit_item,
        #actions.get_field_block,
        #actions.set_field_value,
        #actions.delete_item,
    ]

    def __init__(self, component):
        super().__init__(component)
        assert self.mapper_name

    @cached_property
    def mapper(self):
        mappers = self.component.app.db.mappers
        return mappers[self.db_id][self.mapper_name]

    def get_list_form(self, env):
        class ListForm(self.ListForm):
            fields = self.list_fields
        return ListForm(env=env, stream=self)

    def get_filter_form(self, env):
        class FilterForm(self.FilterForm):
            fields = self.filter_fields
        return FilterForm(env=env, stream=self)

    def get_order_form(self, env):
        class ListForm(self.ListForm):
            fields = [f for f in self.list_fields if f.order]
        return ListForm(env=env, stream=self)

    def get_item_form(self, env, item=None, kwargs=None):
        kwargs = kwargs or {}
        class ItemForm(self.ItemForm):
            fields = self.item_fields
        return ItemForm(env=env, stream=self)

    def query(self):
        return self.mapper.query()

    def get_cfg(self, env):
        list_form = self.get_list_form(env)
        filter_form = self.get_filter_form(env)
        return dict(
            super().get_cfg(env),
            widget=self.widget,
            max_limit=self.max_limit,
            list_fields=list_form.get_cfg(),
            filter_fields=filter_form.get_cfg(),
            permissions=list(self.component.app.auth.get_user_perms(
                env.user,
                self.permissions,
            )),
        )

    async def get_item(self, env, session, item_id, keys=None):
        return await self.query().id(item_id).select_first_item(session, keys)

    async def list_items(
            self,
            env,
            session,
            filters=None,
            order=None,
            page=None,
            page_size=None,
            keys=None,
    ):

        query = self.query()
        query = self._filter_query(env, query, filters)
        query = self._order_query(env, query, order)
        query = self._page_query(env, query, page, page_size)
        return await query.select_items(session, keys=keys)

    async def count_items(self, env, session, filters=None):
        query = self.query()
        query = self._filter_query(env, query, filters)
        return await query.count_items(session)

    async def new_item(self, env, kwargs):
        item_fields_form = self.get_item_form(env, kwargs=kwargs)
        return item_fields_form.get_initials(**kwargs)

    async def insert_item(self, env, session, item):
        if 'id' in item:
            if await self.is_item_exists(env, session, item['id']):
                raise exceptions.StreamItemAlreadyExistsError(
                    self.name,
                    item['id'],
                )
        return await self.query().insert_item(session, item)

    async def update_item(self, env, session, item_id, values):
        keys = list(values.keys())
        if not await self.is_item_exists(env, session, item_id):
            raise exceptions.StreamItemNotFoundError(self.name, item_id)
        return await self.query().update_item(session, item_id, values, keys)

    async def delete_item(self, env, session, item_id):
        if not await self.is_item_exists(env, session, item_id):
            raise exceptions.StreamItemNotFoundError(self.name, item_id)
        return await self.query().delete_item(session, item_id)

    async def check_perms(self, env, perms):
       return self.component.app.auth.check_perms(env.user, perms)

    async def is_item_exists(self, env, session, item_id):
        return bool(await self.get_item(env, session, item_id, ['id']))

    def _filter_query(self, env, query, filters=None):
        filters = filters or {}
        filter_form = self.get_filter_form(env)
        for name, field in filter_form.items():
            query = field.filter(query, filters.get(name))
        return query

    def _order_query(self, env, query, order=None):
        order = order or ['+id']
        order_form = self.get_order_form(env)
        for value in order:
            value, name = value[0], value[1:]
            assert name in order_form
            query = order_form[name].order(query, value)
        return query

    def _page_query(self, env, query, page=1, page_size=1):
        assert page > 0
        assert 0 < page_size <= self.max_limit
        query = query.limit(page_size)
        if page != 1:
            query = query.offset((page-1)*page_size)
        return query


class I18nMixin:

    langs = ['ru', 'en']

    def __init__(self, component, lang, **kwargs):
        assert lang in self.langs
        self.lang = lang
        super().__init__(component, **kwargs)

    def get_id(self, **kwargs):
        lang = kwargs.get('lang', self.lang)
        id = super().get_id(**kwargs)
        return '.'.join([lang, id])

    @classmethod
    def create(cls, component, registry, **kwargs):
        assert 'lang' not in kwargs
        for lang in cls.langs:
            super().create(component, registry, lang=lang, **kwargs)

    @cached_property
    def i18n_streams(self):
        return {lang: self.streams[self.get_id(lang=lang)] \
                for lang in self.langs}

    @cached_property
    def mapper(self):
        mappers = self.component.app.db.mappers
        return mappers[self.db_id][self.lang][self.mapper_name]


class PublicationMixin:

    db_ids = ['admin', 'front']
    db_id = None
    allowed_perms = ['rwxdcp', 'rx']

    def __init__(self, component, db_id, **kwargs):
        assert db_id in self.db_ids
        self.db_id = db_id
        self.is_src = db_id == self.db_ids[0]
        self.is_dest = db_id == self.db_ids[1]
        super().__init__(component, **kwargs)
        self.set_permissions()

    def get_id(self, **kwargs):
        db_id = kwargs.get('db_id', self.db_id)
        id = super().get_id(**kwargs)
        return '.'.join([db_id, id])

    @classmethod
    def create(cls, component, registry, **kwargs):
        assert 'db_id' not in kwargs
        for db_id in cls.db_ids:
            super().create(component, registry, db_id=db_id, **kwargs)

    @cached_property
    def pub_streams(self):
        return {db_id: self.streams[self.get_id(db_id=db_id)] \
                for db_id in self.db_ids}

    def set_permissions(self):
        allowed_perms = set(self.allowed_perms[self.db_ids.index(self.db_id)])
        self.permissions = {role: set(perms).intersection(allowed_perms) \
            for role, perms in self.permissions.items()}


class I18nStream(I18nMixin, Stream):
    pass

class PubStream(PublicationMixin, Stream):
    pass

class PubI18nStream(PublicationMixin, I18nMixin, Stream):
    pass
