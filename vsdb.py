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
  return (int(q[0].StepExists) == 1)

# determines step and step_i based on transition
def getNextStep(curr_step, curr_step_i, transition):
  next_step = curr_step
  next_step_i = curr_step_i
  if transition == 'step_back':
    if next_step_i == 0 and stepExists(next_step - 1):
      next_step -= 1
    next_step_i = 0
  elif transition == 'stepi_back':
    if next_step_i == 0 and stepExists(next_step - 1):
      next_step -= 1
      next_step_i = getLastStepIInStep(next_step)
    else:
      next_step_i -= 1
  elif transition == 'step_forward':
    if stepExists(next_step + 1):
      next_step += 1
      next_step_i = 0
    else:
      next_step_i = getLastStepIInStep(next_step)
  elif transition == 'stepi_forward':
    if next_step_i == getLastStepIInStep(next_step):
      if stepExists(next_step + 1):
        next_step += 1
        next_step_i = 0
    else:
      next_step_i += 1
  return next_step, next_step_i

def getLineNum(curr_step, curr_step_i):
  query_string = 'select LineNum from StackFrame where StepNum = $step_num and StepINum = $stepi_num'
  input_vars = {'step_num': curr_step, 'stepi_num': curr_step_i}
  return query(query_string, input_vars)[0].LineNum 

def getMemAddressesForAssembly(curr_step, curr_step_i, transition):
  q = []
  if transition == 'stepi_forward':
    query_string = 'select MemAddr from StackFrame where StepNum = $step_num and StepINum = $stepi_num'
    input_vars = {'step_num': curr_step, 'stepi_num': curr_step_i}
    q = query(query_string, input_vars)
  elif transition == 'step_forward':
    return None
  elif transition == 'stepi_back':
    hop1, hop1_i = getNextStep(curr_step, curr_step_i, transition)
    hop2, hop2_i = getNextStep(hop1, hop1_i, transition)
    query_string = 'select MemAddr from StackFrame where StepNum = $step_num and StepINum = $stepi_num'
    input_vars = {'step_num': hop2, 'stepi_num': hop2_i}
    q = query(query_string, input_vars)
  elif transition == 'step_back':
    return None
  return set([int(addr.MemAddr,16) for addr in q])

# returns a hydrated version of the StackShot for the input step
def getContentsForStep(step, step_i, step_direction = None):
  input_vars = {'stepNum': step, 'stepINum': step_i}
  query_string1 = 'select * from StackFrame where StepNum = $stepNum and StepINum = $stepINum'
  query_string2 = 'select * from StackWordsDelta where StepNum < $stepNum or (StepNum = $stepNum and StepINum <= $stepINum) group by MemAddr'
  query_string3 = 'select * from RegistersDelta where StepNum < $stepNum or (StepNum = $stepNum and StepINum <= $stepINum) group by RegName'
  query_string4 = 'select * from LocalVars where StepNum = $stepNum and StepINum = $stepINum'
  query_string5 = 'select * from FnArguments where StepNum = $stepNum and StepINum = $stepINum'

  result1 = query(query_string1, input_vars)
  if result1 is None or len(result1) == 0:
    return None
  result2 = query(query_string2, input_vars)
  result3 = query(query_string3, input_vars)
  result4 = query(query_string4, input_vars)
  result5 = query(query_string5, input_vars)

  ss = stackshot.StackShot()
  ss.hydrate_from_db(result1, result2, result3, result4, result5, step_direction)
  return ss

# returns local assembly instructions
def getLocalAssembly(line_num, mem_addr):
    query_string = 'select * from Assembly where LineNum = $lineNum order by MemAddr asc'
    input_vars = {'lineNum': line_num}
    code_contents =  query(query_string, input_vars)
    return [(l.MemAddr, l.InstrContents) for l in code_contents]

# returns list starting 2 lines before and ending 2 lines after the line number passed in
def getLocalCode(line_num):
  if line_num is None:
    return None
  query_string = 'select LineContents from Code order by LineNum asc limit $start, $end'
  input_vars = {'start': str(max(line_num-5,0)), 'end': 9} 
  code_contents = query(query_string, input_vars)
  return [l.LineContents for l in code_contents] 

