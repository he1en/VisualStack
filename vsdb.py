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

def getCurrStep():
  query_string = 'select StepNum from CurrStep'
  results = query(query_string)
  # alternatively: return results[0]['currenttime']
  return results[0].StepNum

def getContentsForStep(step):
  input_vars = {'stepNum': step}
  query_string1 = 'select * from StackFrame where StepNum = $stepNum'
  query_string2 = 'select * from StackWords where StepNum = $stepNum'
  result1 = query(query_string1, input_vars)
  if result1 is None or len(result1) == 0:
    return None
  result2 = query(query_string2, input_vars)
  ss = stackshot.StackShot()
  ss.line = result1[0].LineContents
  ss.regs['rsp'] = result1[0].RSP
  ss.regs['rbp'] = result1[0].RBP
  ss.regs['rax'] = result1[0].RAX
  ss.regs['rbx'] = result1[0].RBX
  ss.regs['rcx'] = result1[0].RCX
  ss.regs['rdx'] = result1[0].RDX
  ss.regs['rsi'] = result1[0].RSI
  ss.regs['rdi'] = result1[0].RDI
  ss.regs['r8'] = result1[0].R8
  ss.regs['r9'] = result1[0].R9
  ss.regs['r10'] = result1[0].R10
  ss.regs['r11'] = result1[0].R11
  ss.regs['r12'] = result1[0].R12
  ss.regs['r13'] = result1[0].R13
  ss.regs['r14'] = result1[0].R14
  ss.regs['r15'] = result1[0].R15
  for i in xrange(len(result2)):
    ss.words[result2[i].MemAddr] = result2[i].MemContents
  return ss

def setStep(curr_step):
  query_string = 'update CurrStep set StepNum = $nextStep'
  return querySuccess(query_string, {'nextStep': curr_step})

def addStep(step_num, contents):
  query_string = 'insert into StackFrame values($stepNum, $line'
  for r in stackshot.regs:
    query_string += ', $' + r
  query_string += ')'
  r = contents.regs
  input_vars = {reg: r[reg] for reg in stackshot.regs}
  input_vars['stepNum'] = step_num
  input_vars['line'] = contents.line
  db.query(query_string, input_vars)
  for addr, w in contents.words.iteritems():
    query_string = 'insert into StackWords values($stepNum, $addr, $mem)'
    input_vars = {'stepNum': step_num, 'addr': addr, 'mem': w}
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

