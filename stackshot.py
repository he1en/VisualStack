########################################
# Stack Shot Class
# 
########################################
import re

regs = ['rsp', 'rbp', 'rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi',
        'r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15']


class StackShot:

  def __init__(self):
    self.line = None  # String, last line number
    self.regs = {r: 'N/A' for r in regs}
    self.words = {}
    self.ordered_addresses = []
    self.ordered_regs = regs

    self.changed_regs = set()
    self.changed_words = set()

    self.saved_rbp = None
    self.main_file = None
    self.src_files = []

  # invoke on a new stackshot instance
  def hydrate_from_db(self, stackframe, stackwords, changes):
    self.line = stackframe[0].LineContents
    self.regs['rsp'] = stackframe[0].RSP
    self.regs['rbp'] = stackframe[0].RBP
    self.regs['rax'] = stackframe[0].RAX
    self.regs['rbx'] = stackframe[0].RBX
    self.regs['rcx'] = stackframe[0].RCX
    self.regs['rdx'] = stackframe[0].RDX
    self.regs['rsi'] = stackframe[0].RSI
    self.regs['rdi'] = stackframe[0].RDI
    self.regs['r8'] = stackframe[0].R8
    self.regs['r9'] = stackframe[0].R9
    self.regs['r10'] = stackframe[0].R10
    self.regs['r11'] = stackframe[0].R11
    self.regs['r12'] = stackframe[0].R12
    self.regs['r13'] = stackframe[0].R13
    self.regs['r14'] = stackframe[0].R14
    self.regs['r15'] = stackframe[0].R15
    for i in xrange(len(stackwords)):
      self.words[stackwords[i].MemAddr] = stackwords[i].MemContents
    self.ordered_addresses = sorted(self.words.keys(), key = lambda addr: int(addr, 16), reverse=True)
    for i in xrange(len(changes)):
      if changes[i].ChangeType == 'REGISTER':
        self.changed_regs.add(changes[i].ChangeAddr)
      elif changes[i].ChangeType == 'WORD':
        self.changed_words.add(changes[i].ChangeAddr)

  def stringify(self):
    # TODO: make this useful
    return self.line

  def ingest(self, data, command):
    direct_commands = {
        'next': self.ingest_step,
        'step': self.ingest_step,
        'info registers': self.ingest_registers,
        'info sources': self.ingest_sources,
        'info source': self.ingest_main_file,
        'x/1xg $rbp': self.ingest_saved_rbp
    }
    match_commands = {
      '^x/1xg (0x[a-f\d]+)$': self.ingest_address_examine
    }
    no_action_commands = [
      '^b main$',
      '^run$',
      '^skip .+$'
    ]

    data = data.replace('\n(gdb)', '')

    for direct_command in direct_commands.keys():
      if direct_command == command:
        direct_commands[command](data)
        return

    for match_command in match_commands.keys():
      match = re.match(match_command, command)
      if match:
        match_commands[match_command](match.group(1), data)
        return

    for no_action_command in no_action_commands:
      if re.match(no_action_command, command):
        return

    print "Cannot ingest data from gdb command %s." % command
      
  def ingest_sources(self, data):
    for src_file in data.split(', '):
      if "Source files for which" in src_file:
        continue
      if src_file[-2:] == '.c':
        self.src_files.append(src_file.strip())

  def ingest_main_file(self, data):
    self.main_file = re.match('Current source file is (.+)\n', data).group(1)

  def ingest_saved_rbp(self, data):
    self.saved_rbp = data.split(":")[-1].strip()

  def ingest_address_examine(self, address, data):
    contents = data.split(":")[-1].strip()
    if address not in self.words or self.words[address] != contents:
      self.words[address] = contents
      self.changed_words.add(address)

  def ingest_registers(self, data):
    self.changed_regs = set()
    for register_output in data.split("\n")[:16]: # only want first 16
      register, contents = register_output.split()[:2]
      if self.regs[register] != contents:
        self.changed_regs.add(register)
        self.regs[register] = contents

  def ingest_step(self, new_data):
    last_line = new_data.split('\n')[-1]
    self.line = last_line

  def clear_changed_words(self):
    self.changed_words = set()

  def frame_addresses(self):
    ''' Collects all stack addresses in current frame in descending order. '''
    addresses = []
    rbp_int = int(self.regs['rbp'], 16)
    rsp_int = int(self.regs['rsp'], 16)
    saved_rbp_int = int(self.saved_rbp, 16)

    # Collect memory above base pointer until saved base pointer
    if saved_rbp_int == 0:
      # If saved_rbp is 0x0, we are in main.
      num_above = 0
    else:
      num_above = (saved_rbp_int - rbp_int) / 8

    for i in range(num_above):
      addresses.append(hex(saved_rbp_int - i * 8))
      
    addresses.append(self.regs['rbp'])

    # Collect memory below base pointer until stack pointer
    num_below = (rbp_int - rsp_int) / 8
    for i in range(1, num_below):
      addresses.append(hex(rbp_int - i * 8) )

    return addresses

