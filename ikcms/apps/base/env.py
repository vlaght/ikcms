from iktomi.utils.storage import StorageFrame
from iktomi.utils.storage import VersionedStorage
from iktomi.utils.storage import storage_property
from iktomi.web.route_state import RouteState

class Environment(StorageFrame):

    def __init__(self, app=None, request=None, root=None, _parent_storage=None, **kwargs):
        super(Environment, self).__init__(_parent_storage=_parent_storage, **kwargs)
        self.app = app
        self.request = request
        if self.request:
            self.root = self.app.root.bind_to_env(self._root_storage)
            self._route_state = RouteState(request)
        else:
            self.root = root

    @classmethod
    def create(cls, *args, **kwargs):
        return VersionedStorage(cls, *args, **kwargs)

    def close(self):
        pass

    @storage_property
    def current_location(self):
        ns = getattr(self, 'namespace', '')
        url_name = getattr(self, 'current_url_name', '')
        return '.'.join(filter(None, (ns, url_name)))

