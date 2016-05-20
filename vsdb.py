import web
import stackshot

db = web.database(dbn='sqlite', db='VisualStack.db')

######################BEGIN HELPER METHODS######################

# Enforce foreign key constraints
# WARNING: DO NOT REMOVE THIS!
def enforceForeignKey():
  db.query('PRAGMA foreign_keys = ON')

# initiates a transaction on the database
def transaction():
  return db.transaction()
# Sample usage (in auctionbase.py):
#
# t = sqlitedb.transaction()
# try:
#     sqlitedb.query('[FIRST QUERY STATEMENT]')
#     sqlitedb.query('[SECOND QUERY STATEMENT]')
# except Exception as e:
#     t.rollback()
#     print str(e)
# else:
#     t.commit()
#
# check out http://webpy.org/cookbook/transactions for examples

# returns the number of the current stepi saved in the db
def getCurrStep():
  query_string = 'select * from CurrStep'
  results = query(query_string)
  # alternatively: return results[0]['currenttime']
  return results[0].StepNum, results[0].StepINum

def getLastStepIInStep(step):
  query_string = 'select MAX(StepINum) as MaxStepI from StackFrame where StepNum = $stepNum'
  input_vars = {'stepNum': step}
  q = query(query_string, input_vars)
  return q[0].MaxStepI

def stepExists(step):
  query_string = 'select exists(select StepNum from StackFrame where StepNum = $stepNum limit 1) as StepExists'
  input_vars = {'stepNum': step}
  q = query(query_string, input_vars)
  return q[0].StepExists

# determines step and step_i based on transition
def getNextStep(curr_step, curr_step_i, transition):
  next_step = curr_step
  next_step_i = curr_step_i
  if transition == 'step_back':
    if next_step_i == 0:
      if stepExists(next_step - 1):
        next_step -= 1
    next_step_i = 0
  elif transition == 'stepi_back':
    if next_step_i == 0:
      if stepExists(next_step - 1):
        next_step -= 1
        next_step_i = getLastStepIInStep(next_step)
    else:
      next_step_i -= 1
  elif transition == 'step_forward':
    if stepExists(next_step):
      next_step += 1
      next_step_i = 0
    else:
      next_step_i = getLastStepIInStep(next_step)
  elif transition == 'stepi_forward':
    curr_last_step_i = getLastStepIInStep(next_step)
    if next_step_i == curr_last_step_i:
      if stepExists(next_step + 1):
        next_step += 1
        next_step_i = 0
    else:
      next_step_i += 1
  return next_step, next_step_i

# determines step and step_i based on transition
"""def getNextStep(curr_step, curr_step_i, transition):
  next_step = curr_step
  next_step_i = curr_step_i
  if transition == 'step_back':
    next_step -= 1
    if next_step >= 0:
      next_step_i = getLastStepIInStep(next_step)
    else:
      next_step = 0
      next_step_i = 0
  elif transition == 'stepi_back':
    next_step_i -= 1
    if next_step_i < 0:
      if next_step == 0:
        next_step_i = 0
      else:
        next_step -= 1
        next_step_i = getLastStepIInStep(next_step)
  elif transition == 'step_forward':
    curr_last_step_i = getLastStepIInStep(next_step)
    if next_step_i == curr_last_step_i:
      if stepExists(next_step + 1):
        next_step += 1
        next_step_i = getLastStepIInStep(next_step)
    else:
      next_step_i = curr_last_step_i
  elif transition == 'stepi_forward':
    curr_last_step_i = getLastStepIInStep(next_step)
    if next_step_i == curr_last_step_i:
      if stepExists(next_step + 1):
        next_step += 1
        next_step_i = 0
    else:
      next_step_i += 1
  return next_step, next_step_i"""

# returns a hydrated version of the StackShot for the input step
def getContentsForStep(step, step_i, step_direction = None):
  input_vars = {'stepNum': step, 'stepINum': step_i}
  query_string1 = 'select * from StackFrame where StepNum = $stepNum and StepINum = $stepINum'
  query_string2 = 'select * from StackWordsDelta where StepNum < $stepNum or (StepNum = $stepNum and StepINum <= $stepINum) group by MemAddr'
  query_string3 = 'select * from RegistersDelta where StepNum < $stepNum or (StepNum = $stepNum and StepINum <= $stepINum) group by RegName'
  query_string4 = 'select * from LocalVars where StepNum = $stepNum and StepINum = $stepINum'
  query_string5 = 'select * from FnArguments where StepNum = $stepNum and StepINum = $stepINum'
  query_string6 = 'select * from Assembly where StepNum = $stepNum order by StepINum asc'

  result1 = query(query_string1, input_vars)
  if result1 is None or len(result1) == 0:
    return None
  result2 = query(query_string2, input_vars)
  result3 = query(query_string3, input_vars)
  result4 = query(query_string4, input_vars)
  result5 = query(query_string5, input_vars)
  result6 = query(query_string6, input_vars)

  ss = stackshot.StackShot()
  ss.hydrate_from_db(result1, result2, result3, result4, result5, result6, step_direction)
  return ss

