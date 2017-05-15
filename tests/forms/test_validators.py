from unittest import TestCase
from unittest.mock import MagicMock
from ikcms.forms.validators import *
from ikcms.forms import exceptions


class RequiredTestCase(TestCase):
    def test_is_required(self):
        field = MagicMock()
        field.required = True
        field.required_error = 'Field is required'
        validator = Required(field)
        for value in ['', [], {}, None]:
            with self.assertRaises(exceptions.ValidationError) as ctx:
                validator(value)
            exc = ctx.exception
            self.assertEqual(exc.kwargs['error'], field.required_error)

    def test_is_not_required(self):
        field = MagicMock()
        field.required = False
        field.required_error = 'Field is required'
        validator = Required(field)
        for value in ['', [], {}, None]:
            validator(value)


class RegexTestCase(TestCase):
    def test_regex(self):
        field = MagicMock()
        field.regex = r'\d{4}-\d{2}-\d{2}'
        field.regex_error = 'Field does not match regex'
        validator = Regex(field)
        with self.assertRaises(exceptions.ValidationError) as ctx:
            validator('invalid')
        self.assertEqual(ctx.exception.kwargs['error'], field.regex_error)
        validator('2016-06-15')


class LenTestCase(TestCase):
    def test_len(self):
        field = MagicMock()
        field.min_len = 1
        field.max_len = 10
        field.min_len_error = 'Minimum length error'
        field.max_len_error = 'Maximum length error'
        validator = Len(field)
        validator(list(range(1)))
        validator(list(range(5)))
        validator(list(range(10)))
        with self.assertRaises(exceptions.ValidationError) as ctx:
            validator(list(range(0)))
        self.assertEqual(ctx.exception.kwargs['error'], field.min_len_error)
        with self.assertRaises(exceptions.ValidationError) as ctx:
            validator(list(range(11)))
        self.assertEqual(ctx.exception.kwargs['error'], field.max_len_error)


class RangeTestCase(TestCase):
    def test_range(self):
        field = MagicMock()
        field.min_value = 1
        field.max_value = 10
        field.min_value_error = 'Minimum value error'
        field.max_value_error = 'Maximum value error'
        validator = Range(field)
        validator(1)
        validator(5)
        validator(10)
        with self.assertRaises(exceptions.ValidationError) as ctx:
            validator(0)
        self.assertEqual(ctx.exception.kwargs['error'], field.min_value_error)
        with self.assertRaises(exceptions.ValidationError) as ctx:
            validator(11)
        self.assertEqual(ctx.exception.kwargs['error'], field.max_value_error)
