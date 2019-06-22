
import datetime
import logging
import uuid
import time
import json

import tornado.web
import tornado.websocket
import tornado.ioloop

from tornado import gen
from tornado.options import define, options


define("port", default=3000, help="run on the given port", type=int)
define("message", default="PING", help="send the given message", type=str)

connected_clients = {}
TIMEOUT = 5


class Application(tornado.web.Application):

    def __init__(self):

        handlers = [(r"/", SocketHandler), (r"/list", ApiHandler)]
        settings = dict(debug=True)
        tornado.web.Application.__init__(self, handlers, **settings)


class ApiHandler(tornado.web.RequestHandler):
    def get(self):
        client_list = [str(x) for x in connected_clients.keys()]
        output = {"connected_clients": client_list}
        self.write(json.dumps(output))


class SocketHandler(tornado.websocket.WebSocketHandler):

    def __init__(self, *args, **kwargs):

        tornado.websocket.WebSocketHandler.__init__(self, *args, **kwargs)
        self.id = None
        self.last_sent = None
        self.last_received = None

    def  check_origin(self, origin):

        return True

    def open(self):

        """Called when a websocket connection is initiated."""

        self.id = uuid.uuid1()
        if id not in connected_clients:
            connected_clients[self.id] = self
            logging.info("client with id %s connected", self.id)

    def _check_for_timeout(self):

        if self.last_sent is None:
            return True

        time_elapsed = time.time() - self.last_sent

        if time_elapsed > TIMEOUT:
            self.on_close()
            return True

        return False

    def on_message(self, message):

        """Called when a websocket connection receive message from client."""

        if self._check_for_timeout():
            logging.info("TimeOut for client with id %s", self.id)

        self.last_received = time.time()
        logging.info("Received %s from client id %s", message, self.id)

    def on_close(self):

        """Called when a websocket connection is closed."""

        if self.id in connected_clients:
            del connected_clients[self.id]
            logging.info("client with id %s disconnected", self.id)


@gen.coroutine
def broadcast(message):

    """Broadcast message to every connected client"""

    while True:
        # send message to every connected client

        for uid in connected_clients:
            ws_client = connected_clients[uid]

            # check before sending whether connection is alive
            if not ws_client.ws_connection.stream.socket:
                logging.error("Web socket %s does not exist", uid)
                del connected_clients[uid]

            elif ws_client.last_received < ws_client.last_sent:
                logging.error("Web socket %s taking too much time to respond, Hence closing", uid)
                ws_client.close()
                del connected_clients[uid]

            else:
                ws_client.write_message(message)
                ws_client.last_sent = tornado.ioloop.IOLoop.current().time()
                logging.info("Sending %s to socket id %s", message, uid)

        # wait for 30 seconds before sending next broadcast message
        yield gen.Task(
            tornado.ioloop.IOLoop.current().add_timeout,
            datetime.timedelta(seconds=30))


def main():
    tornado.options.parse_command_line()

    app = Application()
    app.listen(options.port)

    main_loop = tornado.ioloop.IOLoop.instance()

    # send first broadcast after 30 seconds
    main_loop.add_timeout(datetime.timedelta(seconds=30), broadcast, options.message)

    # Start main loop
    main_loop.start()


if __name__ == "__main__":
    main()
