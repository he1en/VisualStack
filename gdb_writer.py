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


def read_gdb_output(read_fd):
    print "here"
    content = ""
    while "The program is not being run" not in content:
        content = os.read(read_fd, 1000)
        print content

def debug(file_to_debug):
    output_file = open('output_' + file_to_debug, 'w')
    proc = subprocess.Popen(['gdb', file_to_debug], stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    fd = proc.stdout.fileno()
    writer = Process(target=read_gdb_output, args=[fd])
    writer.start()
    proc.stdin.write('b main\n')
    proc.stdin.write('run\n')
#    while proc.poll() is None:
    for i in range(150):
        proc.stdin.write('frame\n') 
        proc.stdin.write('next\n')
    writer.join()


def main():
    if len(sys.argv) != 2:
        print "Usage: python gdb_writer.py <executable to debug>"
        exit(0)
    
    debug(sys.argv[1])


if __name__ == "__main__":
    main()
