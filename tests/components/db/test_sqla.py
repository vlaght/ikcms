from unittest import TestCase, skipIf
from unittest.mock import MagicMock

from sqlalchemy import sql
from ikcms.components.db.sqla import component

from tests.cfg import cfg
from tests.models import create_models1, create_models2


try:
    import MySQLdb
    mysql_skip = False
except ImportError:
    mysql_skip = True

try:
    raise ImportError
    import psycopg2
    pg_skip = False
except ImportError:
    pg_skip = True


class SQLAComponentTestCase(TestCase):

    test_models = {
        'db1': create_models1(),
        'db2': create_models2(),
    }

    @skipIf(mysql_skip, 'MySQLdb not installed')
    def test_mysql(self):
        self._db_test(cfg.MYSQL_URL)

    @skipIf(pg_skip, 'Psycopg2 not instaled')
    def test_postgress(self):
        self._db_test(cfg.POSTGRESS_URL)

    def _db_test(self, db_url):
        app = MagicMock()
        del app.db
        app.cfg.DATABASES = {
            'db1': db_url,
            'db2': db_url,
        }

        def get_models(db_id):
            self.assertIn(db_id, app.cfg.DATABASES)
            return self.test_models[db_id]

        Component = component(get_models=get_models)

        db = Component.create(app)
        self.assertEqual(db.models, self.test_models)
        engine1 = db.engines['db1']
        engine2 = db.engines['db2']
        self.assertEqual(db.binds[self.test_models['db1'].test_table1], engine1)
        self.assertEqual(db.binds[self.test_models['db2'].test_table2], engine2)
        test_table1 = self.test_models['db1'].test_table1

        session = db()
        db.reset_all()
        Test = db.models['db1'].Test
        test = Test(id=5, title='test_title')
        session.add(test)
        session.commit()
        test = session.query(Test).filter_by(id=5).one()
        self.assertEqual(test.id, 5)
        self.assertEqual(test.title, 'test_title')

        test.title = 'test_title2'
        session.commit()
        cnt = session.query(Test).filter_by(id=5, title='test_title2').count()
        self.assertEqual(cnt, 1)

        session.delete(test)
        session.commit()
        cnt = session.query(Test).filter_by(id=5, title='test_title2').count()
        self.assertEqual(cnt, 0)
        session.close()

