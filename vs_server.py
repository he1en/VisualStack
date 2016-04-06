from subprocess import call

import BaseHTTPServer
import SocketServer

PORT = 8000

#Handler = SimpleHTTPServer.SimpleHTTPRequestHandler

#httpd = SocketServer.TCPServer(("", PORT), Handler)

print "serving at port", PORT
print call(["ls", "-l"])
#httpd.serve_forever()


def run_while_true(server_class=BaseHTTPServer.HTTPServer,
                   handler_class=BaseHTTPServer.BaseHTTPRequestHandler):
    """
    This assumes that keep_running() is a function of no arguments which
    is tested initially and after each request.  If its return value
    is true, the server continues.
    """
    server_address = ('', PORT)
    httpd = server_class(server_address, handler_class)
    i = 0
    while i < 20:
        httpd.handle_request()
        i+=1

run_while_true()
