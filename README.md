# VisualStack
Visual education tool for students learning about C and how the stack works.

## How It Works

[Describe here how our infrastructure is set up.]

## Getting Started
VisualStack is designed to serve the students and instructors of **CS107: Computer Organization and Systems** at Stanford University. As such, this document will describe how to use VisualStack within the context of the Stanford [myth cluster](https://web.stanford.edu/class/cs107/guide_editors.html).

In the long term, we plan to release an open source version of VisualStack which will be usable outside of this limited context. However, such a version is not available at this time.

### How To Run VisualStack
Visual Stack is designed to run on **myth**. To launch, run:
```
ssh sunetid@myth.stanford.edu
```

Enter your credentials when prompted. This will log you into one of the myth machines, myth##.
Next, invoke:

```
bash /afs/ir/class/cs107/tools/visualstack.sh <filename>.c
```

VisualStack may take a few seconds to run. Eventually, your terminal should output http://00.00.00. At this time, point your browser to [myth##.stanford.edu:8080/visualstack](myth##.stanford.edu:8080/visualstack). You should see your stack in the browser and may interact with it directly there.

## Built With

* jinja2
* web2py
* sqlite3
* gdb

## Authors

* **Helen Hastings** is a senior at Stanford University pursuing a Bachelor's of Science in Computer Science with a concentration in Systems. She is a current Co-Director of she++, a nonprofit that works to encourage and empower young women in technology. Helen is also the Professional Development Co-Chair of the Tau Beta Pi Engineering honors society. In September, Helen will be starting as a Software Engineer at Affirm, a financial tech company based in San Francisco.
* **Rachel Mellon** is a senior at Stanford University pursuing a Bachelor's of Science in Computer Science with a concentration in Information and a minor in Spanish. Rachel is a former Co-Director of she++ and a current Co-Director of the she++ ThinkTank project. She is a member of Sigma Delta Pi, an honors society for the study of Hispanic language and culture. In October, Rachel will be starting as a Software Engineer at Google in Mountain View, CA.

## Acknowledgments

Special thanks to:
* Jerry Cain, for advising the project
* The CS107 Teaching Staff

