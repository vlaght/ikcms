import os
import asyncio
import logging
import mimetypes
import collections
import email.message
import websockets
import websockets.http
import websockets.handshake
import websockets.protocol


logger = logging.getLogger(__name__)


class HTTPResponse:
    default_content_type = 'text/html'
    default_charset = 'UTF-8'
    default_status = '200 OK'

    def __init__(self, body, status=None, content_type=None, charset=None):
        self.body = body
        self.status = status or self.default_status
        self.content_length = str(len(body))
        self.content_type = content_type or self.default_content_type
        if content_type.startswith('text/'):
            charset = charset or self.default_charset
            self.content_type += ';charset={}'.format(charset)

    def __str__(self):
        headers = [
            ('Content-Type', self.content_type),
            ('Content-Length', self.content_length),
        ]
        response = ['HTTP/1.1 ', self.status, '\r\n']
        for key, value in headers:
            response.append('{}: {}\r\n'.format(key, value))
        response.append('\r\n')
        response.append(self.body)
        return ''.join(response)


def try_files(root, path):
    def translate(root, path):
        parts = filter(None, path.split('/'))
        for part in parts:
            drive, part = os.path.splitdrive(part)
            head, part = os.path.split(part)
            if drive or head or part in [os.curdir, os.pardir]:
                return None
        return os.path.join(root, path)
    filename = translate(root, path)
    if filename is None or not os.path.exists(filename):
        body = 'File not found'
        return HTTPResponse(body, status='404 Not Found')
    with open(filename) as fp:
        content_type, charset = mimetypes.guess_type(filename)
        body = fp.read()
        return HTTPResponse(body, content_type=content_type, charset=charset)


class TryFilesError(Exception):
    def __init__(self, path):
        self.path = path


class WebSocketServerProtocol(websockets.WebSocketServerProtocol):

    @asyncio.coroutine
    def handshake(self, origins=None, subprotocols=None, extra_headers=None):
        # Read handshake request.
        try:
            path, headers = yield from websockets.http.read_request(self.reader)
        except Exception as exc:
            raise websockets.InvalidHandshake("Malformed HTTP message") from exc

        self.request_headers = headers
        self.raw_request_headers = list(headers.raw_items())

        get_header = lambda k: headers.get(k, '')

        try:
            key = websockets.handshake.check_request(get_header)
        except websockets.InvalidHandshake as exc:
            raise TryFilesError(path)

        if origins is not None:
            origin = get_header('Origin')
            if not set(origin.split() or ['']) <= set(origins):
                raise websockets.InvalidOrigin("Origin not allowed: {}".format(origin))

        if subprotocols is not None:
            protocol = get_header('Sec-WebSocket-Protocol')
            if protocol:
                client_subprotocols = [p.strip() for p in protocol.split(',')]
                self.subprotocol = self.select_subprotocol(
                    client_subprotocols, subprotocols)

        headers = []
        set_header = lambda k, v: headers.append((k, v))
        set_header('Server', websockets.http.USER_AGENT)
        if self.subprotocol:
            set_header('Sec-WebSocket-Protocol', self.subprotocol)
        if extra_headers is not None:
            if callable(extra_headers):
                extra_headers = extra_headers(path, self.raw_request_headers)
            if isinstance(extra_headers, collections.abc.Mapping):
                extra_headers = extra_headers.items()
            for name, value in extra_headers:
                set_header(name, value)
        websockets.handshake.build_response(set_header, key)

        self.response_headers = email.message.Message()
        for name, value in headers:
            self.response_headers[name] = value
        self.raw_response_headers = headers

        # Send handshake response. Since the status line and headers only
        # contain ASCII characters, we can keep this simple.
        response = ['HTTP/1.1 101 Switching Protocols']
        response.extend('{}: {}'.format(k, v) for k, v in headers)
        response.append('\r\n')
        response = '\r\n'.join(response).encode()
        self.writer.write(response)

        assert self.state == websockets.protocol.CONNECTING
        self.state = websockets.protocol.OPEN
        self.opening_handshake.set_result(True)

        return path

    @asyncio.coroutine
    def handler(self):
        # Since this method doesn't have a caller able to handle exceptions,
        # it attemps to log relevant ones and close the connection properly.
        try:

            try:
                path = yield from self.handshake(
                    origins=self.origins, subprotocols=self.subprotocols,
                    extra_headers=self.extra_headers)
            except Exception as exc:
                logger.info("Exception in opening handshake: {}".format(exc))
                if isinstance(exc, TryFilesError):
                    response = try_files(exc.path)
                elif isinstance(exc, websockets.InvalidOrigin):
                    response = 'HTTP/1.1 403 Forbidden\r\n\r\n' + str(exc)
                elif isinstance(exc, websockets.InvalidHandshake):
                    response = 'HTTP/1.1 400 Bad Request\r\n\r\n' + str(exc)
                    import pdb;pdb.set_trace()
                else:
                    response = ('HTTP/1.1 500 Internal Server Error\r\n\r\n'
                                'See server log for more information.')
                self.writer.write(response.encode())
                raise

            try:
                yield from self.ws_handler(self, path)
            except Exception:
                logger.error("Exception in connection handler", exc_info=True)
                yield from self.fail_connection(1011)
                raise

            try:
                yield from self.close()
            except Exception as exc:
                logger.info("Exception in closing handshake: {}".format(exc))
                raise

        except Exception:
            # Last-ditch attempt to avoid leaking connections on errors.
            try:
                self.writer.close()
            except Exception:                               # pragma: no cover
                pass

        finally:
            # Unregister the connection with the server when the handler task
            # terminates. Registration is tied to the lifecycle of the handler
            # task because the server waits for tasks attached to registered
            # connections before terminating.
            self.ws_server.unregister(self)
