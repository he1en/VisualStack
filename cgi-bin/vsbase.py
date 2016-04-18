#!/usr/bin/env python

import sys; sys.path.insert(0, 'lib') # this line is necessary for the rest
import os                             # of the imports to work!

import web
from jinja2 import Environment, FileSystemLoader

import vsdb
import gdb_runner


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
#writer = gdb_writer.GDBWriter()

class visual_stack:
  def GET(self):
    return render_template('vs.html', stack = None)
  def POST(self):
    post_params = web.input()
    gdb_command = post_params['gdb_command']
    # pass this gdb command into gdb. get output. send to output
    #print globals()['writer']
    #globals()['writer'].step()

    # for vsdb, get current step, get output, increment stepper
    curr_stack = 'Something failed :('
    t = vsdb.transaction()
    try:
      currStep = vsdb.getCurrStep()
      contents = vsdb.getContentsForStep(currStep)
      vsdb.setStep(currStep+1)
      if contents is not None:
        curr_stack = contents
    except Exception as e:
      t.rollback()
      print str(e)
    else:
      t.commit()
    return render_template('vs.html', stack = curr_stack)

if __name__ == '__main__':
    if len(sys.argv) != 3:
      print "Usage: python vsbase.py <port number> <executable to debug>"
      exit(0)
    web.internalerror = web.debugerror
    app = web.application(urls, globals())
    app.add_processor(web.loadhook(vsdb.enforceForeignKey))
    runner = gdb_runner.GDBRunner(sys.argv[2])
    runner.debug()
    runner.run_to_completion()
    app.run()
