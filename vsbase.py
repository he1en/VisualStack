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
    # for vsdb, get current step
    curr_stack = None
    local_code = None
    t = vsdb.transaction()
    try:
      currStep = vsdb.getCurrStep()
      contents = vsdb.getContentsForStep(currStep)
      if contents is not None:
        curr_stack = contents
        local_code = vsdb.getLocalCode(contents.line_num)
    except Exception as e:
      t.rollback()
      print str(e)
    else:
      t.commit()
    return render_template('vs.html', stack = curr_stack, localcode = local_code)
  def POST(self):
    post_params = web.input()
    step_direction = None
    if 'step_forward' in post_params:
      step_direction = 1
    elif 'step_back' in post_params:
      step_direction = -1
    print step_direction

    # for vsdb, get current step, increment stepper in correct direction, get output
    curr_stack = None
    local_code = None
    t = vsdb.transaction()
    try:
      currStep = vsdb.getCurrStep()
      contents = vsdb.getContentsForStep(currStep + step_direction)
      vsdb.setStep(currStep + step_direction)
      if contents is not None:
        curr_stack = contents
        local_code = vsdb.getLocalCode(contents.line_num)
    except Exception as e:
      t.rollback()
      print str(e)
    else:
      t.commit()
    return render_template('vs.html', stack = curr_stack, localcode = local_code)

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
