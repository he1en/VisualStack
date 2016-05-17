########################################
# Stack Shot Class
 
########################################
import re

regs = ['rsp', 'rbp', 'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi',
        'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15']

REDZONE_SIZE = 16
WORD = 8

class StackShot:

  class Var:
    def __init__(self, name, value=None, address=None, active=False):
      self.name = name
      self.value = value
      self.address = address
      self.active = active

  def __init__(self):
    self.line = None  # String, last line number
    self.line_num = None
    self.instruction = None
    self.regs = {r: 'N/A' for r in regs}
    self.ordered_regs = regs
    self.changed_regs = set()

    self.words = {}
    self.ordered_addresses = []
    self.changed_words = set()

    self.saved_rbp = None
    self.args = []
    self.highest_arg_addr = None
    self.local_vars = []

    self.main_file = None
    self.src_files = []

    self.new_line = True
    self.new_function = True
    self.new_frame_loaded = True
    self.fn_names = []

    self.instruction_lines = []
    self.curr_instruction_index = 0
    self.line_instruction_limits = None

  # invoke on a new stackshot instance
  def hydrate_from_db(self, stackframe, stackwords, registers, local_vars, arguments, assembly):
    self.line = stackframe[0].LineContents
    self.line_num = stackframe[0].LineNum
    self.curr_instruction_index = stackframe[0].InstrIndex
    self.highest_arg_addr = stackframe[0].HighestArgAddr

    for i in xrange(len(registers)):
      self.regs[registers[i].RegName] = registers[i].RegContents
      if registers[i].StepNum == stackframe[0].StepNum:
        self.changed_regs.add(registers[i].RegName)

    for i in xrange(len(stackwords)):
      self.words[stackwords[i].MemAddr] = stackwords[i].MemContents
      if stackwords[i].StepNum == stackframe[0].StepNum:
        self.changed_words.add(stackwords[i].MemAddr)
    self.ordered_addresses = sorted(self.words.keys(),
                                    key = lambda addr: int(addr, 16),
                                    reverse=True)

    for i in xrange(len(local_vars)):
      self.local_vars.append(self.Var(local_vars[i].VarName,
                                      local_vars[i].VarValue,
                                      local_vars[i].VarAddr))
    for i in xrange(len(arguments)):
      self.args.append(self.Var(arguments[i].ArgName,
                                arguments[i].ArgValue,
                                arguments[i].ArgAddr))

    for i in xrange(len(assembly)):
      self.instruction_lines.append(assembly[i].InstrContents)

  def stringify(self):
    # TODO: make this useful
    return self.line

  def clear_changed_words(self):
    self.changed_words = set()

  def clear_args(self):
    self.args = []

  def clear_locals(self):
    self.local_vars = []

  def frame_addresses(self):
    ''' Collects all stack addresses in current frame in descending order. '''
    addresses = []
    rbp_int = int(self.regs['rbp'], 16)
    rsp_int = int(self.regs['rsp'], 16)
    redzone_int = rsp_int - REDZONE_SIZE * WORD
    saved_rbp_int = int(self.saved_rbp, 16)

    # Collect memory above base pointer until saved base pointer
    if saved_rbp_int == 0:
      # If saved_rbp is 0x0, we are in main.
      num_above = 0
    else:
      num_above = (saved_rbp_int - rbp_int) / WORD

    for i in range(num_above):
      addresses.append(hex(saved_rbp_int - i * WORD))
      
    addresses.append(self.regs['rbp'])

    # Collect memory below base pointer until bottom of red zone
    num_below = (rbp_int - redzone_int) / WORD
    for i in range(1, num_below + 1):
      addresses.append(hex(rbp_int - i * WORD))

    return addresses

  def set_arg_address(self, arg_name, address):
    arg = filter(lambda a: a.name == arg_name, self.args)[0]
    arg.address = address
    if int(address, 16) > int(self.highest_arg_addr, 16):
      self.highest_arg_addr = address
    if int(address, 16) > int(self.regs['rbp'], 16) or \
       self.fn_names[-1] == 'main':
      # arg was passed on the stack, so its value is already correct
      arg.active = True

  def arg_names(self):
    return [arg.name for arg in self.args]

  def set_local_address(self, local_name, address):
    for local in self.local_vars:
      if local.name == local_name:
        local.address = address

  def local_names(self):
    return [local.name for local in self.local_vars]
      
  def first_time_in_function(self):
    return self.fn_names.count(self.fn_names[-1]) == 1
