import subprocess
import multiprocessing
import sys
import os
import vsdb
import stackshot

class GDBRunner:

  def __init__(self, filename):
    self.filename = filename
    self.stackshot = stackshot.StackShot()
    self.running = False

    self.output_file = open('output_' + self.filename, 'w')
    self.proc = subprocess.Popen(['gdb', self.filename], \
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    self.output_queue = multiprocessing.Queue()
    fd = self.proc.stdout.fileno()
    self.collector = multiprocessing.Process(target=self.read_gdb_output, \
                                             args=[fd])
    self.collector.start()
    self.collect_output('step')

  def collect_output(self, command):
    output = ''
    while "(gdb)" not in output:
      output += self.output_queue.get()
      if "program is not being run" in output:
        self.running = False

    if command == 'step' and "exit(0)" in output:
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
    vsdb.setStep(0)
    self.send('b main')
    self.send('run')
    self.skip_other_sources()
    self.capture_stack()


  def capture_stack(self, capture_registers=True):
    if not self.running:
      return

    if capture_registers:
      self.send('info registers')
    self.send('x/1xg $rbp')
    self.stackshot.clear_changed_words()
    for address in self.stackshot.frame_addresses():
      self.send('x/1xg %s' % address)

  def step(self):
    ''' Generator which steps once in gdb and yields a stackshot object
        describing the new stack. '''
    # hacky? 'run' yields first real stack
    yield self.stackshot
    latest_output = ""
    while self.running:
      self.send('step')
      self.capture_stack()
      yield self.stackshot

  def run_to_completion(self):
    ''' To be called AFTER debug. '''
    for output in self.step():
      vsdb.runnerStep(output)
    self.terminate()

  def terminate(self):
    self.proc.terminate()
    self.collector.terminate()
    self.output_file.close()
    vsdb.setStep(0)

def main():
  if len(sys.argv) != 2:
    print "Usage: python gdb_runner.py <executable to debug>"
    exit(0)

  runner = GDBRunner(sys.argv[1])
  runner.debug()
  runner.run_to_completion()


if __name__ == "__main__":
    main()
