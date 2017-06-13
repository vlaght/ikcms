# -*- coding: utf-8 -*-
import os
import re
import json
from collections import OrderedDict
from datetime import datetime, date, time

from iktomi.forms import Field
from iktomi.cms.forms.fields import *
from iktomi.cms.forms.files import FileFieldSetConv, ImageFieldSetConv
from iktomi.cms.flashmessages import flash

from . import convs, widgets, html_body
from models.common import WithState

BaseAjaxImageField = AjaxImageField


def IdField(name='id', conv=convs.Int):
    return Field(name,
                 conv=conv(required=False),
                 widget=widgets.TextInput(template="widgets/id_field",
                                          classname="small"),
                 label=u'Идентификатор',
                 )


def TextareaField(name, label, min_length=1, max_length=250, required=False,
                  hint=None):
    return Field(name,
                 conv=convs.Char(convs.length(min_length, max_length),
                                 required=required),
                 widget=widgets.Textarea(),
                 label=label, hint=hint)


def TextField(name, label, min_length=1, max_length=250,
              required=False, permissions='rw', hint=None):
    return Field(name,
                 conv=convs.Char(convs.length(min_length, max_length),
                                 required=required),
                 widget=widgets.TextInput(),
                 permissions=permissions,
                 label=label, hint=hint)


def EmailField(name, label, required=True, permissions='rw'):
    return Field(name,
                 conv=convs.Email(required=required),
                 widget=widgets.TextInput(),
                 permissions=permissions,
                 label=label)


def SearchFilterField(name, label, min_length=1, max_length=500):
    def filter_query(query, field, filter_value):
        model_field = getattr(field.form.model, field.name)
        for value in filter_value.split():
            query = query.filter(model_field.like("%" + value + "%"))
        return query

    return Field(name,
                 conv=convs.Char(convs.length(min_length, max_length)),
                 widget=widgets.TextInput(),
                 label=label,
                 filter_query=filter_query)


def StreamChoiceField(name, label, model, stream_name, multiple=False,
                      allow_create=False, allow_select=True, allow_delete=True,
                      required=False, condition=None,
                      conv=convs.Int, permissions=None, default_filters=None,
                      sortable=True, unshift=False, conv_cls=None,
                      hint=None):
    extra_kw = {}
    if permissions:
        extra_kw['permissions'] = permissions

    if conv_cls is None:
        conv_cls = convs.ModelChoice

    model_conv = conv_cls(model=model,
                          conv=conv(required=required),
                          condition=condition,
                          required=required)
    if multiple:
        conv = convs.ListOf(model_conv, required=required)
    else:
        conv = model_conv

    return Field(name,
                 label=label,
                 conv=conv,
                 widget=widgets.PopupStreamSelect(
                     stream_name=stream_name,
                     allow_create=allow_create,
                     allow_select=allow_select,
                     allow_delete=allow_delete,
                     sortable=sortable,
                     unshift=unshift,
                     default_filters=default_filters if default_filters else
                     {}),
                 hint=hint,
                 **extra_kw)


def RegionField(name, label, **kwargs):
    kwargs.setdefault('stream_name', 'regions')
    kwargs.setdefault('conv', convs.BaseChar())
    assert 'conv_cls' not in kwargs
    assert 'model' not in kwargs
    kwargs['conv_cls'] = convs.ModelChoiceStr
    kwargs['model'] = 'Region'
    return StreamChoiceField(name, label, **kwargs)


def CountryField(name, label, **kwargs):
    kwargs.setdefault('stream_name', 'countries')
    kwargs.setdefault('conv', convs.BaseChar())
    assert 'conv_cls' not in kwargs
    assert 'model' not in kwargs
    kwargs['conv_cls'] = convs.ModelChoiceStr
    kwargs['model'] = 'Country'
    return StreamChoiceField(name, label, **kwargs)


class AutoPopupStreamSelect(widgets.PopupStreamSelect):
    template = 'widgets/auto_popup_stream_select'


