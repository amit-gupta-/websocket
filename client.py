from tornado.ioloop import IOLoop
from tornado import gen
from tornado.websocket import websocket_connect
import datetime

REPLY = "PONG"


class Client(object):

    def __init__(self, url):
        self.url = url
        self.ioloop = IOLoop.instance()
        self.ws = None
        self.connect()
        self.ioloop.start()

    @gen.coroutine
    def connect(self):

        try:
            # connect to websocket
            self.ws = yield websocket_connect(self.url)
        except Exception, e:
            print("Exception while connecting %s", e)
        else:
            print("Client connected")
            self.run()

    @gen.coroutine
    def run(self):
        while True:
            # read message when available
            msg = yield self.ws.read_message()

            if msg is not None:
                print("Received" + msg + " message from Server")
                print("Sending" + REPLY + " to the Server")
                self.ws.write_message(REPLY)

            else:
                print("Closing connection")
                self.ws = None
                break


if __name__ == "__main__":

    # create client
    client = Client("ws://localhost:3000/")
