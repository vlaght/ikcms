import sys
from lxml import etree

SPHINX_NAMESPACE = 'http://sphinxsearch.com/'

_ns = '{' + SPHINX_NAMESPACE + '}'


class BaseSlot(object):

    def __init__(self, name):
        self.name = name

    def convert(self, value):
        return unicode(value)


class Field(BaseSlot):

    def write_schema(self, xf):
        with xf.element(_ns + 'field', name=self.name):
            pass


class BaseAttr(BaseSlot):

    type = None

    def __init__(self, name, default=None):
        BaseSlot.__init__(self, name)
        self.default = default

    def _schema_attrib(self):
        attrs = {'name': self.name, 'type': self.type}
        if self.default is not None:
            attrs['default'] = self.convert(self.default)
        return attrs

    def write_schema(self, xf):
        with xf.element(_ns + 'attr', attrib=self._schema_attrib()):
            pass


class Int(BaseAttr):

    type = 'int'
    bits = None

    def __init__(self, name, bits=32, default=None):
        BaseAttr.__init__(self, name, default=default)
        assert bits in xrange(1, 33)
        self.bits = int(bits)

    def _schema_attrib(self):
        attrs = BaseAttr._schema_attrib(self)
        attrs['bits'] = str(self.bits)
        return attrs


class BigInt(BaseAttr):

    type = 'bigint'


class String(BaseAttr):

    type = 'string'


class Bool(BaseAttr):

    type = 'bool'

    def convert(self, value):
        return '1' if value else '0'


class Float(BaseAttr):

    type = 'float'


class Multi(BaseAttr):
    '''List of int32'''

    type = 'multi'

    def convert(self, value):
        return ' '.join(str(item) for item in value)


class Timestamp(BaseAttr):

    type = 'timestamp'

    def convert(self, value):
        return value.strftime('%s')


class Pipe(object):

    def __init__(self, fields, attrs=[], fp=sys.stdout):
        self.slots = {s.name: s for s in [Field(n) for n in fields] + attrs}
        self._xf_cm = etree.xmlfile(fp, encoding='utf-8')

    def __enter__(self):
        self._xf = xf = self._xf_cm.__enter__()
        xf.write_declaration()
        self._root = xf.element(_ns + 'docset',
                                nsmap={'sphinx': SPHINX_NAMESPACE})
        self._root.__enter__()
        self.write_schema()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._root.__exit__(exc_type, exc_value, exc_tb)
        self._xf_cm.__exit__(exc_type, exc_value, exc_tb)

    def write_schema(self):
        with self._xf.element(_ns + 'schema'):
            for slot in self.slots.values():
                slot.write_schema(self._xf)

    def document(self, id, **data):
        with self._xf.element(_ns + 'document', id=str(id)):
            for name, value in data.items():
                slot = self.slots[name]
                value = slot.convert(value)
                with self._xf.element(name):
                    self._xf.write(value)

    def killlist(self, ids):
        with self._xf.element(_ns + 'killlist'):
            for id in ids:
                with self._xf.element('id'):
                    self._xf.write(str(id))
