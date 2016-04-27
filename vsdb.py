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
  query_string2 = 'select * from StackWords where StepNum = $stepNum'
  query_string3 = 'select * from Changes where StepNum = $stepNum'
  result1 = query(query_string1, input_vars)
  if result1 is None or len(result1) == 0:
    return None
  result2 = query(query_string2, input_vars)
  result3 = query(query_string3, input_vars)
  ss = stackshot.StackShot()
  ss.hydrate_from_db(result1, result2, result3)
  return ss

# returns list starting 2 lines before and ending 2 lines after the line number passed in
def getLocalCode(line_num):
  if line_num is None:
    return None
  #query_string = 'select LineContents from Code order by LineNum asc limit 0, 5'
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
    # query_list.append('(' + str(i+1) + ',' + code_lines[i] + ')')
    query_list.append(',')
    input_vars['linenum'+str(i+1)] = i
    input_vars['line'+str(i+1)] = code_lines[i]
  query_list[-1] = ';'
  print ''.join(query_list)
  return querySuccess(''.join(query_list), input_vars)

# sets the curr step in db to be the input
def setStep(curr_step):
  query_string = 'update CurrStep set StepNum = $nextStep'
  return querySuccess(query_string, {'nextStep': curr_step})

# never invoked by clients of this module
# adds input contents (StackShot) into the db for the input step_num
def addStep(step_num, contents):
  query_string = 'insert into StackFrame values($stepNum, $linenum, $line'
  for r in stackshot.regs:
    query_string += ', $' + r
  query_string += ')'
  r = contents.regs
  input_vars = {reg: r[reg] for reg in stackshot.regs}
  input_vars['stepNum'] = step_num
  input_vars['linenum'] = contents.line_num
  input_vars['line'] = contents.line
  db.query(query_string, input_vars)
  for addr, w in contents.words.iteritems():
    query_string = 'insert into StackWords values($stepNum, $addr, $mem)'
    input_vars = {'stepNum': step_num, 'addr': addr, 'mem': w}
    db.query(query_string, input_vars)
  for change in contents.changed_regs:
    query_string = 'insert into Changes values($stepNum, $changeType, $changeAddr)'
    input_vars = {'stepNum': step_num, 'changeType': 'REGISTER', 'changeAddr': change}
    db.query(query_string, input_vars)
  for change in contents.changed_words:
    query_string = 'insert into Changes values($stepNum, $changeType, $changeAddr)'
    input_vars = {'stepNum': step_num, 'changeType': 'WORD', 'changeAddr': change}
    db.query(query_string, input_vars)

def runnerStep(contents):
  t = transaction()
  try:
    currStep = getCurrStep()
    addStep(currStep, contents)
    setStep(currStep + 1)
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

