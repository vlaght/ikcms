from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock
from ikcms.forms.convs import *
from ikcms.forms import exceptions
from ikcms.forms import fields


class _BaseConvTestCase(TestCase):

    conv_class = None
    test_values = []
    raw_type_error_values = []
    python_type_error_values = []
    validation_error_values = []

    def setUp(self):
        field = MagicMock(not_null=False, name='test_name')
        self.conv = self.conv_class(field)

    def test_to_python(self):
        for python_value, raw_value in self.test_values:
            self.assertEqual(
                python_value,
                self.conv.to_python(raw_value),
                self._to_python_message(python_value, raw_value),
            )
        for value in self.raw_type_error_values:
            self.assertRaises(
                exceptions.RawValueTypeError,
                self.conv.to_python,
                value,
            )

        for value in self.validation_error_values:
            self.assertRaises(
                exceptions.ValidationError,
                self.conv.to_python,
                value,
            )

    def test_not_none(self):
        self.assertRaises(
                exceptions.RawValueNoneNotAllowedError,
            self.conv.to_python,
            None,
        )
        self.assertRaises(
            exceptions.PythonValueNoneNotAllowedError,
            self.conv.from_python,
            None,
        )
        self.conv.field.not_none = False
        self.assertEqual(
            None,
            self.conv.to_python(None),
            self._to_python_message(None, None),
        )
        self.assertEqual(
            None,
            self.conv.from_python(None),
            self._from_python_message(None, None),
        )

    def test_from_python(self):
        for python_value, raw_value in self.test_values:
            self.assertEqual(
                raw_value,
                self.conv.from_python(python_value),
                self._from_python_message(python_value, raw_value),
            )
        for value in self.python_type_error_values:
            self.assertRaises(
                exceptions.PythonValueTypeError,
                self.conv.from_python,
                value,
            )

    def _to_python_message(self, raw_value, value):
        return "{}().to_python({})!={}".format(
            self.conv_class.__name__,
            raw_value,
            value,
        )

    def _from_python_message(self, value, raw_value):
        return "{}().from_python({})!={}".format(
            self.conv_class.__name__,
            value,
            raw_value,
        )


class BoolConvTestCase(_BaseConvTestCase):

    conv_class = Bool
    test_values = [
        (True, True),
        (False, False),
    ]
    raw_type_error_values = [0, 1, -5, 7.6, '', 'aaa', [], {}, [1, 3]]
    python_type_error_values = raw_type_error_values


class IntConvTestCase(_BaseConvTestCase):
    conv_class = Int
    test_values = [
        (-1, -1),
        (0, 0),
        (10, 10),
    ]
    raw_type_error_values = ['23', 'sss', 4.5, [1, 2], {1: 1}]
    python_type_error_values = raw_type_error_values


class IntStrConvTestCase(_BaseConvTestCase):
    conv_class = IntStr
    test_values = [
        (-1, '-1'),
        (0, '0'),
        (10, '10'),
    ]
    raw_type_error_values = [23, 4.5, [1, 2], {1: 1}]
    python_type_error_values = ['23', 'sss', 4.5, [1, 2], {1: 1}]
    validation_error_values = ["2.2", "dddd", "fr45g", "-7-"]


class StrConvTestCase(_BaseConvTestCase):
    conv_class = Str
    test_values = [
        ("", ""),
        ("11", "11"),
        ("aaa123", "aaa123"),
    ]
    raw_type_error_values = [True, False, 5, 5.6, [], {}, [1, 3]]
    python_type_error_values = raw_type_error_values


class ListConvTestCase(_BaseConvTestCase):

    conv_class = List
    test_values = [
        ([], []),
        ([1], [1]),
        ([1, 2], [1, 2]),
    ]
    raw_type_error_values = [
        True, False, 5, 5.6, "test", {}, {"test":[]},
    ]
    python_type_error_values = raw_type_error_values

    def setUp(self):
        field = MagicMock(
            not_null=False,
            name='test_name',
            fields=[fields.Int()],
        )
        self.conv = self.conv_class(field)


class DictConvTestCase(_BaseConvTestCase):

    conv_class = Dict
    test_values = [
        (
            {'str_field': 'str', 'int_field': 1},
            {'str_field': 'str', 'int_field': 1},
        ),
    ]
    raw_type_error_values = []
    python_type_error_values = raw_type_error_values


    def setUp(self):
        str_field = fields.Field()
        str_field.name = 'str_field'
        str_field.conv = Str(str_field)
        str_field.raw_required = False
        str_field.to_python_default = 'str_default'
        int_field = fields.Field()
        int_field.name = 'int_field'
        int_field.conv = Int(int_field)
        int_field.raw_required = False
        int_field.to_python_default = 'int_default'
        int_field.to_python = int_field.to_python
        field = fields.Field()
        field.fields = [str_field, int_field]
        self.conv = Dict(field)


class DateConvTestCase(_BaseConvTestCase):
    conv_class = Date
    test_values = [
        (date(2016, 6, 15), '2016-06-15'),
    ]

    raw_type_error_values = [True, False, 5, 5.6, [], {}, [1, 3]]
    python_type_error_values = raw_type_error_values

    def setUp(self):
        field = MagicMock(
            not_null=False,
            name='test_name',
            format='%Y-%m-%d',
        )
        self.conv = self.conv_class(field)

