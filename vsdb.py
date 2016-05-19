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
  return results[0].StepINum, results[0].StepNum

# returns a hydrated version of the StackShot for the input step
def getContentsForStepI(step_i):
  input_vars = {'stepINum': step_i}
  query_string1 = 'select * from StackFrame where StepINum = $stepINum'
  query_string2 = 'select * from StackWordsDelta where StepINum <= $stepINum group by MemAddr'
  query_string3 = 'select * from RegistersDelta where StepINum <= $stepINum group by RegName'
  query_string4 = 'select * from LocalVars where StepINum = $stepINum'
  query_string5 = 'select * from FnArguments where StepINum = $stepINum'

  result1 = query(query_string1, input_vars)
  if result1 is None or len(result1) == 0:
    return None
  result2 = query(query_string2, input_vars)
  result3 = query(query_string3, input_vars)
  result4 = query(query_string4, input_vars)
  result5 = query(query_string5, input_vars)

  # must happen once know result1 is not None
  query_string6 = 'select * from Assembly where CLineNum = $cLineNum order by InstrLineNum asc'
  input_vars = {'cLineNum': result1[0].LineNum}
  result6 = query(query_string6, input_vars)

  ss = stackshot.StackShot()
  ss.hydrate_from_db(result1, result2, result3, result4, result5, result6)
  return ss

# returns list starting 2 lines before and ending 2 lines after the line number passed in
# and list starting 2 lines before and ending 2 lines after the current assembly instruction
def getLocalCode(line_num, instr_index):
  if line_num is None or instr_index is None:
    return None
  query_string = 'select LineContents from Code order by LineNum asc limit $start, $end'
  input_vars = {'start': str(max(line_num-3,0)), 'end': 5} 
  code_contents = query(query_string, input_vars)
  query_string = 'select InstrContents from Assembly where CLineNum = $lineNum order by InstrLineNum asc limit $start, $end'
  input_vars = {'lineNum': line_num, 'start': str(max(instr_index-3, 0)), 'end': 5}
  assembly_contents = query(query_string, input_vars)
  return [l.LineContents for l in code_contents] , [a.InstrContents for a in assembly_contents]

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
def setStep(curr_step_i, curr_step):
  query_string = 'update CurrStep set StepINum = $nextStepI, StepNum = $nextStep'
  return querySuccess(query_string, {'nextStepI': curr_step_i, 'nextStep': curr_step})

# never invoked by clients of this module
# adds input contents (StackShot) into the db for the input step_num
def addStepI(step_i_num, step_num, contents):
  query_string = 'insert into StackFrame values($stepINum, $stepNum, $linenum, $line, $instructionIndex, $highestArgAddr)'
  input_vars = {}
  input_vars['stepINum'] = step_i_num
  input_vars['stepNum'] = step_num
  input_vars['linenum'] = contents.line_num
  input_vars['line'] = contents.line
  input_vars['instructionIndex'] = contents.curr_instruction_index
  input_vars['highestArgAddr'] = contents.highest_arg_addr
  db.query(query_string, input_vars)

  for rname, rcontents in contents.regs.iteritems():
    if rname in contents.changed_regs:
      query_string = 'insert into RegistersDelta values($stepINum, $regname, $mem)'
      input_vars = {'stepINum': step_i_num, 'regname': rname, 'mem': rcontents}
      db.query(query_string, input_vars)

  for addr, w in contents.words.iteritems():
    if addr in contents.changed_words:
      query_string = 'insert into StackWordsDelta values($stepINum, $addr, $mem)'
      input_vars = {'stepINum': step_i_num, 'addr': addr, 'mem': w}
      db.query(query_string, input_vars)
  for i, var in enumerate(contents.local_vars):
    if not var.active:
      continue
    query_string = 'insert into LocalVars values($stepINum, $varName, $varValue, $varAddr)'
    input_vars = {'stepINum': step_i_num, 'varName': var.name, 'varValue': var.value, 'varAddr': var.address}
    db.query(query_string, input_vars) 
  for i, arg in enumerate(contents.args):
    if not arg.active:
      continue
    query_string = 'insert into FnArguments values($stepINum, $argName, $argValue, $argAddr)'
    input_vars = {'stepINum': step_i_num, 'argName': arg.name, 'argValue': arg.value, 'argAddr': arg.address}
    db.query(query_string, input_vars)

  if contents.new_line:
    for index in xrange(len(contents.instruction_lines)):
      query_string = 'insert into Assembly values($cLineNum, $instrLineNum, $instrContents)'
      input_vars = {'cLineNum': contents.line_num, 'instrLineNum': index, 'instrContents': contents.instruction_lines[index]}
      db.query(query_string, input_vars)

def runnerStep(step_i, step, contents):
  t = transaction()
  try:
    addStepI(step_i, step, contents)
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