# writes the entire code file to the db
def writeCode(code_lines):
  query_list = ['insert into Code values ']
  input_vars = {}
  for i in xrange(len(code_lines)):
    query_list.append('($linenum' + str(i+1) + ',$line' + str(i+1) + ')')
    query_list.append(',')
    input_vars['linenum'+str(i+1)] = i+1
    input_vars['line'+str(i+1)] = code_lines[i]
  query_list[-1] = ';'
  return querySuccess(''.join(query_list), input_vars)

# sets the curr step in db to be the input
def setStep(curr_step, curr_step_i):
  query_string = 'update CurrStep set StepNum = $nextStep, StepINum = $nextStepI'
  return querySuccess(query_string, {'nextStep': curr_step, 'nextStepI': curr_step_i})

# never invoked by clients of this module
# adds input contents (StackShot) into the db for the input step_num
def addStep(step_num, step_i_num, contents):
  query_string = 'insert into StackFrame values($stepNum, $stepINum, $linenum, $line, $memAddr, $frameTop, $parentFrameTop, $frameBottom)'

  input_vars = {}
  input_vars['stepNum'] = step_num
  input_vars['stepINum'] = step_i_num
  input_vars['linenum'] = contents.line_num
  input_vars['line'] = contents.line
  input_vars['memAddr'] = contents.curr_instr_addr
  input_vars['frameTop'] = contents.frame_top
  input_vars['parentFrameTop'] = contents.parent_frame_top
  input_vars['frameBottom'] = contents.frame_bottom
  db.query(query_string, input_vars)

  for rname, rcontents in contents.regs.iteritems():
    if contents.is_changed_register(rname):
      query_string = 'insert into RegistersDelta values($stepNum, $stepINum, $regname, $mem)'
      input_vars = {'stepNum': step_num, 'stepINum': step_i_num, 'regname': rname, 'mem': rcontents}
      db.query(query_string, input_vars)

  for addr, w in contents.words.iteritems():
    if contents.is_changed_word(addr):
      query_string = 'insert into StackWordsDelta values($stepNum, $stepINum, $addr, $mem)'
      input_vars = {'stepNum': step_num, 'stepINum': step_i_num, 'addr': addr, 'mem': w}
      db.query(query_string, input_vars)

  for i, var in enumerate(contents.local_vars):
    if not var.active:
      continue
    query_string = 'insert into LocalVars values($stepNum, $stepINum, $varName, $varValue, $varAddr, $varReg)'
    input_vars = {'stepNum': step_num, 'stepINum': step_i_num,
                  'varName': var.name, 'varValue': var.value,
                  'varAddr': var.address, 'varReg': var.register}
    db.query(query_string, input_vars) 

  for i, arg in enumerate(contents.args):
    if not arg.active:
      continue
    query_string = 'insert into FnArguments values($stepNum, $stepINum, $argName, $argValue, $argAddr, $argReg)'
    input_vars = {'stepNum': step_num, 'stepINum': step_i_num,
                  'argName': arg.name, 'argValue': arg.value,
                  'argAddr': arg.address, 'argReg': arg.register}
    db.query(query_string, input_vars)

# adds corresponding assembly for line in currstep to db
def writeAssembly(assembly_info_obj):
  t = transaction()
  try:
    for line_num in assembly_info_obj.keys():
      instructions = assembly_info_obj[line_num]
      for instr_addr in instructions.keys():
        query_string = \
          'insert into Assembly values($lineNum, $memAddr, $instrContents)'
        input_vars = {
          'lineNum': line_num,
          'memAddr': instr_addr,
          'instrContents': instructions[instr_addr]
        }
        db.query(query_string, input_vars)
  except Exception as e:
    t.rollback()
    print str(e)
  else:
    t.commit()

def runnerStep(step, step_i, contents):
  t = transaction()
  try:
    addStep(step, step_i, contents)
  except Exception as e:
    t.rollback()
    print str(e)
  else:
    t.commit()

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

