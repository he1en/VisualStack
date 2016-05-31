########################################
# GDB Runner Class
#
# Usage: python gdb_runner.py <uncompiled c file>
#
# Compiles the c file and Starts a gdb process on its executable.
# Repeatedly calls 'stepi' and extracts information about the stack at
# every step, and passes the unformatted gdb output to gdb-parser.
# Also creates an output file that is the exact gdb output as if it
# were run on command line.
#
########################################

import subprocess
import multiprocessing
import sys
import os
import vsdb
import stackshot
import gdb_parser

class GDBRunner:

  def __init__(self, cfilename, step_command='stepi'):
    self.c_filename = cfilename # uncompiled .c file
    with open(self.c_filename) as f:
      self.code_lines = f.readlines()
    self.code_lines = [str(i+1) + '\t' + self.code_lines[i] \
                       for i in xrange(len(self.code_lines))]
    self.save_code()

    self.parser = gdb_parser.GDBParser()
    self.running = False

    self.filename = self.c_filename.replace('.c', '') # compiled file
    subprocess.call(['gcc', self.c_filename, '-o', self.filename, '-g'])

    self.output_file = open('output_' + self.filename, 'w')
    self.proc = subprocess.Popen(['gdb', self.filename], \
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    self.output_queue = multiprocessing.Queue()
    fd = self.proc.stdout.fileno()
    self.collector = multiprocessing.Process(target=self.read_gdb_output, \
                                             args=[fd])
    self.collector.start()
    self.collect_output(self.parser.dummy_start_output)
    
    self.step_num = 0
    self.step_i = 0

  def save_code(self):
    vsdb.writeCode(self.code_lines)

  def collect_output(self, command):
    output = ''
    while '(gdb)' not in output:
      output += self.output_queue.get()
      if 'program is not being run' in output:
        self.running = False

    if command == self.parser.step_command and 'exit(0)' in output:
      self.running = False

    self.output_file.write(output)
    self.parser.ingest(output, command)

  def send(self, command):
    self.output_file.write(command + '\n')
    self.proc.stdin.write(command + '\n')
    self.collect_output(command)

  def read_gdb_output(self, read_fd):
    while True:
      content = os.read(read_fd, 1000)
      self.output_queue.put(content)

  def start(self):
    self.running = True

    for command in self.parser.run_commands():
      self.send(command)
    for command in self.parser.skip_file_commands():
      self.send(command)
    self.capture_stack()

    vsdb.writeAssembly(self.parser.fn_instructions)
    vsdb.setStep(self.step_num, self.step_i)
    vsdb.runnerStep(self.step_num, self.step_i, self.parser.get_stackshot())

  def capture_stack(self):
    for command in self.parser.get_context_commands():
      self.send(command)
    for command in self.parser.examine_commands():
      self.send(command)

  def next(self):
    if not self.running:
      return None
   
    self.send(self.parser.step_command)
    self.capture_stack()

    if self.parser.first_time_new_function():
      vsdb.writeAssembly(self.parser.fn_instructions)

    if self.parser.new_line:
      self.step_num += 1
      self.step_i = 0
    else:
      self.step_i += 1    

    vsdb.runnerStep(self.step_num, self.step_i, self.parser.get_stackshot())

  def run_to_completion(self):
    ''' To be called AFTER start. '''
    while self.running:
      self.next()

    self.terminate()

  def terminate(self):
    self.proc.terminate()
    self.collector.terminate()
    self.output_file.close()

def main():
  if len(sys.argv) != 2 or not sys.argv[1].endswith('.c'):
    print 'Usage: python gdb_runner.py <uncompiled c file>'
    exit(0)

  runner = GDBRunner(sys.argv[1])
  runner.start()
  runner.run_to_completion()


if __name__ == '__main__':
    main()
