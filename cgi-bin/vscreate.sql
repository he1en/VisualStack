DROP TABLE if exists StackFrame;
DROP TABLE if exists StackWords;
DROP TABLE if exists CurrStep;

CREATE TABLE StackFrame(StepNum INT PRIMARY KEY, LineContents TEXT, RSP TEXT, RBP TEXT, RAX TEXT, RBX TEXT, RCX TEXT, RDX TEXT, RSI TEXT, RDI TEXT, R8 TEXT, R9 TEXT, R10 TEXT, R11 TEXT, R12 TEXT, R13 TEXT, R14 TEXT, R15 TEXT);
CREATE TABLE StackWords(StepNum REFERENCES StackFrame(StepNum), MemAddr TEXT, MemContents TEXT);
CREATE TABLE CurrStep(StepNum REFERENCES StackFrame(StepNum));

INSERT into CurrStep values (0);
SELECT StepNum FROM CurrStep;

