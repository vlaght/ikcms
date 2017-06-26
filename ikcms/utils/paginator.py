import math

class Paginator(object):

    class Page(object):

        def __init__(self, paginator, page, items):
            self.paginator = paginator
            self.page = page
            self.items = items
            self.first = bool(page==1)
            self.last = bool(page==paginator.pages_count)

        def __iter__(self):
            return self.items.__iter__()

    def __init__(self, query, limit):
        self.query = query
        self.limit = limit
        self.count = query.count()
        self.pages_count = int(math.ceil(float(self.count or 1) / self.limit))

    def page(self, page):
        page = int(page)
        if (page < 1) or (page > self.pages_count):
            raise ValueError
        return self.Page(self, page, self._get_items(page))

    def _get_items(self, page):
        return self.query[self.limit * (page - 1):self.limit * page]

