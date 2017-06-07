import os
import pkg_resources
from urlparse import urlparse


class UrlBase(object):

    def __init__(self, url):
        super(UrlBase, self).__init__()
        self._url = url

    def isdir(self):
        raise NotImplementedError

    def isfile(self):
        raise NotImplementedError

    def exists(self):
        raise NotImplementedError

    def open_file(self, mode='r'):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError

    def listdir(self):
        raise NotImplementedError

    def dirname(self):
        raise NotImplementedError

    def makedirs(self):
        raise NotImplementedError

    def isreadonly(self):
        raise NotImplementedError

    def join(self, path):
        raise NotImplementedError

    def __str__(self):
        return self._url.geturl()


class FSUrl(UrlBase):

    def __init__(self, root, url):
        super(FSUrl, self).__init__(url)
        self.root = root
        if self._url.netloc:
            raise ValueError('Netloc not allowed', str(self))
        if self._url.params:
            raise ValueError('Params not allowed', str(self))
        if self._url.query:
            raise ValueError('Query not allowed', str(self))
        if self._url.fragment:
            raise ValueError('Fragment not allowed', str(self))
        self.path = os.path.join(root, url.path)

    def isdir(self):
        return os.path.isdir(self.path)

    def isfile(self):
        return os.path.isfile(self.path)

    def exists(self):
        return os.path.exists(self.path)

    def open_file(self, mode='r'):
        return open(self.path, mode)

    def read(self):
        with self.open() as f:
            return f.read()

    def listdir(self):
        return os.path.listdir(self.path)

    def dirname(self):
        return os.path.dirname(self.path)

    def makedirs(self):
        if not self.exists():
            os.makedirs(self.path)

    def isreadonly(self):
#XXX
        return False

    def join(self, path):
        return os.path.join(self.path, path)

    def __str__(self):
        return self.path


class PKGResourcesUrl(UrlBase):

    def __init__(self, url):
        super(PKGResourcesUrl, self).__init__(url)
        if self._url.params:
            raise ValueError('Params not allowed', str(self))
        if self._url.query:
            raise ValueError('Query not allowed', str(self))
        if self._url.fragment:
            raise ValueError('Fragment not allowed', str(self))
        self.package = url.netloc
        self.path = url.path

    def isdir(self):
        return pkg_resources.resource_isdir(self.package, self.path)

    def isfile(self):
        return self.exists() and not self.isdir()

    def exists(self):
        return pkg_resources.resource_exists(self.package, self.path)

    def open_file(self, mode='r'):
        if mode not in ('r', 'rb', 'U'):
            raise ValueError('File is readonly', str(self))
        return pkg_resources.resource_stream(self.package, self.path)

    def read(self):
        with self.open() as f:
            return f.read()

    def listdir(self):
        return pkg_resources.resource_listdir(self.package, self.path)

    def isreadonly(self):
        return True


SCHEMES = {
    '': lambda cfg, url: FSUrl(cfg.ROOT_DIR, url),
    'pkg': lambda cfg, url: PKGResourcesUrl(url),
}


class PathBase(object):

    def __init__(self, cfg, str_path, schemes=None):
        super(PathBase, self).__init__()
        self.cfg = cfg
        url = urlparse(str_path)
        if schemes is None:
            schemes = list(SCHEMES)
        if url.scheme not in schemes or url.scheme not in SCHEMES:
            raise ValueError(
                'Schema {} not allowed'.format(url.scheme),
                str(self),
            )
        self.url = SCHEMES[url.scheme](cfg, url)
        self.scheme = url.scheme

    def __str__(self):
        return str(self.url)


class DirPath(PathBase):

    def __init__(self, cfg, str_path, schemes=['']):
        super(DirPath, self).__init__(cfg, str_path, schemes)

    def check(self):
        if not self.url.exists():
            raise ValueError('Dir not exists', str(self))
        if not self.url.isdir():
            raise ValueError('Is not dir', str(self))

    def exists(self):
        return self.url.exists()

    def listdir(self):
        return self.url.listdir()

    def join(self, path):
        return self.url.join(path)

    def makedirs(self):
        self.url.makedirs()


class FilePath(PathBase):

    def __init__(self, cfg, str_path, schemes=['']):
        super(FilePath, self).__init__(cfg, str_path, schemes)

    def check(self):
        if not self.url.exists():
            raise ValueError('File not exists', str(self))
        if not self.url.isfile():
            raise ValueError('Is not file', str(self))

    def exists(self):
        return self.url.exists()

    def open(self, mode='r'):
        return self.url.open_file(mode)

    def read(self):
        return self.url.read()

    def dirname(self):
        return DirPath(self.cfg, self.url.dirname())

    def makedirs(self):
        self.dirname().makedirs()

    def isreadonly(self):
        return self.url.isreadonly()

