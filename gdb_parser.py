########################################
# GDB Parser Class
#
# 
#
# 
# 
# 
# 
# 
#
########################################
import re
import stackshot

REDZONE_SIZE = 16
WORD = 8

class GDBParser:

  def __init__(self):
    self.new_line = True
    self.new_function = True
    self.new_frame_loaded = True

    self.stackshot = stackshot.StackShot()
    
    self.dummy_start_output = 'DUMMY START'
    self.step_command = 'stepi'


  def get_stackshot(self):
    return self.stackshot

  def setup_output_commands(self):
    commands = []
    for src_file in self.stackshot.src_files:
      if src_file != self.stackshot.main_file:
        commands.append('skip file %s' % src_file)

    commands.append('display/i $pc')

    return commands

  def run_commands(self):
    return [
      'b main',
      'run',
      'info source',
      'info sources'
    ]

  def get_context_commands(self):
   commands = []
   commands.append('info registers')
   commands.append('x/1xg $rbp')
   # new function or first line of new function
   if self.stackshot.new_function or self.stackshot.new_frame_loaded:
      commands.append('info args')
      
   # new line of code
   if self.stackshot.new_line:
     commands.append('info line %s' % str(self.stackshot.line_num))

   commands.append('info locals')

   return commands

  def examine_commands(self):
    commands = []
    if self.stackshot.new_line:
      commands.append('disas %s, %s' % tuple(self.stackshot.line_instruction_limits))

    self.stackshot.clear_changed_words()
    for address in self.stackshot.frame_addresses():
      commands.append('x/1xg %s' % address)
      
    for arg in self.stackshot.arg_names():
      commands.append('p &%s' % arg)
        
    for local in self.stackshot.local_names():
      commands.append('p &%s' % local)
          
    return commands

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
      '^%s$' % self.dummy_start_output,
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
        self.stackshot.src_files.append(src_file.strip())

  def ingest_main_file(self, data):
    self.stackshot.main_file = re.match('Current source file is (.+)\n', data).group(1)

  def ingest_saved_rbp(self, data):
    self.stackshot.saved_rbp = data.split(':')[-1].strip()

  def ingest_address_examine(self, address, data):
    contents = data.split(':')[-1].strip()
    if address not in self.stackshot.words or self.stackshot.words[address] != contents:
      self.stackshot.words[address] = contents
      self.stackshot.changed_words.add(address)

      for var in self.stackshot.args + self.stackshot.local_vars:
        # TODO: address not on word boundary
        if var.address == address:
          var.active = True

  def ingest_registers(self, data):
    self.stackshot.changed_regs = set()
    for register_output in data.split('\n')[:16]: # only want first 16
      register, contents = register_output.split()[:2]
      if self.stackshot.regs[register] != contents:
        self.stackshot.changed_regs.add(register)
        self.stackshot.regs[register] = contents

  def ingest_step(self, new_data):
    last_line = new_data.split('\n')[-1]
    self.stackshot.line = last_line
    line_num = last_line.split()[0]
    try: 
      self.stackshot.line_num = int(line_num)
    except ValueError:
      self.stackshot.line_num = None

  def ingest_run(self, data):
    line_info = data.split('\n')[-1]
    line_num, line = line_info.split('\t')
    self.stackshot.line = line.strip()
    self.stackshot.line_num = line_num.strip()
    self.stackshot.fn_names.append('main')
    try:
      self.stackshot.line_num = int(self.stackshot.line_num)
    except ValueError:
      self.stackshot.line_num = None

  def ingest_stepi(self, data):
    line_info = data.split('\n')[0]
    assembly_info = data.split('\n')[-1]
    self.stackshot.instruction = assembly_info.split(':')[-1]

    if self.stackshot.main_file in data:
      ''' Stepped into new function '''
      self.stackshot.new_function = True
      self.stackshot.new_line = True
      self.stackshot.new_frame_loaded = False
      self.stackshot.clear_args()
      self.stackshot.clear_locals()

      self.stackshot.line = line_info.split('at')[0].strip()
      fn_data, line_data = data.replace('\n', ' ').split(self.stackshot.main_file)
      self.stackshot.line_num = re.search(':(\d+)', line_data).group(1)
      fn_name = re.search('(\w+) \(', fn_data).group(1)
      self.stackshot.fn_names.append(fn_name)

    elif line_info[:2] != '0x':
      ''' Stepped into new line '''
      self.stackshot.new_line = True
      if self.stackshot.new_function:
        self.stackshot.new_frame_loaded = True
        self.stackshot.new_function = False
      line_num, line = line_info.split('\t')
      self.stackshot.line = line.strip()
      self.stackshot.line_num = line_num.strip()

    else:
      ''' Stepped into new assembly instruction in same line '''
      self.stackshot.curr_instruction_index += 1
      self.stackshot.new_line = False
      self.stackshot.new_frame_loaded = False
      _, line_num, line = line_info.split('\t')
      self.stackshot.line = line.strip()
      self.stackshot.line_num = line_num.strip()
    try:
      self.stackshot.line_num = int(self.stackshot.line_num)
    except ValueError:
      self.stackshot.line_num = None

  def ingest_line_info(self, data):
    self.stackshot.line_instruction_limits = re.findall('(0x[a-f\d]+)', data)

  def ingest_disas(self, data):
    self.stackshot.instruction_lines = []
    self.stackshot.curr_instruction_index = 0
    for i, instruction_info in enumerate(data.split('\n')[1:-1]):
      instruction = instruction_info.split(':')[-1].strip()
      self.stackshot.instruction_lines.append(instruction)

  def ingest_var_address(self, var_name, data):
    address = data.split()[-1].strip()

    if var_name in self.stackshot.arg_names():
      self.stackshot.set_arg_address(var_name, address)

    if var_name in self.stackshot.local_names():
      self.stackshot.set_local_address(var_name, address)

  def ingest_args(self, data):
    ''' set highest arg address to above the saved instruction pointer '''
    self.stackshot.highest_arg_addr = hex(int(self.stackshot.regs['rbp'], 16) + WORD)

    new_args = (len(self.stackshot.args) == 0)
    for line in data.split('\n'):
      name, val = line.split(' = ')
      if new_args:
        arg = self.stackshot.Var(name.strip(), value=val.strip())
        self.stackshot.args.append(arg)
      else:
        arg = filter(lambda a: a.name == name, self.stackshot.args)[0]
        arg.value = val.strip()
        if not self.stackshot.first_time_in_function():
          # If we're returning back to this function, all args were
          # already set active.
          arg.active = True

  def ingest_locals(self, data):
    if data.strip() == 'No locals.':
      return

    new_locals = (len(self.stackshot.local_vars) == 0)
    for line in data.split('\n'):
      name, val = line.split(' = ')
      if new_locals:
        var = self.stackshot.Var(name.strip(), value=val.strip())
        self.stackshot.local_vars.append(var)
      else:
        var = filter(lambda v: v.name == name, self.stackshot.local_vars)[0]
        var.value = val.strip()
        if not self.stackshot.first_time_in_function():
          # If we're returning back to this function, all vars were
          # already set active.
          var.active = True