def AutoStreamChoiceField(name, label, model, stream_name,
                          allow_create=False, allow_select=True,
                          allow_delete=True,
                          required=False, condition=None,
                          conv=convs.Int, permissions=None,
                          default_filters=None,
                          sortable=True, unshift=False,
                          hint=None):
    extra_kw = {}
    if permissions:
        extra_kw['permissions'] = permissions

    model_conv = convs.ModelChoice(model=model,
                                   conv=conv(required=required),
                                   condition=condition,
                                   required=required)
    conv = convs.ListOf(model_conv, required=required)

    return Field(name,
                 label=label,
                 conv=conv,
                 widget=AutoPopupStreamSelect(
                     stream_name=stream_name,
                     allow_create=allow_create,
                     allow_select=allow_select,
                     allow_delete=allow_delete,
                     sortable=sortable,
                     unshift=unshift,
                     default_filters=default_filters if default_filters else
                     {}),
                 hint=hint,
                 **extra_kw)


def EnumChoiceField(name, label, choices, required=False, widget=None,
                    permissions='rw', initial=None):
    return Field(name,
                 label=label,
                 conv=convs.EnumChoice(conv=convs.BaseChar(required=required),
                                       choices=choices, required=required),
                 widget=widget and widget or widgets.Select(),
                 initial=initial,
                 permissions=permissions)


def EnumChoiceTabSelectField(name, label, choices, required=False,
                             null_label=u'Все'):
    return EnumChoiceField(
        name, label, choices,
        widget=widgets.Hideable(
            widgets.TabSelect(
                null_label=null_label,
                classname='hidden',
                required=required,
            ),
        )
    )


def find_all_tags(dom_tree, tag_name):
    tags = []
    for node in dom_tree.childNodes:
        if node.nodeType == node.ELEMENT_NODE:
            if node.tagName == tag_name:
                tags.append(node)
            tags.extend(node.getElementsByTagName(tag_name))
    return tags


_media_re = re.compile('^(photos|photosets|videos):\d+$')


def HtmlField(name, label, required=False, medium=False):
    """ Simple Wysihtml-based field accepting only limited number of tags
    Used mostly for LEAD fields.
    """
    Html = convs.MediumHtml if medium else convs.TextHtml
    return Field(name, label=label,
                 conv=Html(
                     allowed_elements=('a', 'p', 'li', 'ul', 'ol', 'i', 'b',
                                       'blockquote', 'hr', 'br'),
                     allowed_protocols=('http', 'https', 'ftp'),
                     allowed_attributes=('href', 'src', 'alt', 'target',
                                         'title', 'class', 'rel', 'border'),
                     required=required),
                 widget=html_body.SimpleWysiHtml5Widget()
                 )


# Seems like we do not use it
# class MediaHtmlFieldClass(Field):
#
#     media_fields_names = []
#     model_url_fields_names = []
#
#     @cached_property
#     def media_fields(self):
#         return [self.form.get_field(name) for name in self.media_fields_names]
#
#     @cached_property
#     def model_url_fields(self):
#         return [self.form.get_field(name)
#                 for name in self.model_url_fields_names]
#
#     def get_tag(self, field_name):
#         for tag, field_name in self.item.media_tags.items():
#             if field_name == field_name:
#                 return tag


def HtmlWithMediaField(name, label, required=True, widget_classname='',
                       with_links_block=False, max_length=1000000):
    if with_links_block:
        widget_cls = html_body.WithLinksBlockWysiHtml5Widget
    else:
        widget_cls = html_body.ExtendedWysiHtml5Widget

    return Field(name=name,
                 label=label,
                 conv=html_body.body_conv(required=required,
                                          max_length=max_length),
                 widget=widget_cls(
                     classname=widget_classname))


def EmbeddedVideoField(name, label, required=False, max_length=10000):
    return Field(name=name,
                 label=label,
                 conv=html_body.embedded_video_conv(required=required,
                                                    max_length=max_length),
                 widget=widgets.Textarea())


# Wrong: this is not Body field
# def BodyField(name, label, required=True):
#     return HtmlField(name, label=label, required=required)



