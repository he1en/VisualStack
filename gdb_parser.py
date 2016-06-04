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
NUM_REGS = 17

class GDBParser:

  def __init__(self):
    self._new_line = True
    self._new_function = True
    self._re_entered_fn = False

    self._fn_instructions = {} # line_num -> {addr -> instruction}
    self._functions = [] # 'stack' of (fn_name, first instruction addr) tuples
    self._saved_frame_boundaries = [] # 'stack' of frame boundaries
    self._saved_rip_addrs = [] # 'stack' of locations of rips

    self.stackshot = stackshot.StackShot()
    
    self.dummy_start_output = 'DUMMY START'
    self.step_command = 'stepi'

  @property
  def new_line(self):
    return self._new_line

  def new_function_first_entry(self):
    return self._new_function and not self._re_entered_fn

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
    ''' Called after gdb made a stepi '''
    commands = []
    commands.append('info registers')
    commands.append('print $eflags')

    if self._new_function:
      commands.append('disassemble /m %s' % self._functions[-1][0])

    commands.append('info args')
    commands.append('info locals')

    # get new frame boundary and rip location if in new leaf function
    if self.new_function_first_entry():
      commands.append('info frame')

    return commands

  def examine_commands(self):
    ''' Called after get_context_commands '''
    commands = []
    
    self.calc_frame_bottom()

    self.stackshot.clear_changed_words()
    for address in self.stackshot.frame_addresses():
      commands.append('x/1xg %s' % address)
      
    for var in self.stackshot.args + self.stackshot.local_vars:
      if not var.value == '<optimized out>':
        commands.append('p &%s' % var.name)
          
    return commands

  def calc_frame_bottom(self):
    rsp = self.stackshot.regs['rsp']
    if self._new_function or rsp < self.stackshot.frame_bottom:
      self.stackshot.frame_bottom = rsp

  def parse(self, data, command):
    try:
      self.failed = False
      self.ingest(data, command)
    except (ValueError, IndexError, AttributeError) as e:
      print 'ERROR!: \'%s\' parsing command \'%s\' on gdb output:\n %s.' \
        % (e, command, data)
      self.failed = True

  def ingest(self, data, command):
    direct_commands = {
      '^run$': self.ingest_run,
      '^stepi$': self.ingest_stepi,
      '^info registers$': self.ingest_registers,
      '^print \$eflags$': self.ingest_flags,
      '^info sources$': self.ingest_sources,
      '^info source$': self.ingest_main_file,
      '^info args$': self.ingest_args,
      '^info locals$': self.ingest_locals,
      'disassemble /m .+$': self.ingest_disassemble,
      '^info frame$': self.ingest_frame,
      '^finish$': self.ingest_finish
    }
    match_commands = {
      '^x/1xg (0x[a-f\d]+)$': self.ingest_address_examine,
      '^p &(.+)$': self.ingest_var_location
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
      self.stackshot.add_src_file(src_file.strip())

  def ingest_main_file(self, data):
    self.stackshot.main_file = \
      re.match('Current source file is (.+)\n', data).group(1)

  def ingest_address_examine(self, address, data):
    contents = data.split(':')[-1].strip()
    if address not in self.stackshot.words:
      self.stackshot.set_word(address, contents)

    if self.stackshot.words[address] != contents:
      self.stackshot.set_word(address, contents)
      if address < self.stackshot.frame_bottom:
        self.stackshot.frame_bottom = address

  def ingest_registers(self, data):
    self.stackshot.clear_changed_regs()
    for register_output in data.split('\n')[:NUM_REGS]:
      register, contents = register_output.split()[:2]
      if self.stackshot.regs[register] != contents:
        self.stackshot.set_register(register, contents)

  def ingest_flags(self, data):
    flags = data.split(' = ')[-1]
    self.stackshot.set_register('eflags', flags)


  def ingest_run(self, data):
    line_info = data.split('\n')[-3]
    line_num, line = line_info.split('\t')
    self.stackshot.line = line.strip()
    self.stackshot.line_num = int(line_num.strip())
    instr_addr = re.search('=> (.+) <.+>:', data.split('\n')[-1]).group(1)
    self.stackshot.curr_instr_addr = instr_addr
    self._functions.append(('main', instr_addr))

  def ingest_finish(self, data):
    if data == '"finish" not meaningful in the outermost frame.':
      return

    lines = data.split('\n')
    for i, line in enumerate(lines):
      if re.match('=>', line):
        instr_info = line
        line_info = lines[i-2]
        
    instr_addr = re.search('=> (.+) <.+>:', instr_info).group(1)
    self.stackshot.curr_instr_addr = instr_addr

    self._new_line = True
    fn_name = re.search('<(.+)\+\d+>:', instr_info).group(1)
    if fn_name != self._functions[-1][0]:
      ''' We stepped out of the erroring function into a different
          function than we were in before '''
      self.clean_data_for_new_fn(fn_name, instr_addr, forced_finish=True)
    
    line_num, line = line_info.split('\t')
    self.stackshot.line_num = int(line_num)
    self.stackshot.line = line.strip()

  def clean_data_for_new_fn(self, fn_name, instr_addr, forced_finish=False):
    self._re_entered_fn = False
    self._new_function = True
    self._new_line = True
    self.stackshot.clear_args()
    self.stackshot.clear_locals()

    old_frame_fn = self._functions[-1]
    if fn_name == old_frame_fn[0] and instr_addr != old_frame_fn[1]:
      # stepped into previous function, we know because same name and we
      # didn't start at the beginning so it's not recursion
      self._re_entered_fn = True
      if not forced_finish:
        # this won't work if we forced a finish after ingest_frame
        # succeeded for a step
        self._saved_frame_boundaries.pop()
        self._saved_rip_addrs.pop()
        self._functions.pop()
      self.stackshot.frame_top = self._saved_frame_boundaries[-1]
      self.stackshot.parent_frame_top = self._saved_frame_boundaries[-2]
    else:
      self._functions.append((fn_name, instr_addr))


  def stepped_out_of_src_file(self, data):
    flat_output = data.join('')
    for f in self.stackshot.src_files:
      if f in data:
        print 'ERROR!: Stepped out of main source file.'
        return True
    return False

  def ingest_stepi(self, data):
    if self.stepped_out_of_src_file(data):
      self.failed = True
      return
    # print 'INGESTING: <', data, '>'

    line_info = data.split('\n')[0]
    instr_addr = re.search('=> (.+) <.+>:', data.split('\n')[-1]).group(1)
    self.stackshot.curr_instr_addr = instr_addr

    if self.stackshot.main_file in data:
      ''' Stepped into new function '''
      fn_data, line_data = \
        data.replace('\n', ' ').split(self.stackshot.main_file)
      line_num = int(re.search(':(\d+)', line_data).group(1))
      self.stackshot.line_num = line_num
      fn_name = re.search('(\w+) \(', fn_data).group(1)

      for i, line in enumerate(data.split('\n')):
        if 'at %s:%d' % (self.stackshot.main_file, line_num) in line:
          line_contents = data.split('\n')[i+1]
          self.stackshot.line = line_contents.split('\t')[-1]
          break

      self.clean_data_for_new_fn(fn_name, instr_addr)

    elif line_info[:2] != '0x':
      ''' Stepped into new line '''
      self._new_line = True
      self._new_function = False
      line_num, line = line_info.split('\t')
      self.stackshot.line = line.strip()
      self.stackshot.line_num = int(line_num.strip())

    else:
      ''' Stepped into new assembly instruction in same line '''
      self._new_line = False
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
    if self._functions[-1][0] == 'main':
      self._saved_frame_boundaries.append(frame_boundary)
      self.stackshot.frame_top = frame_boundary

    self.stackshot.parent_frame_top = self.stackshot.frame_top
    self.stackshot.frame_top = frame_boundary

    rip_addr = re.search('rip at (0x[a-f0-9]+)', rip_line).group(1)
    self._saved_rip_addrs.append(rip_addr)

  def ingest_var_location(self, var_name, data):
    if re.match('Can\'t take address of \".+\" which isn\'t an lvalue.', data):
      self.stackshot.set_var_opimized_out(var_name)
      return

    in_reg_match = \
      re.match('Address requested for identifier .+ which is in register \$(.+)',
                data)
    address = register = None
    if in_reg_match:
      register = in_reg_match.group(1).strip()
    else:
      address = data.split()[-1].strip()

    if var_name in self.stackshot.arg_names():
      self.stackshot.set_arg_location(self._saved_rip_addrs[-1],
                                      var_name,
                                      address,
                                      register,
                                      self._functions[-1] == 'main')

    if var_name in self.stackshot.local_names():
      self.stackshot.set_local_location(var_name, address, register)

  def ingest_vars(self, var_list, data):
    new_vars = (len(var_list) == 0)
    for line in data.split('\n'):
      splt = line.find(' = ')
      name = line[0:splt].strip()
      val = line[splt+len(' = '):].strip()
      if new_vars:
        var = self.stackshot.Var(name, value=val)
        var_list.append(var)
      else:
        var = filter(lambda v: v.name == name, var_list)[0]
        var.value = val
        if val == '<optimized out>':
          var.active = False

      if self._re_entered_fn and not val == '<optimized out>':
        # If we're returning back to this function, all vars were
        # already set active.
        var.active = True

  def ingest_args(self, data):
    self.ingest_vars(self.stackshot.args, data)

  def ingest_locals(self, data):
    if data.strip() == 'No locals.':
      return

    self.ingest_vars(self.stackshot.local_vars, data)
