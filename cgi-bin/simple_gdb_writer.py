import subprocess
from multiprocessing import Process
import sys
import os


class GDBWriter:
  def __init__(self, filename):
    self.filename = filename
    self.write = None
    self.proc = None

  def read_gdb_output(self, read_fd):
    print "here"
    content = ""
    while "The program is not being run" not in content:
      content = os.read(read_fd, 1000)
      print content

  def debug(self):
    output_file = open('output_' + self.filename, 'w')
    self.proc = subprocess.Popen(['gdb', self.filename], stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    fd = self.proc.stdout.fileno()
    self.writer = Process(target=self.read_gdb_output, args=[fd])
    self.writer.start()
    self.proc.stdin.write('b main\n')
    self.proc.stdin.write('run\n')
    #for i in range(150):
    #self.proc.stdin.write('frame\n') 
    #self.proc.stdin.write('next\n')
    #self.writer.join()

  def step(self):
    self.proc.stdin.write('frame\n')
    self.proc.stdin.write('next\n')

