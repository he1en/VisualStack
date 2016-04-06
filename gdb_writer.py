import subprocess
from multiprocessing import Process
import sys
import os

def output_poll_and_write(read_handle, write_handle):
    print "in func", read_handle, write_handle
    for line in read_handle.readlines():
        print line
        write_handle.write(line)
        write_handle.flush()

def debug(file_to_debug):
    output_file = open('output_' + file_to_debug, 'w')
    proc = subprocess.Popen(['gdb', file_to_debug], stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
#    writer = Process(target=output_poll_and_write, args=(proc.stdout, output_file))
 #   writer.start()
    #output_file.write(proc.stdout.readline())
    fd = proc.stdout.fileno()
    print os.fstat(fd)
    print os.read(fd, 1000)
    print os.fstat(fd)
    print os.read(fd, 1000)
    print os.fstat(fd)
    print proc.stdout.readline()
    proc.stdin.write('b main\n')
    print os.fstat(fd)
  #  output_file.write('b main\n(gdb) ')
    proc.stdin.write('run\n')
#    while proc.poll() is None:
    for i in range(20):
       #output_file.write(last_output)
        proc.stdin.write('info frame\n') 
        proc.stdin.write('step\n')
        print "step"
   # writer.join()


def main():
    if len(sys.argv) != 2:
        print "Usage: python gdb_writer.py <executable to debug>"
        exit(0)
    
    debug(sys.argv[1])


if __name__ == "__main__":
    main()