# returns list starting 2 lines before and ending 2 lines after the line number passed in
def getLocalCode(line_num, step_num, step_i_num):
  if line_num is None or step_num is None or step_i_num is None:
    return None
  query_string = 'select LineContents from Code order by LineNum asc limit $start, $end'
  input_vars = {'start': str(max(line_num-3,0)), 'end': 5} 
  code_contents = query(query_string, input_vars)
  return [l.LineContents for l in code_contents] 

# writes the entire code file to the db
def writeCode(code_lines):
  query_list = ['insert into Code values ']
  input_vars = {}
  for i in xrange(len(code_lines)):
    query_list.append('($linenum' + str(i+1) + ',$line' + str(i+1) + ')')
    query_list.append(',')
    input_vars['linenum'+str(i+1)] = i
    input_vars['line'+str(i+1)] = code_lines[i]
  query_list[-1] = ';'
  #print ''.join(query_list)
  return querySuccess(''.join(query_list), input_vars)

# sets the curr step in db to be the input
def setStep(curr_step, curr_step_i):
  query_string = 'update CurrStep set StepNum = $nextStep, StepINum = $nextStepI'
  return querySuccess(query_string, {'nextStep': curr_step, 'nextStepI': curr_step_i})

# never invoked by clients of this module
# adds input contents (StackShot) into the db for the input step_num
def addStep(step_num, step_i_num, contents):
  query_string = 'insert into StackFrame values($stepNum, $stepINum, $linenum, $line, $highestArgAddr)'
  input_vars = {}
  input_vars['stepNum'] = step_num
  input_vars['stepINum'] = step_i_num
  input_vars['linenum'] = contents.line_num
  input_vars['line'] = contents.line
  input_vars['highestArgAddr'] = contents.highest_arg_addr
  db.query(query_string, input_vars)

  for rname, rcontents in contents.regs.iteritems():
    if rname in contents.changed_regs:
      query_string = 'insert into RegistersDelta values($stepNum, $stepINum, $regname, $mem)'
      input_vars = {'stepNum': step_num, 'stepINum': step_i_num, 'regname': rname, 'mem': rcontents}
      db.query(query_string, input_vars)

  for addr, w in contents.words.iteritems():
    if addr in contents.changed_words:
      query_string = 'insert into StackWordsDelta values($stepNum, $stepINum, $addr, $mem)'
      input_vars = {'stepNum': step_num, 'stepINum': step_i_num, 'addr': addr, 'mem': w}
      db.query(query_string, input_vars)
  for i, var in enumerate(contents.local_vars):
    if not var.active:
      continue
    query_string = 'insert into LocalVars values($stepNum, $stepINum, $varName, $varValue, $varAddr)'
    input_vars = {'stepNum': step_num, 'stepINum': step_i_num, 'varName': var.name, 'varValue': var.value, 'varAddr': var.address}
    db.query(query_string, input_vars) 
  for i, arg in enumerate(contents.args):
    if not arg.active:
      continue
    query_string = 'insert into FnArguments values($stepNum, $stepINum, $argName, $argValue, $argAddr)'
    input_vars = {'stepNum': step_num, 'stepINum': step_i_num, 'argName': arg.name, 'argValue': arg.value, 'argAddr': arg.address}
    db.query(query_string, input_vars)

# never invoked by clients of this module
# adds corresponding assembly for line in currstep to db
def addAssembly(step_num, step_i_num, assembly_line):
  query_string = 'insert into Assembly values($stepNum, $stepINum, $instrContents)'
  input_vars = {'stepNum': step_num, 'stepINum': step_i_num, 'instrContents': assembly_line}
  querySuccess(query_string, input_vars)

def runnerStep(step, step_i, contents):
  t = transaction()
  try:
    addStep(step, step_i, contents)
  except Exception as e:
    t.rollback()
    print str(e)
  else:
    t.commit()
  addAssembly(step, step_i, contents.instruction_lines[contents.curr_instruction_index])

# wrapper method around web.py's db.query method
# check out http://webpy.org/cookbook/query for more info
def query(query_string, vars = {}):
    return list(db.query(query_string, vars))

def querySuccess(query_string, vars = {}):
    try:
      db.query(query_string, vars)
    except Exception as e:
      print str(e)
      return False
    else:
      return True

