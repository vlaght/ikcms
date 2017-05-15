from unittest import TestCase
from unittest.mock import MagicMock

from ikcms.forms import exceptions
from ikcms.forms import fields


class BaseTestCase(TestCase):

    field_cls = fields.Base
    type_error_values = []
    test_values = [
        ('test_str', 'test_str'),
        (5, 5),
        ({'aa', 22}, {'aa', 22}),
        ([3, 6], [3, 6]),
    ]
    to_python_default_values = ['test_str', None, 5, [3, 6]]


    validation_tests = []


    def test_init(self):
        context = MagicMock()
        parent = MagicMock()
        field = self.field()(context, parent)
        self.assertEqual(field.context, context.copy())
        self.assertEqual(field.parent, parent)

    def test_to_python(self):
        field = self.field()()
        for python_value, raw_value in self.test_values:
            self.assertEqual(
                field.to_python(raw_value),
                python_value,
                self._to_python_message(raw_value, python_value),
            )
        for value in self.type_error_values:
            with self.assertRaises(exceptions.RawValueTypeError) as ctx:
                field.to_python(value)
            self.assertEqual(ctx.exception.kwargs['field_name'], field.name)

        for kwargs, allowed_values, denied_values in self.validation_tests:
            field = self.field(**dict(kwargs, ))()
            for value in allowed_values:
                field.to_python(value)
            for value in denied_values:
                with self.assertRaises(exceptions.ValidationError):
                    field.to_python(value)

    def test_to_python_default(self):
        field = self.field(raw_required=False)()
        self.assertEqual(field.to_python(fields.NOTSET), fields.NOTSET)
        for value in self.to_python_default_values:
            field = self.field(to_python_default=value, raw_required=False)()
            self.assertEqual(field.to_python(fields.NOTSET), value)

    def test_raw_required(self):
        field = self.field()()
        with self.assertRaises(exceptions.RawValueRequiredError) as ctx:
            field.to_python(fields.NOTSET)
        self.assertEqual(ctx.exception.kwargs['field_name'], field.name)

    def test_from_python(self):
        field = self.field()()
        for python_value, raw_value in self.test_values:
            self.assertEqual(field.from_python(python_value), raw_value)

    def field(self, **kwargs):
        kwargs.setdefault('name', 'test')
        return type('TestField', (self.field_cls,), kwargs)

    def _to_python_message(self, raw_value, value):
        return "{}().to_python({})!={}".format(
            self.field_cls.__name__,
            raw_value,
            value,
        )

    def _from_python_message(self, value, raw_value):
        return "{}().from_python({})!={}".format(
            self.field_cls.__name__,
            value,
            raw_value,
        )


class FieldTestCase(BaseTestCase):

    field_cls = fields.Field

    def test_to_python(self):
        field = self.field()()
        for python_value, raw_value in self.test_values:
            self.assertEqual(
                field.to_python(self.test_dict(field.name, raw_value)),
                {field.name: python_value},
            )

        for value in self.type_error_values:
            with self.assertRaises(exceptions.RawValueTypeError) as ctx:
                field.to_python(self.test_dict(field.name, value))
            self.assertEqual(ctx.exception.kwargs['field_name'], field.name)

        for kwargs, allowed_values, denied_values in self.validation_tests:
            field = self.field(**dict(kwargs, ))()
            for value in allowed_values:
                field.to_python(self.test_dict(field.name, value))
            for value in denied_values:
                with self.assertRaises(exceptions.ValidationError) as ctx:
                    field.to_python(self.test_dict(field.name, value))
                self.assertEqual(
                    list(ctx.exception.kwargs['error'].keys()),
                    [field.name],
                )


    def test_to_python_default(self):
        field = self.field(raw_required=False)()
        self.assertEqual(field.to_python(self.test_dict()), {})

        for value in self.to_python_default_values:
            field = self.field(to_python_default=value, raw_required=False)()
            self.assertEqual(
                field.to_python(self.test_dict()),
                {field.name: value},
            )

    def test_raw_required(self):
        field = self.field(raw_required=True)()
        with self.assertRaises(exceptions.RawValueRequiredError) as ctx:
            field.to_python(self.test_dict())
        self.assertEqual(ctx.exception.kwargs['field_name'], field.name)

    def test_from_python(self):
        field = self.field()()
        for python_value, raw_value in self.test_values:
            self.assertEqual(
                field.from_python(self.test_dict(field.name, python_value)),
                {field.name: raw_value},
            )

    def test_dict(self, name=None, value=None):
        d = {
            'other1': 'str value',
            'other2': 7777,
            'other3': None,
            5: 'this not wrong',
            None: 'xxx',
        }
        if name:
            d[name] = value
        return d


