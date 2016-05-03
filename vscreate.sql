DROP TABLE if exists Code;
DROP TABLE if exists StackFrame;
DROP TABLE if exists StackWords;
DROP TABLE if exists Changes;
DROP TABLE if exists FnArguments;
DROP TABLE if exists CurrStep;

CREATE TABLE Code(LineNum INT PRIMARY KEY, LineContents TEXT);
CREATE TABLE StackFrame(StepNum INT PRIMARY KEY, LineNum REFERENCES Code(LineNum), LineContents TEXT, HighestArgAddr TEXT, RSP TEXT, RBP TEXT, RAX TEXT, RBX TEXT, RCX TEXT, RDX TEXT, RSI TEXT, RDI TEXT, R8 TEXT, R9 TEXT, R10 TEXT, R11 TEXT, R12 TEXT, R13 TEXT, R14 TEXT, R15 TEXT);
CREATE TABLE StackWords(StepNum REFERENCES StackFrame(StepNum), MemAddr TEXT, MemContents TEXT);
CREATE TABLE Changes(StepNum REFERENCES StackFrame(StepNum), ChangeType TEXT, ChangeAddr TEXT);
CREATE TABLE FnArguments(StepNum REFERENCES StackFrame(StepNum), ArgName TEXT, ArgValue TEXT, ArgAddr TEXT);
CREATE TABLE CurrStep(StepNum REFERENCES StackFrame(StepNum));

INSERT into CurrStep values (0);
SELECT StepNum FROM CurrStep;

