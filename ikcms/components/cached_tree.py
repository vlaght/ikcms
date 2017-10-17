import logging
import cPickle as pickle
import time

import sqlalchemy as sa
from sqlalchemy.orm import Query

import ikcms.components.base


logger = logging.getLogger(__name__)


class Component(ikcms.components.base.Component):

    name = 'cached_tree'
    model = 'front.TreeItem'
    check_timeout = 3
    lock_timeout = 3

    def __init__(self, app):
        super(Component, self).__init__(app)
        self.model = self.app.db.get_model(self.model)
        self.cache_key_checked_ts = '{}:checked_ts'.format(self.name)
        self.cache_key_updated_ts = '{}:updated_ts'.format(self.name)
        self.cache_key_updating = '{}:updating'.format(self.name)
        self.cache_key_meta = '{}:meta'.format(self.name)
        self.cache_key_body = '{}:body'.format(self.name)
        self.cache_key_lock = '{}:lock'.format(self.name)
        self.init_cache()

    def on_request(self, request):
        self.update_cache()

    def reset_cache(self, pipe):
        self.app.cache.delete(
            self.cache_key_updated_ts,
            self.cache_key_updating,
            self.cache_key_meta,
            self.cache_key_body,
        )

    def init_cache(self):
        with self.app.cache.lock(
            self.cache_key_lock,
            expires=self.lock_timeout,
        ) as lock:
            self.update_cache()

    def update_cache(self):
        # check update timeout
        cache_checked_ts, cache_updated_ts = self.app.cache.mget(
            self.cache_key_checked_ts,
            self.cache_key_updated_ts,
        )
        try:
            cache_checked_ts = int(cache_checked_ts)
            cache_updated_ts = int(cache_updated_ts)
        except (TypeError, ValueError):
            cache_checked_ts = None
            cache_updated_ts = None

        # if check timeout not expired, updating is not required
        if cache_checked_ts:
            if time.time() < (cache_checked_ts + self.check_timeout):
                return cache_updated_ts

        # if other process is already updating cache, we do nothing
        if not self.app.cache.add(self.cache_key_updating, 1, self.lock_timeout):
            return cache_updated_ts

        now_ts = int(time.time())
        try:
            db_updated_ts = self.get_updated_ts_from_db()
        except sa.exc.ProgrammingError as exc:
            logger.warning('Retrieve {} error: {}'.format(self.model, exc))
            return None

        # if db not changed, we update cache checked ts
        if cache_updated_ts and db_updated_ts <= cache_updated_ts:
            with self.app.cache.pipe() as pipe:
                pipe.set(self.cache_key_checked_ts, now_ts)
                pipe.delete(self.cache_key_updating)
                pipe.execute()
            return cache_updated_ts

        # Get sections from db
        items_meta, items_body = self.get_items_from_db()

        items_meta = {s_id: self._dumps(s) \
            for s_id, s in items_meta.items()}
        items_body = {s_id: self._dumps(s) \
            for s_id, s in items_body.items()}

        # Update cache 
        with self.app.cache.pipe() as pipe:
            pipe.set(self.cache_key_updated_ts, db_updated_ts)
            pipe.set(self.cache_key_checked_ts, now_ts)
            pipe.delete(self.cache_key_updating)
            pipe.delete(self.cache_key_meta)
            pipe.delete(self.cache_key_body)
            pipe.hmset(self.cache_key_meta, items_meta)
            if items_body:
                pipe.hmset(self.cache_key_body, items_body)
            pipe.execute()
        return db_updated_ts

    def get_updated_ts_from_db(self):
        session = self.app.db()
        s = sa.sql.select([sa.func.max(self.model.updated_dt)])
        result = list(session.execute(s))
        session.close()
        if result and result[0][0]:
            return int(time.mktime(result[0][0].timetuple()))
        else:
            return None

    def get_items_from_db(self):
        session = self.app.db()
        db_objs = self._get_objs_from_db(session)

        objs_by_id = {obj.id: obj for obj in db_objs}
        items = [obj.to_meta_dict() for obj in db_objs]
        items_by_id = {item['id']: item for item in items}
        items_by_parent = {}
        for item in items:
            if item['parent_id'] is not None:
                parent_item = items_by_id.get(item['parent_id'])
                if not parent_item:
                    continue
            items_by_parent.setdefault(item['parent_id'], []).append(item)

        items = self._walk_tree(items_by_parent)
        items = self._filter_items(items)
        items_meta = {item['id']: item for item in items}
        items_body = {item_id: objs_by_id[item_id].to_body_dict()\
            for item_id in items_meta}
        root_ids = [item['id'] for item in items_by_parent.get(None, [])]
        items_meta[''] = {'children': root_ids}
        session.close()
        return items_meta, items_body

    def get_items(self, ids):
        return self._get_items_meta(ids)

    def get_item(self, id):
        return self.get_items([id])[0]

    def get_items_with_body(self, db, ids):
        with self.app.cache.pipe() as pipe:
            metas = self._get_items_meta(ids)
            bodies = self._get_items_bodies(ids)
        items = []
        for meta, body in zip(metas, bodies):
            if meta is not None and body is not None:
                item = dict(meta, **body)
            else:
                item = None
            items.append(item)
        return items

    def get_item_with_body(self, db, id):
        return self.get_items_with_body(db, [id])[0]

    def _get_items_meta(self, ids):
        if not ids:
            return []
        raw_items = self.app.cache.hmget(self.cache_key_meta, ids)
        items = []
        for id, item in zip(ids, raw_items):
            if item is not None:
                item = self._loads(item)
            items.append(item)
        return items

    def _get_items_bodies(self, ids):
        if not ids:
            return []
        raw_items = self.app.cache.hmget(self.cache_key_body, ids)
        items = []
        for id, item in zip(ids, raw_items):
            if item is not None:
                item = self._loads(item)
            items.append(item)
        return items

    def _walk_tree(self, items_by_parent, parent_item=None):
        result = []
        parent_id = parent_item and parent_item['id'] or None
        for item in items_by_parent.get(parent_id, []):
            item = self._create_item(item, parent_item)
            result.append(item)
            result += self._walk_tree(items_by_parent, item)
        return result

    def _create_item(self, item, parent_item):
        item = item.copy()
        item['children'] = []
        if parent_item is None:
            item['parents'] = []
        else:
            item['parents'] = parent_item['parents'] + [parent_item['id']]
            parent_item['children'].append(item['id'])
        return item

    def _filter_items(self, items):
        return items

    def _get_objs_from_db(self, session):
        return session.query(self.model).order_by(self.model.order.asc()).all()

    def _dumps(self, obj):
        return pickle.dumps(obj)

    def _loads(self, string):
        return pickle.loads(string)


component = Component.create_cls
