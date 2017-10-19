import ikcms.components.render.jinja2.custom_tags


class IktomiMediaTag(ikcms.components.render.jinja2.custom_tags.Tag):

    item_field_name = 'medias'
    tags = ['iktomi_media']
    template = 'tags/iktomi_{media.type}'
    media_types = ('photo', 'photoset', 'video')

    def func(self, env, item, **kwargs):
        try:
            media_id = int(kwargs.get('item_id'))
        except (TypeError, ValueError):
            return None
        collection = getattr(item, self.item_field_name)
        media = next((b for b in collection if b.id == media_id), None)
        if media:
            assert media.type in self.media_types, \
                'Unknown media type {}'.format(media.type)
            return dict(
                env=env,
                item=item,
                media=media,
                **kwargs
            )
        else:
            return None


class IktomiPhotoTag(IktomiMediaTag):

    item_field_name = 'photos'
    tags = ['iktomi_photo']
    template = 'tags/iktomi_photo.html'
    media_types = ('photo',)


class IktomiPhotosetTag(IktomiMediaTag):

    item_field_name = 'photosets'
    tags = ['iktomi_photoset']
    template = 'tags/iktomi_photoset.html'
    media_types = ('photoset',)


class IktomiVideoTag(IktomiMediaTag):

    item_field_name = 'videos'
    tags = ['iktomi_video']
    template = 'tags/iktomi_video.html'
    media_types = ('video',)


iktomi_media = IktomiMediaTag
iktomi_photo = IktomiPhotoTag
iktomi_photoset = IktomiPhotosetTag
iktomi_video = IktomiVideoTag
