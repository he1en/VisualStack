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

  # invoke on a new stackshot instance
  def hydrate_from_db(self, stackframe, stackwords, registers, local_vars, arguments, assembly, step_direction):
    step_ = stackframe[0].StepNum
    stepi_ = stackframe[0].StepINum
    self.line = stackframe[0].LineContents
    self.line_num = stackframe[0].LineNum
    self.curr_instruction_index = stepi_
    self.highest_arg_addr = stackframe[0].HighestArgAddr

    for i in xrange(len(registers)):
      self.regs[registers[i].RegName] = registers[i].RegContents
      reg_s = registers[i].StepNum
      reg_si = registers[i].StepINum
      if step_direction is not None and  "i_" in step_direction: # stepi_forward or stepi_back
        if reg_s == step_ and reg_si == stepi_:
          self.changed_regs.add(registers[i].RegName)
      else:
        if (reg_s == step_-1 and reg_si != 0) or (reg_s == step_ and reg_si == stepi_):
          self.changed_regs.add(registers[i].RegName)

    for i in xrange(len(stackwords)):
      self.words[stackwords[i].MemAddr] = stackwords[i].MemContents
      sw_s = stackwords[i].StepNum
      sw_si = stackwords[i].StepINum
      if step_direction is not None and "i_" in step_direction:
        if sw_s == step_ and sw_si == stepi_:
          self.changed_words.add(stackwords[i].MemAddr)
      else:
        if (sw_s == step_-1 and sw_si != 0) or (sw_s == step_ and sw_si == stepi_):
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

  def ingest(self, data, command):
    direct_commands = {
      '^run$': self.ingest_run,
      '^next$': self.ingest_step,
      '^step$': self.ingest_step,
      '^stepi$': self.ingest_stepi,
      '^info registers$': self.ingest_registers,
      '^info sources$': self.ingest_sources,
      '^info source$': self.ingest_main_file,
      '^x/1xg \$rbp$': self.ingest_saved_rbp,
      '^info args$': self.ingest_args,
      '^info locals$': self.ingest_locals,
      '^info line \d+$': self.ingest_line_info,
      'disas .+, .+$': self.ingest_disas
    }
    match_commands = {
      '^x/1xg (0x[a-f\d]+)$': self.ingest_address_examine,
      '^p &(.+)$': self.ingest_var_address
    }
    no_action_commands = [
      '^initial start$',
      '^b main$',
      '^skip .+$',
      '^display/i \$pc$'
    ]

    data = data.replace('\n(gdb)', '')

    for direct_command in direct_commands.keys():
      if re.match(direct_command, command):
        direct_commands[direct_command](data)
        return

    for match_command in match_commands.keys():
      match = re.match(match_command, command)
      if match:
        match_commands[match_command](match.group(1), data)
        return

    for no_action_command in no_action_commands:
      if re.match(no_action_command, command):
        return

    print 'Cannot ingest data from gdb command %s.' % command
      
  def ingest_sources(self, data):
    for src_file in data.split(', '):
      if 'Source files for which' in src_file:
        continue
      if src_file[-2:] == '.c':
        self.src_files.append(src_file.strip())

  def ingest_main_file(self, data):
    self.main_file = re.match('Current source file is (.+)\n', data).group(1)

  def ingest_saved_rbp(self, data):
    self.saved_rbp = data.split(':')[-1].strip()

  def ingest_address_examine(self, address, data):
    contents = data.split(':')[-1].strip()
    if address not in self.words or self.words[address] != contents:
      self.words[address] = contents
      self.changed_words.add(address)

      for var in self.args + self.local_vars:
        # TODO: address not on word boundary
        if var.address == address:
          var.active = True

  def ingest_registers(self, data):
    self.changed_regs = set()
    for register_output in data.split('\n')[:16]: # only want first 16
      register, contents = register_output.split()[:2]
      if self.regs[register] != contents:
        self.changed_regs.add(register)
        self.regs[register] = contents

  def ingest_step(self, new_data):
    last_line = new_data.split('\n')[-1]
    self.line = last_line
    line_num = last_line.split()[0]
    try: 
      self.line_num = int(line_num)
    except ValueError:
      self.line_num = None

  def ingest_run(self, data):
    line_info = data.split('\n')[-1]
    line_num, line = line_info.split('\t')
    self.line = line.strip()
    self.line_num = line_num.strip()
    self.fn_names.append('main')
    try:
      self.line_num = int(self.line_num)
    except ValueError:
      self.line_num = None

  def ingest_stepi(self, data):
    line_info = data.split('\n')[0]
    assembly_info = data.split('\n')[-1]
    self.instruction = assembly_info.split(':')[-1]

    if self.main_file in data:
      ''' Stepped into new function '''
      self.new_function = True
      self.new_line = True
      self.new_frame_loaded = False
      self.clear_args()
      self.clear_locals()

      self.line = line_info.split('at')[0].strip()
      fn_data, line_data = data.replace('\n', ' ').split(self.main_file)
      self.line_num = re.search(':(\d+)', line_data).group(1)
      fn_name = re.search('(\w+) \(', fn_data).group(1)
      self.fn_names.append(fn_name)

    elif line_info[:2] != '0x':
      ''' Stepped into new line '''
      self.new_line = True
      if self.new_function:
        self.new_frame_loaded = True
        self.new_function = False
      line_num, line = line_info.split('\t')
      self.line = line.strip()
      self.line_num = line_num.strip()

    else:
      ''' Stepped into new assembly instruction in same line '''
      self.curr_instruction_index += 1
      self.new_line = False
      self.new_frame_loaded = False
      _, line_num, line = line_info.split('\t')
      self.line = line.strip()
      self.line_num = line_num.strip()
    try:
      self.line_num = int(self.line_num)
    except ValueError:
      self.line_num = None

  def ingest_line_info(self, data):
    self.line_instruction_limits = re.findall('(0x[a-f\d]+)', data)

  def ingest_disas(self, data):
    self.instruction_lines = []
    self.curr_instruction_index = 0
    for i, instruction_info in enumerate(data.split('\n')[1:-1]):
      instruction = instruction_info.split(':')[-1].strip()
      self.instruction_lines.append(instruction)

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

  def ingest_var_address(self, var_name, data):
    address = data.split()[-1].strip()

    if var_name in self.arg_names():
      self.set_arg_address(var_name, address)

    if var_name in self.local_names():
      self.set_local_address(var_name, address)

  def ingest_args(self, data):
    ''' set highest arg address to above the saved instruction pointer '''
    self.highest_arg_addr = hex(int(self.regs['rbp'], 16) + WORD)

    new_args = (len(self.args) == 0)
    for line in data.split('\n'):
      name, val = line.split(' = ')
      if new_args:
        arg = self.Var(name.strip(), value=val.strip())
        self.args.append(arg)
      else:
        arg = filter(lambda a: a.name == name, self.args)[0]
        arg.value = val.strip()
        if not self.first_time_in_function():
          # If we're returning back to this function, all args were
          # already set active.
          arg.active = True

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

  def ingest_locals(self, data):
    if data.strip() == 'No locals.':
      return

    new_locals = (len(self.local_vars) == 0)
    for line in data.split('\n'):
      name, val = line.split(' = ')
      if new_locals:
        var = self.Var(name.strip(), value=val.strip())
        self.local_vars.append(var)
      else:
        var = filter(lambda v: v.name == name, self.local_vars)[0]
        var.value = val.strip()
        if not self.first_time_in_function():
          # If we're returning back to this function, all vars were
          # already set active.
          var.active = True

  def set_local_address(self, local_name, address):
    for local in self.local_vars:
      if local.name == local_name:
        local.address = address

  def local_names(self):
    return [local.name for local in self.local_vars]
      
  def first_time_in_function(self):
    return self.fn_names.count(self.fn_names[-1]) == 1
