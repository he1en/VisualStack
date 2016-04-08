import subprocess
import multiprocessing
import sys
import os
import stackshot

def read_gdb_output(read_fd, output_queue):
    while True:
        content = os.read(read_fd, 1000)
        output_queue.put(content)

def debug(file_to_debug):
    output_file = open('output_' + file_to_debug, 'w')
    proc = subprocess.Popen(['gdb', file_to_debug], stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
    fd = proc.stdout.fileno()
    output_queue = multiprocessing.Queue()
    writer = multiprocessing.Process(target=read_gdb_output, args=[fd, output_queue])
    writer.start()

    proc.stdin.write('b main\n')
    proc.stdin.write('run\n')
    latest_output = output_queue.get()
    while "exited normally" not in latest_output:
        print latest_output
        proc.stdin.write('frame\n') 
        proc.stdin.write('next\n')
        latest_output = output_queue.get()
    print latest_output
    writer.terminate()


def main():
    if len(sys.argv) != 2:
        print "Usage: python gdb_writer.py <executable to debug>"
        exit(0)
    
    debug(sys.argv[1])

if __name__ == "__main__":
    main()
