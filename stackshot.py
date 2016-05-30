########################################
# Stack Shot Class
 
########################################
import re

regs = ['rsp', 'rbp', 'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi',
        'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15']

REDZONE_SIZE = 16
WORD = 8

class StackShot(object):

  class Var:
    def __init__(self, name, value=None, address=None, active=False):
      self.name = name
      self.value = value
      self.address = address
      self.active = active

  def __init__(self):
    self._line = None
    self._line_num = None

    self._regs = {r: 'N/A' for r in regs}
    self._ordered_regs = regs
    self._changed_regs = set()

    self._words = {}
    self._ordered_addresses = []
    self._changed_words = set()

    self._saved_rbp = None
    self._args = []
    self._highest_arg_addr = None
    self._local_vars = []

    self._main_file = None
    self._src_files = []

    self._fn_names = []

    self._curr_instr_addr = None

  # invoke on a new stackshot instance
  def hydrate_from_db(self, stackframe, stackwords, registers, local_vars, \
                      arguments, step_direction):

    step_ = stackframe[0].StepNum
    stepi_ = stackframe[0].StepINum
    self._line = stackframe[0].LineContents
    self._line_num = stackframe[0].LineNum
    self._curr_instr_addr = stackframe[0].MemAddr
    self._highest_arg_addr = stackframe[0].HighestArgAddr

    for i in xrange(len(registers)):
      self._regs[registers[i].RegName] = registers[i].RegContents
      reg_s = registers[i].StepNum
      reg_si = registers[i].StepINum
      if step_direction is not None and  "i_" in step_direction: # stepi_forward or stepi_back
        if reg_s == step_ and reg_si == stepi_:
          self._changed_regs.add(registers[i].RegName)
      else:
        if (reg_s == step_-1 and reg_si != 0) or (reg_s == step_ and reg_si == stepi_):
          self._changed_regs.add(registers[i].RegName)

    for i in xrange(len(stackwords)):
      self._words[stackwords[i].MemAddr] = stackwords[i].MemContents
      sw_s = stackwords[i].StepNum
      sw_si = stackwords[i].StepINum
      if step_direction is not None and "i_" in step_direction:
        if sw_s == step_ and sw_si == stepi_:
          self._changed_words.add(stackwords[i].MemAddr)
      else:
        if (sw_s == step_-1 and sw_si != 0) or (sw_s == step_ and sw_si == stepi_):
          self._changed_words.add(stackwords[i].MemAddr)
    self._ordered_addresses = sorted(self._words.keys(),
                                    key = lambda addr: int(addr, 16),
                                    reverse=True)

    for i in xrange(len(local_vars)):
      self._local_vars.append(self.Var(local_vars[i].VarName,
                                      local_vars[i].VarValue,
                                      local_vars[i].VarAddr))
    for i in xrange(len(arguments)):
      self._args.append(self.Var(arguments[i].ArgName,
                                arguments[i].ArgValue,
                                arguments[i].ArgAddr))


  def stringify(self):
    # TODO: make this useful
    return self._line

  def clear_changed_words(self):
    self._changed_words = set()

  def clear_changed_regs(self):
    self._changed_regs = set()

  def clear_args(self):
    self._args = []

  def clear_locals(self):
    self._local_vars = []

  def frame_addresses(self):
    ''' Collects all stack addresses in current frame in descending order. '''
    addresses = []
    rbp_int = int(self._regs['rbp'], 16)
    rsp_int = int(self._regs['rsp'], 16)
    redzone_int = rsp_int - REDZONE_SIZE * WORD
    saved_rbp_int = int(self._saved_rbp, 16)

    # Collect memory above base pointer until saved base pointer
    if saved_rbp_int == 0:
      # If saved_rbp is 0x0, we are in main.
      num_above = 0
    else:
      num_above = (saved_rbp_int - rbp_int) / WORD

    for i in range(num_above):
      addresses.append(hex(saved_rbp_int - i * WORD))
      
    addresses.append(self._regs['rbp'])

    # Collect memory below base pointer until bottom of red zone
    num_below = (rbp_int - redzone_int) / WORD
    for i in range(1, num_below + 1):
      addresses.append(hex(rbp_int - i * WORD))

    return addresses

  def set_arg_address(self, arg_name, address):
    arg = filter(lambda a: a.name == arg_name, self._args)[0]
    arg.address = address
    if int(address, 16) > int(self._highest_arg_addr, 16):
      self._highest_arg_addr = address
    if int(address, 16) > int(self._regs['rbp'], 16) or \
       self._fn_names[-1] == 'main':
      # arg was passed on the stack, so its value is already correct
      arg.active = True

  def arg_names(self):
    return [arg.name for arg in self._args]

  def set_local_address(self, local_name, address):
    for local in self._local_vars:
      if local.name == local_name:
        local.address = address

  def local_names(self):
    return [local.name for local in self._local_vars]
      
  def first_time_in_function(self):
    return self._fn_names.count(self._fn_names[-1]) == 1

######### GETTERS AND SETTERS ############
  @property
  def line(self):
    return self._line

  @line.setter
  def line(self, value):
    self._line = value

  @property
  def line_num(self):
    return self._line_num

  @line_num.setter
  def line_num(self, value):
    self._line_num = value

  @property
  def regs(self):
    return self._regs

  @property
  def ordered_regs(self):
    return self._ordered_regs

  def set_register(self, register, value):
    self._regs[register] = value
    self._changed_regs.add(register)

  def is_changed_register(self, register):
    return register in self._changed_regs

  @property
  def words(self):
    return self._words

  @property
  def ordered_addresses(self):
    return self._ordered_addresses

  def set_word(self, address, word):
    self._words[address] = word
    self._changed_words.add(address)
    
    for var in self._args + self._local_vars:
      # TODO: address not on word boundary
      if var.address == address:
        var.active = True

  def is_changed_word(self, address):
    return address in self._changed_words

  @property
  def saved_rbp(self):
    return self._saved_rbp

  @saved_rbp.setter
  def saved_rbp(self, value):
    self._saved_rbp = value

  @property
  def args(self):
    return self._args

  @property
  def local_vars(self):
    return self._local_vars

  @property
  def highest_arg_addr(self):
    return self._highest_arg_addr

  @highest_arg_addr.setter
  def highest_arg_addr(self, value):
    self._highest_arg_addr = value

  @property
  def main_file(self):
    return self._main_file

  @main_file.setter
  def main_file(self, value):
    self._main_file = value

  @property
  def src_files(self):
    return self._src_files

  def add_src_file(self, filename):
    self._src_files.append(filename)

  @property
  def fn_names(self):
    return self._fn_names

  def current_fn_name(self):
    return self._fn_names[-1]

  def add_fn_name(self, fnname):
    self._fn_names.append(fnname)

  @property
  def curr_instr_addr(self):
    return self._curr_instr_addr

  @curr_instr_addr.setter
  def curr_instr_addr(self, value):
    self._curr_instr_addr = value

