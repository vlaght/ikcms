import time
import logging
import cPickle as pickle

import sqlalchemy as sa


logger = logging.getLogger(__name__)


class CachedModel(object):

    check_timeout = 5
    lock_timeout = 5
    checked_ts = 0

    def __init__(self, component, model_path):
        self.component = component
        self.app = component.app
        self.model_path = model_path
        self.model = self.app.db.get_model(model_path)
        self.preview = hasattr(self.app, 'preview')
        self.front_db_id = self.preview and 'admin' or 'front'
        t = time.time()
        self.init_cache()
        logging.info('{} cache initialized: {}'.format(
            model_path,
            time.time()-t,
        ))

    def reset_cache(self, pipe):
        self.app.cache.delete(
            self._cache_key('checked_ts'),
            self._cache_key('updated_ts'),
            self._cache_key('updating'),
            self._cache_key('items'),
            self._cache_key('indexes'),
        )

    def init_cache(self):
        with self.app.cache.lock(
            self._cache_key('lock'),
            expires=self.lock_timeout,
        ) as lock:
            self.update_cache()

    def update_cache(self):
        if time.time() < (self.checked_ts + self.check_timeout):
            return

        # check update timeout
        cache_checked_ts, cache_updated_ts = self.app.cache.mget(
            self._cache_key('checked_ts'),
            self._cache_key('updated_ts'),
        )
        try:
            cache_checked_ts = int(cache_checked_ts)
            self.checked_ts = cache_checked_ts
            cache_updated_ts = int(cache_updated_ts)
        except (TypeError, ValueError):
            cache_checked_ts = None
            cache_updated_ts = None

        # if check timeout not expired, updating is not required
        if cache_checked_ts:
            if time.time() < (cache_checked_ts + self.check_timeout):
                return cache_updated_ts

        # if other process is already updating cache, we do nothing
        if not self.app.cache.add(
                self._cache_key('updating'),
                1,
                self.lock_timeout,
        ):
            return cache_updated_ts

        now_ts = int(time.time())
        try:
            db_updated_ts = self.get_updated_ts_from_db()
        except sa.exc.DBAPIError as exc:
            logger.warning('Retrieve {} error: {}'.format(self.model, exc))
            return None

        # if db not changed, we update cache checked ts
        if cache_updated_ts and db_updated_ts <= cache_updated_ts:
            with self.app.cache.pipe() as pipe:
                pipe.set(self._cache_key('checked_ts'), now_ts)
                pipe.delete(self._cache_key('updating'))
                pipe.execute()
                self.checked_ts = now_ts
            return cache_updated_ts

        # Get items from db
        try:
            items = self.get_items_from_db()
        except sa.exc.DBAPIError as exc:
            logger.warning('Retrieve sections error: {}'.format(exc))
            return None

        indexes = self.create_indexes(items)
        raw_items = {id: self._dumps(item) for id, item in items.items()}
        raw_indexes = {id: self._dumps(item) for id, item in indexes.items()}

        # Update cache 
        with self.app.cache.pipe() as pipe:
            pipe.set(self._cache_key('updated_ts'), db_updated_ts)
            pipe.set(self._cache_key('checked_ts'), now_ts)
            if raw_items:
                pipe.hmset(self._cache_key('items'), raw_items)
            if raw_indexes:
                pipe.hmset(self._cache_key('indexes'), raw_indexes)
            pipe.delete(self._cache_key('updating'))
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
        items = {obj.id: obj.to_dict() for obj in db_objs}
        session.close()
        return items

    def get_items(self, ids):
        if not ids:
            return []
        raw_items = self.app.cache.hmget(self._cache_key('items'), ids)
        items = []
        for id, item in zip(ids, raw_items):
            if item is not None:
                item = self._loads(item)
            items.append(item)
        return items

    def get_all(self):
        raw_items = self.app.cache.hvals(self._cache_key('items'))
        return [self._loads(item) for item in raw_items]

    def get(self, id, default=None):
        item = self.get_items([id])[0]
        if item is None:
            return default
        else:
            return item

    def get_index(self, name):
        raw_index = self.app.cache.hget(self._cache_key('indexes'), name)
        if not raw_index:
            raise Exception('Index "{}" not found'.format(name))
        index = self._loads(raw_index)
        return self.get_items(index)

    def create_indexes(self, items):
        return {}

    def _get_objs_from_db(self, session):
        return session.query(self.model).all()

    def _cache_key(self, name):
        return '{}:{}'.format(self.model_path, name)

    def _query(self, session):
        return session.query(self.model)

    def _dumps(self, obj):
        return pickle.dumps(obj)

    def _loads(self, string):
        return pickle.loads(string)

    def __iter__(self):
        return self.get_all().__iter__()