state_choices = [(WithState.PRIVATE, u'Скрытое'),
                 (WithState.PUBLIC, u'Опубликованное')]


def StateSelectField(name, choices, initial=None, null_label=None):
    def filter_query(query, field, filter_value):
        prop = getattr(field.form.model, field.name)
        return query.filter(prop == filter_value)

    return Field(name,
                 conv=convs.EnumChoice(choices=choices,
                                       conv=convs.BaseChar(),
                                       required=True),
                 widget=widgets.LabelSelect(),
                 filter_query=filter_query,
                 initial=initial)


def check_file_exists(conv, value):
    if value and conv.field.writable and not os.path.isfile(value.path):
        msg = u'Файл «{}» утерян: {}. ' \
              u'Восстановите файл или обратитесь к администратору'.format(
            conv.field.label or conv.field.input_name,
            value.url)
        flash(conv.env, msg, 'warning')
    return value


def check_file_has_extension(conv, value):
    if value:
        name, ext = os.path.splitext(value.file_name)
        if name and not ext:
            raise convs.ValidationError(u'У файла отсутствует расширение')
    return value


def FileField(name, label, required=True):
    return AjaxFileField(name,
                         conv=FileFieldSetConv(check_file_has_extension,
                                               required=required),
                         label=label)


def ImageField(name, label, show_thumbnail=True, required=False, show_size=True,
               crop=True):
    return AjaxImageField(name,
                          conv=ImageFieldSetConv(required=required),
                          show_thumbnail=show_thumbnail,
                          label=label,
                          show_size=show_size,
                          crop=crop)


class AjaxImageField(BaseAjaxImageField):
    conv = BaseAjaxImageField.conv(check_file_exists)
    require_upload_handler = True


def SvgImageField(name, label, required=False):
    # TODO: add custom widget with thumbnail for this field
    return FileField(name, label, required)


class LowResImageField(AjaxImageField):
    show_thumbnail = False
    crop = False
    conv = AjaxImageField.conv(autocrop=True)
    widget = AjaxImageField.widget(classname="no-upload")

    def accept(self):
        return AjaxImageField.accept(self)


def BooleanField(name, label, initial=False, permissions='rw'):
    return Field(name,
                 conv=convs.Bool(),
                 widget=widgets.CheckBox(),
                 label=label,
                 initial=initial,
                 permissions=permissions)


def IntegerField(name, label, initial=None, required=False):
    return Field(name,
                 conv=convs.Int(required=required),
                 label=label,
                 initial=initial)


def SlugField(name, label, required=False, permissions='rw',
              widget=widgets.TextInput()):
    return Field(name,
                 conv=convs.Slug(),
                 label=label,
                 required=required,
                 widget=widget,
                 permissions=permissions)


def DateField(name, label, required=False):
    return Field(name,
                 label=label,
                 conv=convs.Date(required=required),
                 widget=widgets.Calendar)


def TitleField(name='title', label=u'Заголовок', max_length=1000,
               required=True, widget=widgets.Textarea, initial='', hint=None):
    conv = convs.Char(convs.length(0, max_length),
                      convs.NoUpper, convs.StripTrailingDot,
                      required=required, typograph=True)
    return Field(name,
                 conv=conv,
                 initial=initial,
                 widget=widget(),
                 label=label,
                 hint=hint)


def ShortTitleField(name='short_title', label=u'Короткий заголовок',
                    max_length=255,
                    hint=u'Используется на главной и в списках'):
    return TitleField(name, label, max_length=max_length, required=False,
                      widget=widgets.TextInput, hint=hint)


def DisplayOnlyField(name, label):
    return Field(name,
                 conv=convs.DisplayOnly,
                 widget=widgets.CharDisplay,
                 permissions='r',
                 label=label)


def DisplayIdField(name='id', label='ID'):
    return DisplayOnlyField(name, label)


def TypeField(types, required=True):
    return EnumChoiceField('type', u'Тип',
                           choices=types,
                           required=required,
                           permissions='r',
                           widget=widgets.ReadonlySelect(), )


