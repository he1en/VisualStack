# VisualStack
Visual education tool for students learning about C, assembly, and how the stack works.

## About VisualStack
VisualStack is designed to serve the students and instructors of **CS107: Computer Organization and Systems** at Stanford University. As such, this document will describe how to use VisualStack within the context of the Stanford [myth cluster](https://web.stanford.edu/class/cs107/guide_editors.html). The machines in the myth cluster are 64-bit and run Ubuntu 14. In order to cater to the needs of **CS107**, VisualStack compiles using the `-Og` flag and only shows red-zone contents when they are directly touched by assembly instructions (typically in leaf functions).

We plan to release an open source version of VisualStack which will be usable outside of this limited context. However, such a version is not available at this time.

### How To Run VisualStack
VisualStack is designed to run on **myth**. To launch, run
```
ssh sunetid@myth.stanford.edu
```
Enter your credentials when prompted. This will log you into one of the myth machines, myth##.
Next, invoke
```
bash /afs/ir/class/cs107/tools/visualstack.sh <filename>.c
```

VisualStack may take a few seconds to run. Eventually, your terminal should output http://0.0.0.0:8080/. At this time, point your browser to [myth##.stanford.edu:8080/visualstack](myth##.stanford.edu:8080/visualstack). You will see the code, registers, and stack for `<filename>.c` in the browser and may interact with it directly there.

## How It Works

When you run the VisualStack bash script, a few things happen. First, `vscreate.sql` is invoked, which sets up tables in an SQLite database (`VisualStack.db`). Next, `vsbase`, which is the **web2py** controller, is launched at port 8080. Upon start up, `vsbase` prompts the `gdb` pipeline; this pipeline must complete in order for you to be able to see anything meaningful in the web client. Once it has completed, you will be able to interact with the web interface, which allows stepping forwards or backwards through the code either by source line or by assembly instruction.

The `gdb` pipeline is made up of several parts: `gdb_runner`, `gdb_parser`, and of course `gdb` itself. The `gdb_runner` module is responsible for managing the `gdb` subprocess by feeding it commands as input and managing its output, which it handles in two ways: first, by writing all string output directly into an output file and second, by passing the same string output to the `gdb_parser` module. Upon receipt, `gdb_parser` parses out the meaning of each output string and uses these discovered states to populate an instance of the `stackshot` object.

`stackshot` is a pythonic object representation of the state of the stack during a given instruction step in `gdb`. It is the object parallel to the data stored in various database tables, namely: `StackFrame`, `StackWordsDelta`, `RegistersDelta`, `LocalVars`, and `FnArguments`. Each `stackshot` instance generated by `gdb_parser` is writen to the database using the `vsdb` module. The `stackshot` object is also used by the `vsbase` action handlers since upon each step, the relevant `stackshot` is hydrated from the databases by `vsdb` so that it can be passed to the client using `jinja2` templating and rendered.

## Built With

* jinja2
* web2py
* sqlite3
* gdb

## Authors

* [**Helen Hastings**](https://github.com/he1en) is a senior at Stanford University pursuing a Bachelor's of Science in Computer Science with a concentration in Systems. She is a current Co-Director of she++, a nonprofit that works to encourage and empower young women in technology. Helen is also the Professional Development Co-Chair of the Tau Beta Pi Engineering Honors Society. In September, Helen will be starting as a Software Engineer at Affirm, a financial tech company based in San Francisco.
* [**Rachel Mellon**](https://github.com/rbmellon) is a senior at Stanford University pursuing a Bachelor's of Science in Computer Science with a concentration in Information and a minor in Spanish. Rachel is a former Co-Director of she++ and a current Co-Director of the she++ ThinkTank project. She is a member of Sigma Delta Pi, an honors society for the study of Hispanic language and culture. In October, Rachel will be starting as a Software Engineer at Google in Mountain View, CA.

## Acknowledgments

Special thanks to:
* [Jerry Cain](https://github.com/jerrycainjr), for advising the project team
* The CS107 teaching staff, for their support & guidance
