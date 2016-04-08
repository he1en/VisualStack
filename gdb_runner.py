import subprocess
import multiprocessing
import sys
import os
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
    self.collect_output()

  def collect_output(self):
    output = ''
    while "(gdb)" not in output:
      output += self.output_queue.get()
      if "program is not being run" in output:
        self.running = False

    self.output_file.write(output)
    self.stackshot.ingest_step(output)

  def send(self, command):
    self.output_file.write(command + '\n')
    self.proc.stdin.write(command + '\n')
    self.collect_output()

  def read_gdb_output(self, read_fd):
    while True:
      content = os.read(read_fd, 1000)
      self.output_queue.put(content)

  def debug(self):
    self.running = True
    self.send('b main')
    self.send('run')

  def step(self):
    # hacky? 'run' yields first real stack
    yield self.stackshot.stringify()
    latest_output = ""
    while self.running:
      self.send('step')
      yield self.stackshot.stringify()

  def run_to_completion(self):
    ''' To be called AFTER debug. '''
    for output in self.step():
      print output
    self.terminate()

  def terminate(self):
    self.proc.terminate()
    self.collector.terminate()
    self.output_file.close()


def main():
  if len(sys.argv) != 2:
    print "Usage: python gdb_runner.py <executable to debug>"
    exit(0)

  runner = GDBRunner(sys.argv[1])
  runner.debug()
  runner.run_to_completion()


if __name__ == "__main__":
    main()



    