def TypeSelectField(types):
    return EnumChoiceField('type', u'Тип',
                           choices=types,
                           required=True,
                           permissions='rw',
                           widget=widgets.Select(), )


# class FieldGroup(FieldSet):
#     widget = widgets.FieldGroupWidget
#
#     def accept(self):
#         return {field.name: field.raw_value for field in self.fields}


class LinksConv(convs.TabbedModelDictConv):
    # XXX using index is not good idea: we have to redefine values if we remove
    #     some choices from the middle of tabs list.
    #     We do not use garant and consultant links on english version and in
    #     HighlighZone.
    indicator_fields = {}
    title_field = 'ref_title'

    def to_python(self, value):
        _kind = value['_kind']
        for field, kind in self.indicator_fields.items():
            if kind != _kind:
                value[field] = None
            elif not value[field]:
                raise convs.ValidationError(u'вы должны выбрать материал или ' \
                                            u'указать URL для ссылки')

        if value.get('ref_url') and self.title_field:
            self.assert_(value[self.title_field],
                         u'вы должны указать текст ссылки')
        return convs.TabbedModelDictConv.to_python(self, value)


def LinksField(models, name, model, validators=(),
               label=u'Ссылки', hint=None):
    tabs = [
        (None, 'id', '_kind'),
        (u'Материал', 'ref_doc', 'ref_title'),
        (u'Файл', 'ref_file', 'ref_title'),
        (u'Ссылка', 'ref_url', 'ref_title'),
    ]

    tabs = [x for x in tabs if getattr(model, x[1], None) is not None]
    indicator_fields = OrderedDict((x[1], i)
                                   for i, x in enumerate(tabs[1:])
                                   if getattr(model, x[1], None) is not None)
    # XXX very useful functionality from kremlin.ru
    # validators += (link_to_internal,)

    fieldset = TabbedFieldSet(
        None,
        conv=LinksConv(model=model,
                       indicator_fields=indicator_fields,
                       *validators),
        fields=[
            Field('id', conv=convs.Int(),
                  widget=widgets.HiddenInput),
            StreamChoiceField('ref_doc', u'Материал',
                              models.Doc, 'docs',
                              allow_create=True),
            UrlField('ref_url'),
            StreamChoiceField('ref_file', u'Файл',
                              models.File, 'files',
                              allow_create=True),

            Field('_kind',
                  conv=convs.Int(),
                  initial=0,
                  widget=widgets.HiddenInput),
            Field('ref_title',
                  conv=convs.Char(convs.length(0, 500),
                                  typograph=True),
                  label=u'Текст ссылки'),
        ],
        trigger_field='_kind',
        tabs=tabs)

    fieldset.fields = [x for x in fieldset.fields
                       if getattr(model, x.name, None) is not None]

    return FieldList(name, order=True, field=fieldset, label=label, hint=hint)


