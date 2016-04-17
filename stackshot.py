########################################
# Stack Shot Class
# 
########################################

class StackShot:

  def __init__(self):
    self.line = None  # String, last line number
    self.regs = {
      'rsp': None,
      'rbp': None,
      'rax': None,
      'rbx': None,
      'rcx': None,
      'rdx': None,
      'rsi': None,
      'rdi': None,
      'r8': None,
      'r9': None,
      'r10': None,
      'r11': None,
      'r12': None,
      'r13': None,
      'r14': None,
      'r15': None
    }
    self.words = {}

  def stringify(self):
    return self.line

  def ingest(self, data, command):
    try:
      {
        'step': self.ingest_step,
        'info registers': self.ingest_all_registers
      }[command](data)
    except KeyError:
      print "Cannot ingest data from gdb command %s." % command 
    
  def ingest_all_registers(self, data):
    if "The program has no registers now" in data:
      return
    for register_output in data.split("\n")[:16]: # only want first 16
      register, contents = register_output.split()[:2]
      self.regs[register] = contents


  def ingest_step(self, new_data):
    last_line = new_data.split('\n')[-2] # actual last line is (gdb)
    self.line = last_line

    # ingestion methods from raw gdb output

    # formatting of register / stack info as different lengths of memory,
    # ptrs, etc
        
