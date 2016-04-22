import logging
import json

from .exc import BaseError, MessageError
from . import messages

logger = logging.getLogger(__name__)


class AppBase:
    def __init__(self, cfg):
        """ Called before started ws server """
        self.cfg = cfg

    async def __call__(self, server, client_id):
        """ Called when recived message """
        raise NotImplemented


class App(AppBase):

    messages = messages

    def __init__(self, cfg):
        self.client_envs = {}
        self.cfg = cfg
        self.cfg.config_uid()
        self.cfg.config_logging()
        self.env_class = self.get_env_class()
        self.handlers = self.get_handlers()

    def get_handlers(self):
        return {}

    def get_env_class(self):
       from .env import Environment
       return Environment

    @property
    def clients(self):
        return self.client_envs.values()

    async def __call__(self, server, client_id):
        env = self.env_class(self, server, client_id)
        self.client_envs[client_id] = env
        try:
            while True:
                try:
                    raw_message =  await server.recv(client_id)
                    message = self.messages.Message.from_json(raw_message)
                    handler = self.handlers.get(message['name'])
                    if not handler:
                        raise MessageError(
                           'Handler "{}" not allowed'.format(message['name']))
                    await handler(env, message['body'])
                except BaseError as e:
                    logger.debug(str(e))
                    error_message = self.messages.ErrorMessage(str(e), e.code)
                    await server.send(client_id, error_message.to_json())
        finally:
            del self.client_envs[client_id]

