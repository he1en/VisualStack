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

# returns the number of the current step saved in the db
def getCurrStep():
  query_string = 'select StepNum from CurrStep'
  results = query(query_string)
  # alternatively: return results[0]['currenttime']
  return results[0].StepNum

# returns a hydrated version of the StackShot for the input step
def getContentsForStep(step):
  input_vars = {'stepNum': step}
  query_string1 = 'select * from StackFrame where StepNum = $stepNum'
  query_string2 = 'select * from StackWordsDelta where StepNum <= $stepNum group by MemAddr'
  query_string3 = 'select * from RegistersDelta where StepNum <= $stepNum group by RegName'
  query_string4 = 'select * from LocalVars where StepNum = $stepNum'
  query_string5 = 'select * from FnArguments where StepNum = $stepNum'


  result1 = query(query_string1, input_vars)
  if result1 is None or len(result1) == 0:
    return None
  result2 = query(query_string2, input_vars)
  result3 = query(query_string3, input_vars)
  result4 = query(query_string4, input_vars)
  result5 = query(query_string5, input_vars)

  ss = stackshot.StackShot()
  ss.hydrate_from_db(result1, result2, result3, result4, result5)
  return ss

# returns list starting 2 lines before and ending 2 lines after the line number passed in
def getLocalCode(line_num):
  if line_num is None:
    return None
  query_string = 'select LineContents from Code order by LineNum asc limit $start, $end'
  input_vars = {'start': str(max(line_num-3,0)), 'end': 5}
  #input_vars = {'start': str(max(line_num-3,0)), 'end': str(line_num+2)}
  q = query(query_string, input_vars)
  return [l.LineContents for l in query(query_string, input_vars)]

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
def setStep(curr_step):
  query_string = 'update CurrStep set StepNum = $nextStep'
  return querySuccess(query_string, {'nextStep': curr_step})

# never invoked by clients of this module
# adds input contents (StackShot) into the db for the input step_num
def addStep(step_num, contents):
  query_string = 'insert into StackFrame values($stepNum, $linenum, $line, $instruction, $highestArgAddr)'
  input_vars = {}
  input_vars['stepNum'] = step_num
  input_vars['linenum'] = contents.line_num
  input_vars['line'] = contents.line
  input_vars['instruction'] = contents.instruction
  input_vars['highestArgAddr'] = contents.highest_arg_addr
  db.query(query_string, input_vars)

  for rname, rcontents in contents.regs.iteritems():
    if rname in contents.changed_regs:
      query_string = 'insert into RegistersDelta values($stepNum, $regname, $mem)'
      input_vars = {'stepNum': step_num, 'regname': rname, 'mem': rcontents}
      db.query(query_string, input_vars)

  for addr, w in contents.words.iteritems():
    if addr in contents.changed_words:
      query_string = 'insert into StackWordsDelta values($stepNum, $addr, $mem)'
      input_vars = {'stepNum': step_num, 'addr': addr, 'mem': w}
      db.query(query_string, input_vars)
  for i, var in enumerate(contents.local_vars):
    query_string = 'insert into LocalVars values($stepNum, $varName, $varValue, $varAddr)'
    input_vars = {'stepNum': step_num, 'varName': var.name, 'varValue': var.value, 'varAddr': var.address}
    db.query(query_string, input_vars) 
  for i, arg in enumerate(contents.args):
    query_string = 'insert into FnArguments values($stepNum, $argName, $argValue, $argAddr)'
    input_vars = {'stepNum': step_num, 'argName': arg.name, 'argValue': arg.value, 'argAddr': arg.address}
    db.query(query_string, input_vars)

def runnerStep(step, contents):
  t = transaction()
  try:
    addStep(step, contents)
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

