# coding: utf-8

from iktomi.cms.forms.widgets import *  # For module inheritance
import json


def ReadonlyInput():
    return widgets.TextInput(template="widgets/readonly_input",
                             classname="small")


def ReadonlySelect():
    return widgets.Select(template="widgets/readonly_select",
                          classname="small")


class Hideable(object):

    template = 'widgets/hideable'

    def __init__(self, widget):
        self._widget = widget

    def __getattr__(self, name):
        return getattr(self._widget, name)

    def __call__(self, *args, **kwargs):
        return self.__class__(self._widget(*args, **kwargs))

    def render(self):
        field = self._widget.field
        if field.name+'-hide' not in field.form.raw_data:
            return self._widget.render()
        else:
            data = self.prepare_data()
            return self.env.template.render(self.template, **data)


class DiscusPopupStreamSelect(PopupStreamSelect):
    def item_row(self, item, row_cls=''):
        """ CopyPaste of original one to rewrite url definition """
        url = self.stream.item_url(self.env, item=item)
        read_allowed = self.stream.has_permission(self.env, 'r')
        return self.render_row_template(stream=self.stream,
                                        item=item,
                                        list_fields=self.list_fields,
                                        read_allowed=read_allowed,
                                        url=url, row_cls=row_cls)


class PhotoPosition(widgets.Widget):

    template = 'widgets/photo_position'

    @property
    def js_config(self):
        data = {
            'image_css_class': self.image_css_class,
            'title': 'Настройка положения фото',
            'container': self.id,
            'input_name': self.input_name,
        }
        return json.dumps(data)

    def prepare_data(self):
        return dict(widgets.Widget.prepare_data(self),
                    js_config=self.js_config)
