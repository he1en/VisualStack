#!/usr/bin/env python

import sys; sys.path.insert(0, 'lib') # this line is necessary for the rest
import os                             # of the imports to work!

import web
from jinja2 import Environment, FileSystemLoader

import vsdb
import gdb_runner

def hex_to_int(hexstring):
  return int(hexstring, 16)

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

    # in both of these instances, the 'hex' representation is a string
    jinja_env.filters['hex_to_int'] = hex_to_int
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
      currStepI, currStep = vsdb.getCurrStep()
      contents = vsdb.getContentsForStepI(currStepI)
      if contents is not None:
        curr_stack = contents
        local_code, local_assembly = vsdb.getLocalCode(contents.line_num, contents.curr_instruction_index)
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

    # for vsdb, get current step, increment stepper in correct direction, get output
    curr_stack = None
    local_code = None
    t = vsdb.transaction()
    try:
      if step_direction is None:
        vsdb.setStep(0, 0)
        contents = vsdb.getContentsForStepI(0)
        print contents.new_line
      else:
        currStepI, currStep = vsdb.getCurrStep()
        contents = vsdb.getContentsForStepI(currStepI + step_direction)
        print contents.new_line
        if contents.new_line:
          currStep += 1
        vsdb.setStep(currStepI + step_direction, currStep)
      if contents is not None:
        curr_stack = contents
        local_code, local_assembly = vsdb.getLocalCode(contents.line_num, contents.curr_instruction_index)
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
