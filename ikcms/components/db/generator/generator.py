# -*- coding: utf-8 -*-
from StringIO import StringIO
from models.common.fields import ExpandableMarkup
from datetime import datetime, timedelta
from random import randint, choice, sample, randrange, random

from iktomi.unstable.db.sqla.factories import return_locals
from .vesna import phrase, randname


# import logging
# logging.basicConfig()
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

def _create_image_file(file_manager, width, height):
    from iktomi.unstable.db.sqla.images import Image as PILImage
    image = PILImage.new('RGB', (width, height), (randint(1, 240),
                                                  randint(1, 240),
                                                  randint(1, 240), 1))
    fp = StringIO()
    image.save(fp, 'JPEG')
    fp.seek(0)
    temp_file = file_manager.create_transient(fp, '%s.%s' %
                                              (randint(1, 10000000), '.jpg'))
    fp.close()
    return temp_file
    # return None


class GeneratorField(object):
    pass


class FullName(GeneratorField):
    def __call__(self, app):
        return randname()


class FirstName(GeneratorField):
    def __call__(self, app):
        return randname().split(' ')[1]


class LastName(GeneratorField):
    def __call__(self, app):
        return randname().split(' ')[0]


class Image(GeneratorField):
    def __init__(self, width=1600, height=900):
        self.width = width
        self.height = height

    def __call__(self, app):
        file_manager = app.admin_file_manager
        return _create_image_file(file_manager, self.width, self.height)


class Date(GeneratorField):
    def __init__(self, years=None):
        self.years = years or [datetime.now().year - 1]

    def __call__(self, app):
        return datetime(choice(self.years), randint(1, 12), randint(1, 28))


class Text(GeneratorField):
    def __init__(self, min_length=20, max_length=250, html=False):
        self.min_length = min_length
        self.max_length = max_length
        self.html = html

    def __call__(self, app):
        if self.html:
            return '\n'.join(
                ['<p>%s</p>' % self.chunk() for _ in range(1, randint(2, 10))])
        return self.chunk()

    def chunk(self):
        return phrase()[:randint(self.max_length, self.max_length + 1)]


class NumberedTitle(GeneratorField):
    def __init__(self, title):
        self.title = title

    def __call__(self, app):
        return "%s %d" % (self.title, randint(1, 10000))


class EHTMLText(Text):
    def __call__(self, app):
        return ExpandableMarkup(super(EHTMLText, self).__call__(app))


class Words(GeneratorField):
    def __init__(self, min_length=4, count=1):
        self.min_length = min_length
        self.count = count

    def __call__(self, app):
        chunk = phrase()[:100]
        words = chunk.split(u' ')
        words = [word[:-1] if word.endswith(',') else word for word in words]
        words = [word.title() for word in words if len(word) > self.min_length]
        words = words[:self.count]
        return u' '.join(words)


class Slug(Words):
    pass


class Constant(GeneratorField):
    def __init__(self, value):
        self.value = value

    def __call__(self, app):
        return self.value


class Choice(GeneratorField):
    def __init__(self, choices):
        self.choices = choices

    def __call__(self, app):
        return choice(self.choices)


class TrueOrFalse(Choice):
    def __init__(self):
        self.choices = (True, False)


class Relation(GeneratorField):
    def __init__(self, model, multiple=False,
                 min_count=1, max_count=5, self_related=False):
        self.model = model
        self.multiple = multiple
        self.min_count = min_count
        self.max_count = max_count
        self.self_related = self_related

    def __call__(self, db, id=0):
        items = db.query(self.model).all()
        items = filter(lambda x: x.id != id, items)
        if self.multiple:
            max_count = min(self.max_count, len(items))
            min_count = min(self.min_count, max_count)
            return sample(items, randint(min_count, max_count))
        return choice(items)


class Generate(object):
    registered = []

    @classmethod
    def run(cls, app, names=[]):
        for f in cls.registered:
            if not names or f.name in names:
                print 'Generating %i item(s) for: %s' % (f.count, f.model)
                f(app)

    def __init__(self, model, **kwargs):
        self.model = model
        self.__dict__.update(kwargs)

    def __call__(self, f):
        def wrapper(app):
            db = app.db()
            f_locals = return_locals(f)(db, self.model)

            for n in range(0, self.count):
                plain_fields = {
                    k: v(app) for k, v in f_locals.iteritems() if
                    isinstance(v, GeneratorField) and not isinstance(v, Relation)
                }
                relation_fields = {k: v(db) for k, v in f_locals.iteritems() if
                                   isinstance(v, Relation)}
                obj = self.model(**plain_fields)
                db.add(obj)

                if hasattr(obj, '_create_versions'):
                    obj._create_versions()

                db.flush()
                [setattr(obj, k, v) for k, v in relation_fields.iteritems()]
                db.add(obj)
                if callable(getattr(obj, 'publish', None)):
                    if random() > 0.2:
                        obj.publish()

                db.commit()

        wrapper.count = self.count
        wrapper.model = self.model
        wrapper.name = f.func_name
        self.registered.append(wrapper)
        return wrapper



class Update(Generate):
    registered = []

    @classmethod
    def run(cls, app, names=[]):
        for f in cls.registered:
            if not names or f.name in names:
                print 'Updating item(s) for: %s' % (f.model)
                f(app)

    def __call__(self, f):
        def wrapper(app):
            db = app.db()
            f_locals = return_locals(f)(db, self.model)
            for obj in db.query(self.model):
                plain_fields = {
                    k: v(app) for k, v in f_locals.iteritems() if
                    isinstance(v, GeneratorField) and not isinstance(v, Relation)
                }
                relation_fields = {k: v(db, obj.id) for k, v in
                                   f_locals.iteritems() if
                                   isinstance(v, Relation)}
                for key, value in plain_fields.items():
                    setattr(obj, key, value)
                for key, value in relation_fields.items():
                    setattr(obj, key, value)
                db.commit()
                if random() > 0.2:
                    obj.publish()

        wrapper.model = self.model
        wrapper.name = f.func_name
        self.registered.append(wrapper)
        return wrapper


class Generator(object):

    def __init__(self):
        self.generate = type('Generate', (Generate,), dict(registered=[]))
        self.update = type('Update', (Update,), dict(registered=[]))

    def __call__(self, component, names):
        self.generate.run(component.app, names)
        self.update.run(component.app, names)

