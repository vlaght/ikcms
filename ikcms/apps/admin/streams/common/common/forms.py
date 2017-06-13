# -*- coding: utf-8 -*-

from iktomi.cms.stream import FilterForm as BaseFilter
from iktomi.cms.forms import ModelForm as BaseModelForm
from iktomi.unstable.db.sqla.files import FileAttribute
from iktomi.unstable.db.sqla.images import ImageFile
from iktomi.unstable.forms.files import FileFieldSet


class FilterForm(BaseFilter):
    def get_data(self, compact=True):
        """
        Sort of hack: We need `__copy_from_id` parameter only to load initial
        values to ModelForm. To avoid saving it un url, we are forced to
        remove it here, because query string is constructed from form data.
        """
        data = super(FilterForm, self).get_data(compact=compact)
        data.pop('__copy_from_id', None)
        return data


class DuplicableModelForm(BaseModelForm):
    # Fields with this names/types will not be copied to duplicate item
    _private_field_names = ('id', )
    _private_value_types = (FileAttribute, ImageFile)

    # id's from objects from this field should be removed, because
    # it couse duplication error.
    _detached_fields = []

    @classmethod
    def load_initial(cls, env, item, initial=None, **kwargs):
        """
        If `__copy_from_id` parameter is presented in GET request, `item` is
        treated as duplicate of existing object. Get this object from db
        and fill `initial` from object's field values. Fields from
        `_private_field_names` and `_private_value_types` will not be copied.

        !!! If you need to overload this method, do not forget to use super().

        If form contains FieldBlock with fields=FieldList with specified model
        to provide duplication support and prevent Duplicate db error we should
        null ids of linked objects.
        """
        if initial is None:
            initial = {}

        if item.id is None:
            original_id = env.request.GET.pop('__copy_from_id', None)
            if original_id:
                original_item = env.db.query(item.__class__) \
                    .filter_by(id=original_id).first()
                initial = cls._load_initial(original_item, initial, cls.fields)

                initial = {name: value for name, value in initial.items()
                           if name not in cls._private_field_names and
                           not isinstance(value, cls._private_value_types)}

                if cls._detached_fields:
                    for field in cls._detached_fields:
                        detached_items = initial.get(field, [])
                        for item in detached_items:
                            item.id = None
        else:
            initial = cls._load_initial(item, initial, cls.fields)

        return cls(env, initial, item=item, **kwargs)
