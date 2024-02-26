"""
Simple API used to test how efficient and reliable the cache is.

Usage:
poetry run webapp --help
"""

from datetime import datetime
from logging import info
import sys
from time import sleep

from tornado.ioloop import IOLoop
from tornado.options import define, options, parse_command_line
from tornado.web import Application, RequestHandler

from rediscache import RedisCache

sys.set_int_max_str_digits(10000)

define("port", default=9090, help="Port to listen on")

rediscache = RedisCache()


@rediscache.cache(2, 10, default="default", wait=True)
def long_function(value: str) -> str:
    """
    This is the function we will need to cache
    """
    # Simulate IO
    sleep(0.5)
    # A bit of heavy calculation: 2000!
    for _ in range(10):
        fact = 1
        for i in range(1, 2001):
            fact = fact * i
    # Return a string that depends on 'value'
    return f"{value} at {datetime.utcnow()}: \n{fact}"


class DirectHandler(RequestHandler):  # pylint: disable=abstract-method,too-few-public-methods
    """
    Calls the function with no cache.
    """

    def get(self, value: str) -> None:
        """
        It's a simple browser request, therefore a GET.
        """
        self.write(long_function.function(value))  # type: ignore


class CachedHandler(RequestHandler):  # pylint: disable=abstract-method,too-few-public-methods
    """
    Calls the function with the cache.
    """

    def get(self, value: str) -> None:
        """
        It's a simple browser request, therefore a GET.
        """
        self.write(long_function(value))


class StatsHandler(RequestHandler):  # pylint: disable=abstract-method,too-few-public-methods
    """
    Calls the function with the cache.
    """

    def get(self) -> None:
        """
        It's a simple browser request, therefore a GET.
        """
        self.write(rediscache.get_stats())


def main() -> None:
    """
    Entry point
    """
    parse_command_line()
    app = Application(
        [
            (r"/direct/(.+)", DirectHandler),
            (r"/cached/(.+)", CachedHandler),
            (r"/stats", StatsHandler),
        ],
        debug=True,
    )
    app.listen(options.port)
    info(f"Listening on port {options.port}.")
    # Stopping the application with a Ctrl+C only works on the console
    print("Press Ctrl+C to terminate.")
    try:
        IOLoop.current().start()
    except KeyboardInterrupt:
        print()  # Go to the next line after the Ctrl+C
        info("Web application manually stopped.")
        # At this point the tornado application is still running
        IOLoop.current().stop()


if __name__ == "__main__":
    main()
