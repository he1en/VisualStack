#######################################
# Stack Shot Class
 
########################################
import re

regs = ['rsp', 'rbp', 'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi',
        'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15',
        'rip', 'eflags']

REDZONE_SIZE = 16
WORD = 8

class StackShot(object):

  class Var:
    def __init__(self, name, value=None, address=None, register=None,
                 active=False):
      self.name = name
      self.value = value
      self.address = address
      self.active = active
      self.register = register

  def __init__(self):
    self._line = None
    self._line_num = None

    self._regs = {r: 'N/A' for r in regs}
    self._ordered_regs = regs
    self._changed_regs = set()

    self._words = {}
    self._ordered_addresses = []
    self._changed_words = set()

    self._args = []
    self._frame_top = None
    self._parent_frame_top = None
    self._frame_bottom = None
    self._rip_addr = None

    self._local_vars = []

    self._main_file = None
    self._src_files = []

    self._curr_instr_addr = None

  # invoke on a new stackshot instance
  def hydrate_from_db(self, stackframe, stackwords, registers, local_vars, \
                      arguments, step_direction):

    step_ = stackframe[0].StepNum
    stepi_ = stackframe[0].StepINum
    self._line = stackframe[0].LineContents
    self._line_num = stackframe[0].LineNum
    self._curr_instr_addr = stackframe[0].MemAddr
    self._frame_top = stackframe[0].FrameTop
    self._parent_frame_top = stackframe[0].ParentFrameTop
    self._frame_bottom = stackframe[0].FrameBottom

    for i in xrange(len(registers)):
      self._regs[registers[i].RegName] = registers[i].RegContents
      reg_s = registers[i].StepNum
      reg_si = registers[i].StepINum
      if step_direction is not None and  "i_" in step_direction:
        # stepi_forward or stepi_back
        if reg_s == step_ and reg_si == stepi_:
          self._changed_regs.add(registers[i].RegName)
      else:
        if (reg_s == step_-1 and reg_si != 0) or \
           (reg_s == step_ and reg_si == stepi_):
          self._changed_regs.add(registers[i].RegName)

    for i in xrange(len(stackwords)):
      self._words[stackwords[i].MemAddr] = stackwords[i].MemContents
      sw_s = stackwords[i].StepNum
      sw_si = stackwords[i].StepINum
      if step_direction is not None and "i_" in step_direction:
        if sw_s == step_ and sw_si == stepi_:
          self._changed_words.add(stackwords[i].MemAddr)
      else:
        if (sw_s == step_-1 and sw_si != 0) or \
           (sw_s == step_ and sw_si == stepi_):
          self._changed_words.add(stackwords[i].MemAddr)
    self._ordered_addresses = sorted(self._words.keys(),
                                    key = lambda addr: int(addr, 16),
                                    reverse=True)

    for i in xrange(len(local_vars)):
      self._local_vars.append(self.Var(local_vars[i].VarName,
                                       local_vars[i].VarValue,
                                       local_vars[i].VarAddr,
                                       local_vars[i].VarReg))
    for i in xrange(len(arguments)):
      self._args.append(self.Var(arguments[i].ArgName,
                                 arguments[i].ArgValue,
                                 arguments[i].ArgAddr,
                                 arguments[i].ArgReg))


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
    top_int = int(self._parent_frame_top, 16)
    rsp_int = int(self._regs['rsp'], 16)
    redzone_int = rsp_int - REDZONE_SIZE * WORD

    num_words = (top_int - redzone_int) / WORD

    for i in range(num_words):
      addresses.append(hex(top_int - i * WORD))
    
    return addresses

  def set_var_opimized_out(self, var_name):
    var = None
    
    if var_name in self.arg_names():
      var_match = filter(lambda a: a.name == var_name, self._args)
      if var_match:
        var = var_match[0]
    elif var_name in self.local_names():
      var_match = filter(lambda l: l.name == var_name, self._local_vars)
      if var_match:
        var = var_match[0]
    
    var.value = '<optimized out>' 
    var.active = False

  def set_arg_location(self, saved_rip_addr, arg_name,
                       address=None, register=None, in_main=False):
    arg = filter(lambda a: a.name == arg_name, self._args)[0]

    if address:
      arg.address = address
      addr_int = int(address, 16)
      if addr_int > int(saved_rip_addr, 16) or in_main:
        # arg was passed on the stack, so its value is already correct
        arg.active = True
        if addr_int > int(self._frame_top, 16):
          self._frame_top = hex(addr_int + 8)

    if register:
      arg.register = register
      arg.active = True

  def arg_names(self):
    return [arg.name for arg in self._args]

  def set_local_location(self, local_name, address=None, register=None):
    for local in self._local_vars:
      if local.name == local_name:
        if address:
          local.address = address
        if register:
          local.register = register
          local.active = True

  def local_names(self):
    return [local.name for local in self._local_vars]
      
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
      if not var.address:
        continue
      var_addr_int = int(var.address, 16)
      addr_int = int(address, 16)
      if var_addr_int >= addr_int and var_addr_int < addr_int + 8:
        var.active = True

  def is_changed_word(self, address):
    return address in self._changed_words

  @property
  def args(self):
    return self._args

  @property
  def local_vars(self):
    return self._local_vars

  @property
  def frame_top(self):
    return self._frame_top

  @frame_top.setter
  def frame_top(self, value):
    self._frame_top = value

  @property
  def parent_frame_top(self):
    return self._parent_frame_top

  @parent_frame_top.setter
  def parent_frame_top(self, value):
    self._parent_frame_top = value

  @property
  def frame_bottom(self):
    return self._frame_bottom

  @frame_bottom.setter
  def frame_bottom(self, value):
    self._frame_bottom = value

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
  def curr_instr_addr(self):
    return self._curr_instr_addr

  @curr_instr_addr.setter
  def curr_instr_addr(self, value):
    self._curr_instr_addr = value

