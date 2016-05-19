import subprocess
import multiprocessing
import sys
import os
import vsdb
import stackshot

class GDBRunner:

  def __init__(self, cfilename, step_command='stepi'):
    self.c_filename = cfilename # uncompiled .c file
    with open(self.c_filename) as f:
      self.code_lines = f.readlines()
    self.code_lines = [str(i+1) + '\t' + self.code_lines[i] for i in xrange(len(self.code_lines))]
    self.save_code()

    self.stackshot = stackshot.StackShot()
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
    self.step_command = step_command
    self.collector.start()
    self.collect_output('initial start')

  def save_code(self):
    vsdb.writeCode(self.code_lines)

  def collect_output(self, command):
    output = ''
    while '(gdb)' not in output:
      output += self.output_queue.get()
      if 'program is not being run' in output:
        self.running = False

    if command == self.step_command and 'exit(0)' in output:
      self.running = False
    self.output_file.write(output)
    self.stackshot.ingest(output, command)

  def send(self, command):
    self.output_file.write(command + '\n')
    self.proc.stdin.write(command + '\n')
    self.collect_output(command)

  def read_gdb_output(self, read_fd):
    while True:
      content = os.read(read_fd, 1000)
      self.output_queue.put(content)

  def skip_other_sources(self):
    self.send('info source')
    self.send('info sources')

    for src_file in self.stackshot.src_files:
      if src_file != self.stackshot.main_file:
        self.send('skip file %s' % src_file)

  def debug(self):
    self.running = True
    vsdb.setStep(0, 0)
    self.send('b main')
    self.send('run')
    self.skip_other_sources()
    self.send('display/i $pc')
    self.capture_stack()

  def capture_stack(self):
    if not self.running:
      return

    self.send('info registers')
    self.send('x/1xg $rbp')

    self.stackshot.clear_changed_words()
    for address in self.stackshot.frame_addresses():
      self.send('x/1xg %s' % address)

    # new function or first line of new function
    if self.stackshot.new_function or self.stackshot.new_frame_loaded:
      self.send('info args')
      for arg in self.stackshot.arg_names():
        self.send('p &%s' % arg)

    # new line of code
    if self.stackshot.new_line:
      self.send('info line %s' % str(self.stackshot.line_num))
      self.send('disas %s, %s' % tuple(self.stackshot.line_instruction_limits))

    self.send('info locals')
    for local in self.stackshot.local_names():
      self.send('p &%s' % local)

  def step(self):
    ''' Generator which steps once in gdb and yields a stackshot object
        describing the new stack. '''
    # hacky? 'run' yields first real stack
    yield self.stackshot
    latest_output = ''
    while self.running:
      self.send(self.step_command)
      self.capture_stack()
      yield self.stackshot

  def run_to_completion(self):
    ''' To be called AFTER debug. '''
    step_i = 0
    step_full = -1
    for output in self.step():
      print 'step_i: %d; step: %d is_new_line: %r' % (step_i, step_full, output.new_line)
      if output.new_line:
        step_full += 1
      vsdb.runnerStep(step_i, step_full, output)
      step_i += 1
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
  runner.debug()
  runner.run_to_completion()


if __name__ == '__main__':
    main()
