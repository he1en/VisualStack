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
    self._new_line = True
    self._new_function = True
    self._new_frame_loading = True
    self._new_frame_loaded = False

    self._fn_instructions = {} # line_num -> {addr -> instruction}
    self._saved_frame_boundaries = [] # 'stack' of frame boundaries
    self._saved_rip_addrs = [] # 'stack' of locations of rips

    self.stackshot = stackshot.StackShot()
    
    self.dummy_start_output = 'DUMMY START'
    self.step_command = 'stepi'

  @property
  def new_line(self):
    return self._new_line

  def first_time_new_function(self):
    return self._new_function and self.stackshot.first_time_in_function()

  @property
  def fn_instructions(self):
    return self._fn_instructions

  def get_stackshot(self):
    return self.stackshot

  def skip_file_commands(self):
    commands = []
    for src_file in self.stackshot.src_files:
      if src_file != self.stackshot.main_file:
        commands.append('skip file %s' % src_file)

    return commands

  def run_commands(self):
    return [
      'b main',
      'display/i $pc',
      'run',
      'info source',
      'info sources'
    ]

  def get_context_commands(self):
   commands = []
   commands.append('info registers')

   if self._new_function:
     commands.append('disassemble /m %s' % self.stackshot.current_fn_name())

   # new function or first line of new function
   if self._new_frame_loading or self._new_frame_loaded:
      commands.append('info args')
      
   commands.append('info locals')

   # get new frame boundary and rip location if in new leaf function,
   # else revert back to previous frame info
   if self.first_time_new_function():
     print "NEW"
     commands.append('info frame')
   elif self._new_function:
     self._saved_frame_boundaries.pop()
     self._saved_rip_addrs.pop()
     self.stackshot.frame_top = self._saved_frame_boundaries[-1]

   return commands

  def examine_commands(self):
    commands = []

    self.stackshot.clear_changed_words()
    if len(self._saved_frame_boundaries) > 1:
      frame_top = self._saved_frame_boundaries[-2]
    else:  # in main
      frame_top = self._saved_frame_boundaries[-1]
    for address in self.stackshot.frame_addresses(frame_top):
      commands.append('x/1xg %s' % address)
      
    for arg in self.stackshot.arg_names():
      commands.append('p &%s' % arg)
        
    for local in self.stackshot.local_names():
      commands.append('p &%s' % local)
          
    return commands

  def ingest(self, data, command):
    direct_commands = {
      '^run$': self.ingest_run,
      '^stepi$': self.ingest_stepi,
      '^info registers$': self.ingest_registers,
      '^info sources$': self.ingest_sources,
      '^info source$': self.ingest_main_file,
      '^info args$': self.ingest_args,
      '^info locals$': self.ingest_locals,
      'disassemble /m .+$': self.ingest_disassemble,
      '^info frame$': self.ingest_frame
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
        self.stackshot.add_src_file(src_file.strip())

  def ingest_main_file(self, data):
    self.stackshot.main_file = \
      re.match('Current source file is (.+)\n', data).group(1)

  def ingest_address_examine(self, address, data):
    contents = data.split(':')[-1].strip()
    if address not in self.stackshot.words or \
       self.stackshot.words[address] != contents:
      self.stackshot.set_word(address, contents)

  def ingest_registers(self, data):
    self.stackshot.clear_changed_regs()
    for register_output in data.split('\n')[:16]: # only want first 16
      register, contents = register_output.split()[:2]
      if self.stackshot.regs[register] != contents:
        self.stackshot.set_register(register, contents)

  def ingest_run(self, data):
    line_info = data.split('\n')[-3]
    line_num, line = line_info.split('\t')
    self.stackshot.line = line.strip()
    self.stackshot.line_num = int(line_num.strip())
    self.stackshot.add_fn_name('main')
    instr_addr = re.search('=> (.+) <.+>:', data.split('\n')[-1]).group(1)
    self.stackshot.curr_instr_addr = instr_addr

  def ingest_stepi(self, data):
    line_info = data.split('\n')[0]
    instr_addr = re.search('=> (.+) <.+>:', data.split('\n')[-1]).group(1)
    self.stackshot.curr_instr_addr = instr_addr

    if self.stackshot.main_file in data:
      ''' Stepped into new function '''
      self._new_function = True
      self._new_line = True
      self._new_frame_loading = True
      self._new_frame_loaded = False
      self.stackshot.clear_args()
      self.stackshot.clear_locals()

      self.stackshot.line = line_info.split('at')[0].strip()
      fn_data, line_data = \
        data.replace('\n', ' ').split(self.stackshot.main_file)
      self.stackshot.line_num = int(re.search(':(\d+)', line_data).group(1))
      fn_name = re.search('(\w+) \(', fn_data).group(1)
      self.stackshot.add_fn_name(fn_name)

    elif line_info[:2] != '0x':
      ''' Stepped into new line '''
      self._new_line = True
      if self._new_function:
        self._new_frame_loading = False
        self._new_frame_loaded = True
        self._new_function = False
      line_num, line = line_info.split('\t')
      self.stackshot.line = line.strip()
      self.stackshot.line_num = int(line_num.strip())

    else:
      ''' Stepped into new assembly instruction in same line '''
      self._new_line = False
      self._new_frame_loaded = False
      self._new_function = False
      _, line_num, line = line_info.split('\t')
      self.stackshot.line = line.strip()
      self.stackshot.line_num = int(line_num.strip())

  def ingest_disassemble(self, data):
    self._fn_instructions = {}
    for line in data.split('\n')[1:-1]:
      line = line.replace('=>', '')
      if len(line) == 0:
        continue
      
      elif line[0] != ' ':
        line_num = int(line.split()[0])
        self._fn_instructions[line_num] = {}
       
      else:
        location, contents = line.split('>:')
        addr = location.split('<')[0].strip()
        self._fn_instructions[line_num][addr] = contents.strip()

  def ingest_frame(self, data):
    frame_line = data.split('\n')[0]
    rip_line = data.split('\n')[-1]

    frame_boundary = re.search('frame at (0x[a-f0-9]+):', frame_line).group(1)
    self._saved_frame_boundaries.append(frame_boundary)
    print self._saved_frame_boundaries
    self.stackshot.frame_top = frame_boundary

    rip_addr = re.search('rip at (0x[a-f0-9]+)', rip_line).group(1)
    self._saved_rip_addrs.append(rip_addr)

  def ingest_var_address(self, var_name, data):
    address = data.split()[-1].strip()

    if var_name in self.stackshot.arg_names():
      self.stackshot.set_arg_address(var_name,
                                     address,
                                     self._saved_rip_addrs[-1])

    if var_name in self.stackshot.local_names():
      self.stackshot.set_local_address(var_name, address)

  def ingest_vars(self, var_list, data):
    new_vars = (len(var_list) == 0)
    for line in data.split('\n'):
      name, val = line.split(' = ')
      if new_vars:
        var = self.stackshot.Var(name.strip(), value=val.strip())
        var_list.append(var)
      else:
        var = filter(lambda v: v.name == name, var_list)[0]
        var.value = val.strip()
        if not self.stackshot.first_time_in_function():
          # If we're returning back to this function, all vars were
          # already set active.
          var.active = True

  def ingest_args(self, data):
    self.ingest_vars(self.stackshot.args, data)

  def ingest_locals(self, data):
    if data.strip() == 'No locals.':
      return

    self.ingest_vars(self.stackshot.local_vars, data)
