import web

db = web.database(dbn='sqlite',
        db='VisualStack.db'
    )

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
  query_string = 'select LineContents from StackFrame where StepNum = $stepNum'
  result = query(query_string, {'stepNum': step})
  # TODO: get entire stackshot including words content from StackWords table
  if result is None or len(result) == 0:
    return None
  return result[0]

def step(curr_step):
  query_string = 'update CurrStep set StepNum = $nextStep'
  return querySuccess(query_string, {'nextStep': curr_step + 1})

def addStep(step_num, contents):
  query_string = 'insert into StackFrame values($stepNum, $line, $rsp, $rbp, $rax, $rbx, $rcx, $rdx, $rsi, $rdi, $r8, $r9, $r10, $r11, $r12, $r13, $r14, $r15)'
  r = contents.regs
  input_vars = {'stepNum': step_num, 'line': contents.line, 'rsp': r['rsp'],
                'rbp': r['rbp'], 'rax': r['rax'], 'rbx': r['rbx'],
                'rcx': r['rcx'], 'rdx': r['rdx'], 'rsi': r['rsi'],
                'rdi': r['rdi'], 'r8': r['r8'], 'r9': r['r9'], 'r10': r['r10'],
                'r11': r['r11'], 'r12': r['r12'], 'r13': r['r13'],
                'r14': r['r14'], 'r15': r['r15']}
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
    step(currStep)
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

