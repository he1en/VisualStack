DROP TABLE if exists Code;
DROP TABLE if exists Assembly;
DROP TABLE if exists StackFrame;
DROP TABLE if exists StackWordsDelta;
DROP TABLE if exists RegistersDelta;
DROP TABLE if exists LocalVars;
DROP TABLE if exists FnArguments;
DROP TABLE if exists CurrStep;


CREATE TABLE Code(LineNum INT PRIMARY KEY, LineContents TEXT);
CREATE TABLE Assembly(CLineNum REFERENCES Code(LineNum), InstrLineNum INT, InstrContents TEXT, UNIQUE(CLineNum, InstrLineNum));
CREATE TABLE StackFrame(StepNum INT PRIMARY KEY, LineNum REFERENCES Code(LineNum), LineContents TEXT, InstrIndex INT, HighestArgAddr TEXT);
CREATE TABLE StackWordsDelta(StepNum REFERENCES StackFrame(StepNum), MemAddr TEXT, MemContents TEXT);
CREATE TABLE RegistersDelta(StepNum REFERENCES StackFrame(StepNum), RegName TEXT, RegContents TEXT);
CREATE TABLE LocalVars(StepNum REFERENCES StackFrame(StepNum), VarName TEXT, VarValue TEXT, VarAddr TEXT);
CREATE TABLE FnArguments(StepNum REFERENCES StackFrame(StepNum), ArgName TEXT, ArgValue TEXT, ArgAddr TEXT);
CREATE TABLE CurrStep(StepNum REFERENCES StackFrame(StepNum));

INSERT into CurrStep values (0);
SELECT StepNum FROM CurrStep;

