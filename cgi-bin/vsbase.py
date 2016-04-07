#!/usr/bin/env python

import sys; sys.path.insert(0, 'lib') # this line is necessary for the rest
import os                             # of the imports to work!

import web
from jinja2 import Environment, FileSystemLoader

import gdb_writer


# helper method to render a template in the templates/ directory
#
# `template_name': name of template file to render
#
# `**context': a dictionary of variable names mapped to values
# that is passed to Jinja2's templating engine
#
def render_template(template_name, **context):
    extensions = context.pop('extensions', [])
    globals = context.pop('globals', {})

    jinja_env = Environment(autoescape=True,
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'vstemplates')),
            extensions=extensions,
            )
    jinja_env.globals.update(globals)

    web.header('Content-Type','text/html; charset=utf-8', unique=True)

    return jinja_env.get_template(template_name).render(context)

urls = ('/visualstack', 'visual_stack')
#writer = None

class visual_stack:
  def GET(self):
    return render_template('vs.html', stack = None)
  def POST(self):
    post_params = web.input()
    gdb_command = post_params['gdb_command']
    # pass this gdb command into gdb. get output. send to output
    #writer.step()
    curr_stack = gdb_command
    return render_template('vs.html', stack = curr_stack)

if __name__ == '__main__':
    if len(sys.argv) != 3:
      print "Usage: python vsbase.py <port number> <executable to debug>"
      exit(0)
    writer = gdb_writer.GDBWriter(sys.argv[2])
    writer.debug()
    web.internalerror = web.debugerror
    app = web.application(urls, globals())
    app.run()
