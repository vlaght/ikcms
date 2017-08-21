import math

from ikcms.utils import cached_property


class PageNotFound(Exception):
    pass


class Paginator(object):

    class Page(object):

        def __init__(self, paginator, number, items):
            self.paginator = paginator
            self.count = self.paginator.count
            self.number = number
            self.items = items
            self.first = bool(number == 1)
            self.last = bool(number == paginator.pages_count)
            self.has_prev = not self.first
            self.has_next = not self.last
            self.next_page_number = self.has_next and (self.number + 1) or None
            self.prev_page_number = self.has_prev and (self.number - 1) or None

        def __iter__(self):
            return self.items.__iter__()

        @cached_property
        def next_page(self):
            if self.has_next:
                return self.paginator.page(self.number + 1)

        @cached_property
        def prev_page(self):
            if self.has_prev:
                return self.paginator.page(self.number - 1)



    def __init__(self, query, limit):
        self.query = query
        self.limit = limit
        self.count = query.count()
        self.pages_count = int(math.ceil(float(self.count or 1) / self.limit))

    def page(self, page):
        try:
            page = int(page)
            if (page < 1) or (page > self.pages_count):
                raise ValueError
        except (TypeError, ValueError):
            raise PageNotFound(page)
        return self.Page(self, page, self._get_items(page))

    def _get_items(self, page):
        return self.query[self.limit * (page - 1):self.limit * page]