class StringTestCase(FieldTestCase):

    field_cls = fields.String

    test_values = {
        ('test_str', 'test_str'),
        ('', ''),
    }
    type_error_values = [
        5, {'d': 'teet'}, [2, 4], 66.2, set((4, 5, 6)), (3, 4), MagicMock(),
    ]
    validation_tests = [
        ({'required': True}, ['test_str', '325566'], ['']),
        ({'min_len': 3}, ['test_str', '325', '333'*40], ['', '1', '23']),
        ({'max_len': 3}, ['', '3', '32', '123'], ['1234', '23'*5]),
        (
            {'regex': '[abs]{3}$'},
            ['bsa', 'abs'],
            ['ab', 'abd', 'absabs', ''],
        ),
    ]


class IntTestCase(FieldTestCase):

    field_cls = fields.Int

    test_values = [
        (1, 1),
        (-4, -4),
        (500, 500),
        (0, 0),
    ]
    type_error_values = [
        '5', {'d': 'teet'}, [2, 4], 66.2, set((4, 5, 6)), (3, 4), MagicMock(),
        'dddddd',
    ]
    validation_tests = [
        ({'required': True}, [5, 10, -6, 0], []),
        ({'min_value': 3}, [3, 325, 333*40], [-50, 0, 1, 2]),
        ({'max_value': 3}, [-50, 0, 1, 2, 3], [4, 10, 104, 5*600]),
    ]


class IntStrTestCase(FieldTestCase):

    field_cls = fields.IntStr

    test_values = [
        (1, '1'),
        (-4, '-4'),
        (500, '500'),
        (0, '0'),
    ]
    type_error_values = [
        5, 0, -6, 66.2,
        {'d': 'teet'}, [2, 4], set((4, 5, 6)), (3, 4), MagicMock(),
    ]
    validation_tests = [
        ({'required': True}, ['5', '10', '-6', '0'], ['asss', '5.5', '66sx']),
        ({'min_value': 3}, ['3', '325'], ['-50', '0', '1', '2']),
        ({'max_value': 3}, ['-50', '0', '1', '2', '3'], ['4', '10', '104']),
    ]



class DictTestCase(FieldTestCase):

    field_cls = fields.Dict
    type_error_values = [5, [2, 4], "ddddd", MagicMock()]
    test_values = [
        (
            {'f1': 'value1', 'f2': 'value2'},
            {'f1': 'value1', 'f2': 'value2'},
        ),
        (
            {'f1': 'value1', 'f2': None},
            {'f1': 'value1', 'f2': None},
        ),

    ]
    validation_tests = [
        (
            {'required': True},
            [
                {
                    'f1': 'value1',
                    'f2': 'value2',
                    'other4': 'value3',
                },
                {
                    'f1': 'value1',
                    'f2': 'value2',
                },
            ],
            []
        ),
    ]

    def field(self, **kwargs):
        class f1(fields.Field):
            name = 'f1'
        class f2(fields.Field):
            name = 'f2'
            not_none = False
        kwargs.setdefault('fields', [f1, f2])
        return super().field(**kwargs)


class ListTestCase(FieldTestCase):

    field_cls = fields.List
    type_error_values = [5, {'x':'xxx'}, "ddddd", MagicMock()]
    test_values = [
        ([], []),
        ([1, 2, 3], [1, 2, 3]),
        ([1, 3], [1, 3]),
        ([{}, [], []], [{}, [], []]),
    ]

    validation_tests = [
        (
            {'required': True},
            [[1, 2, 3], [[]]],
            [[]],
        ),
    ]

    def field(self, **kwargs):
        kwargs.setdefault('fields', [fields.Field])
        return super().field(**kwargs)


class BlockTestCase(BaseTestCase):

    field_cls = fields.Block
    type_error_values = [
        {'test': 5},
        {'test': [2, 4]},
        {'test': "ddddd"},
        {'test': MagicMock()},
    ]
    to_python_default_values = []

    test_values = [
        (
            {
                'f1': 'value1',
                'f2': 'value2'
            },
            {
                'test': {
                    'f1': 'value1',
                    'f2': 'value2',
                },
            },
        ),
        (
            {
                'f1': 'value1',
                'f2': None,
            },
            {
                'test': {
                    'f1': 'value1',
                    'f2': None,
                }
            }
        ),
    ]
    validation_tests = [
        (
            {
                'required': True,
            },
            [
                {
                    'test': {
                        'f1': 'value1',
                        'f2': 'value2',
                        'other4': 'value3',
                    },
                },
                {
                    'test': {
                        'f1': 'value1',
                        'f2': 'value2',
                    },
                },
            ],
            [],
        ),
    ]

    def field(self, **kwargs):
        class f1(fields.Field):
            name = 'f1'
        class f2(fields.Field):
            name = 'f2'
            not_none = False
        kwargs.setdefault('fields', [f1, f2])
        return super().field(**kwargs)

    def test_to_python_default(self):
        field = self.field(raw_required=False)()
        self.assertEqual(field.to_python({}), {})

        for value in self.to_python_default_values:
            field = self.field(to_python_default=value)()
            self.assertEqual(field.to_python({}), value)

    def test_raw_required(self):
        field = self.field(raw_required=True)()
        with self.assertRaises(exceptions.RawValueRequiredError) as ctx:
            field.to_python({})
        self.assertEqual(ctx.exception.kwargs['field_name'], field.name)