class TabbedFieldSet(FieldSet):
    # XXX should not work???

    """
    Usage:
        TabbedFieldSet('fieldset_name'
            tabs = [
                (None, 'commonfield1', 'hidden_field'),
                (u'tab1', 'foo', 'bar'),
                (u'tab2', 'spam', 'eggs')
                ],
                select_tab = lambda field, value: 1,
                trigger_field = 'hidden_field',
                use_field = True, # Save only selected tab
                fields=[.....]
        )

    trigger field will contain number of selected tab
    if it's conv is int. if it's enumchoice, corresponding
    value will be selected (by index)
    """

    trigger_field = None
    use_trigger = True

    widget = FieldSet.widget(template='widgets/tabbed_fieldset')

    def __init__(self, *args, **kwargs):
        assert 'tabs' in kwargs, '"tabs" is required argument for ' \
                                 'TabbedFieldSet'
        super(TabbedFieldSet, self).__init__(*args, **kwargs)
        self.common_fields = []
        self.tabbed_fields = []
        index = 0
        for tab in self.tabs:
            if tab[0] is None:
                self.common_fields = tab[1:]
            else:
                self.tabbed_fields.append(
                    dict(tab=tab[0], fields=tab[1:], index=index))
                index += 1
        self.tabbed_fields_list = []
        for field in [field.name for field in self.fields]:
            for tab in self.tabbed_fields:
                if field in tab[
                    'fields'] and field not in self.tabbed_fields_list:
                    self.tabbed_fields_list.append(field)

    @staticmethod
    def select_tab(field, value):
        # overrided in most cases

        if field.trigger_field:
            trigger = field.get_field(field.trigger_field)
            try:
                return int(field.form.raw_data[trigger.input_name])
            except (ValueError, KeyError):
                if value[field.trigger_field] is not None:
                    return value[field.trigger_field]
                return 0

        else:
            tabs = field.tabbed_fields
            tabs_fields = sum([list(t['fields']) for t in tabs], [])
            for tab in tabs:
                for f in tab['fields']:
                    if tabs_fields.count(f) > 1:
                        continue
                    if value[f]:
                        return tab['index']
        return 0

    @property
    def json_config(self):
        conf = dict(tabbed_fields=[tab['fields'] for tab in self.tabbed_fields],
                    common_fields=self.common_fields,
                    tabbed_fields_list=self.tabbed_fields_list,
                    active_tab=self.active_tab)

        if self.trigger_field:
            field = self.get_field(self.trigger_field)
            conf['trigger_id'] = field.id

        return json.dumps(conf)

    @property
    def active_tab(self):
        return self.select_tab(self, self.python_data)

    def get_field(self, name):
        for field in self.fields:
            if field.name == name:
                return field
        raise KeyError, name

    def get_initial(self):
        result = {}
        for field in self.fields:
            result[field.name] = field.get_initial()
        return self.conv.to_python_default(result)

    def accept(self, roles=None):
        if 'w' not in self.perm_getter.get_perms(self):
            raise convs.SkipReadonly
        result = self.python_data

        active_fields = self.tabbed_fields[self.active_tab]['fields']
        active_fields += self.common_fields

        result = dict(self.python_data)
        for field in self.fields:
            if field.writable:
                if self.trigger_field and self.use_trigger:
                    if field.name in active_fields:
                        result.update(field.accept())
                    else:
                        # XXX field blocks will not work!
                        result[field.name] = None
                else:
                    result.update(field.accept())
            else:
                # readonly field
                field.set_raw_value(self.form.raw_data,
                                    field.from_python(result[field.name]))
        self.clean_value = self.conv.accept(result)
        return {self.name: self.clean_value}


def UrlField(name, label=u'URL', max_length=250, required=False,
             domain_is_required=True, classname='link_source direct',
             unique=False, hint=u'Адрес страницы, включая http://'):
    conv_args = [convs.length(0, max_length)]
    if unique:
        conv_args.append(convs.DBUnique())
    conv_kwargs = dict(domain_is_required=domain_is_required,
                       required=required)
    conv = convs.UrlConv(*conv_args, **conv_kwargs)
    return Field(name,
                 conv=conv,
                 widget=widgets.TextInput(classname=classname),
                 label=label,
                 hint=hint)


class AnyFieldBlock(convs.FieldBlockConv):
    """
    At least one field in this FieldBlock must have value.
    """

    def accept(self, value, silent=False):
        if not any(value.values()):
            e = convs.ValidationError(message=u'required field')
            e.fill_errors(self.field)
        return super(AnyFieldBlock, self).accept(value, silent=silent)


def SelectWithCustomChoiceField(name, label, choices):
    """
    Model, used with this field, should have fields
    Enum('name') and String('_custom_' + name), e.g.
    title = Enum(...)
    _custom_title = String()
    """
    custom_choice_name = 'custom_' + name
    fields = [
        EnumChoiceField(name, label, choices,
                        widget=widgets.Select(
                            classname='custom-choice',
                            null_label=u'-- Свой вариант --')
                        ),
        Field(custom_choice_name,
              conv=convs.Char(convs.length(1, 250), required=False),
              widget=widgets.TextInput(classname='hidden custom-choice-text'))
    ]
    return FieldBlock(
        'title',
        label=label,
        fields=fields,
        conv=AnyFieldBlock(),
        widget=FieldBlock.widget(template='widgets/select_with_custom_choice',
                                 classname='', render_type='')
    )


