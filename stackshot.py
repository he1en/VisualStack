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

    self.changed_regs = []
    self.changed_words = []

    self.saved_rbp = None
    self.main_file = None
    self.src_files = []

    self.no_action_commands = [
      'b main',
      'run',
      'skip .+'
    ]

  def stringify(self):
    # TODO: make this useful
    return self.line

  def ingest(self, data, command):
    data = data.replace('\n(gdb)', '')
    try:
      {
        'next': self.ingest_step,
        'step': self.ingest_step,
        'info registers': self.ingest_registers,
        'info sources': self.ingest_sources,
        'info source': self.ingest_main_file,
        'x/1xg $rbp': self.ingest_saved_rbp
      }[command](data)
    except KeyError:
      if command in self.no_action_commands:
        return

      address = re.match('^x/1xg (0x[a-f\d]+)$', command)
      if address:
        self.ingest_address_examine(address.group(1), data)
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
      self.changed_words.append(address)

  def ingest_registers(self, data):
    self.changed_regs = []
    for register_output in data.split("\n")[:16]: # only want first 16
      register, contents = register_output.split()[:2]
      if self.regs[register] != contents:
        self.changed_regs.append(register)
        self.regs[register] = contents

  def ingest_step(self, new_data):
    last_line = new_data.split('\n')[-1]
    self.line = last_line

  def clear_changed_words(self):
    self.changed_words = []

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