def SpecialProjectClassifierField(models, name='special_projects',
                                  label=u'Спецпроекты'):
    return Field(name,
                 conv=convs.ListOf(convs.ModelChoice(
                     condition=models.SiteSection.page_type ==
                               models.SiteSection.types.special_project,
                     model=models.SiteSection),
                     required=False),
                 label=label,
                 widget=widgets.PopupFilteredSelect())


def DocQuestionsField(name, models, label=u'Вопросы'):
    QuestionModel = models.DocQuestion
    QuestionMaterialModel = models.DocQuestionMaterial

    material_fieldset = FieldSet(
        'material', conv=convs.ModelDictConv(model=QuestionMaterialModel),
        fields=[
            Field('id', conv=convs.Int(required=False),
                  widget=widgets.HiddenInput),
            TextareaField('title', label=u'Название', required=True,
                          min_length=3, max_length=255),
            TextareaField('url', label=u'url',
                          required=False),
            StreamChoiceField('file', u'файл',
                              models.File,
                              multiple=False, stream_name='files')
        ],
    )
    material_fieldlist = FieldList('materials',
                                   field=material_fieldset, label=u'Материалы',
                                   allow_create=True, allow_delete=True)

    fieldset = FieldSet(
        name, conv=convs.ModelDictConv(model=QuestionModel),
        fields=[
            Field('id', conv=convs.Int(required=False),
                  widget=widgets.HiddenInput),
            TextareaField('title', label=u'Вопрос', required=True,
                          min_length=3, max_length=999),
            TextareaField('body', label=u'Расширенное описание вопроса',
                          required=False),
            material_fieldlist
        ],
    )

    return FieldList(name, field=fieldset, label=label,
                     allow_create=True, allow_delete=True)


def SectionsField(models, name='sections', label=u'Ленты событий'):
    return StreamChoiceField(name, label,
                             models.SiteSection, required=False,
                             multiple=True,
                             stream_name='sections')


def SectionEventsField(name='events'):
    return Field(name,
                 widget=widgets.TextInput(template="widgets/section_events"),
                 label=u'События',
                 )


class DateTimeIntervalConv(convs.Converter):
    def to_python(self, value):
        if isinstance(value['since'], datetime) \
                and isinstance(value['till'], datetime) \
                and value['since'] > value['till']:
            raise convs.ValidationError(
                u'дата начала не может быть больше даты завершения')
        return value


class SplitDateTimeFilterConv(convs.SplitDateTime):
    def to_python(self, value):
        date_ = value['date']
        time_ = value['time']
        if date_ is None and time_ is None:
            return None
        elif date_ is None:
            date_ = date.today()
        elif time_ is None:
            time_ = time(0)
        res = datetime.combine(date_, time_)
        return res


def SplitDateTimeFilterField(name, label, required=True,
                             get_initial=datetime.now,
                             template='widgets/fieldset-line'):
    return FieldSet(
        name,
        widget=widgets.FieldSetWidget(js_block='datetime',
                                      template=template),
        conv=SplitDateTimeFilterConv(required=required),
        fields=[Field('date',
                      conv=convs.Date(required=required),
                      widget=widgets.Calendar(js_block='calendar-simple')),
                Field('time',
                      conv=convs.Time(required=required),
                      widget=widgets.TextInput(classname='timeinput'))],
        get_initial=get_initial,
        label=label)


class SplitDateTimeFromTo(DateFromTo):
    conv = DateTimeIntervalConv

    fields = [
        SplitDateTimeFilterField('since', label=u'С', required=False,
                                 get_initial=lambda: None),
        SplitDateTimeFilterField('till', label=u'По', required=False,
                                 get_initial=lambda: None),
    ]

    def filter_query(self, query, field, value):
        model = self.form.model
        if value['since'] is not None:
            query = query.filter(getattr(model, self.name) >= value['since'])
        if value['till'] is not None:
            query = query.filter(getattr(model, self.name) < value['till'])
        return query
