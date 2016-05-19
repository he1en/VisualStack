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
CREATE TABLE StackFrame(StepINum INT PRIMARY KEY, StepNum INT, LineNum REFERENCES Code(LineNum), LineContents TEXT, InstrIndex INT, HighestArgAddr TEXT, UNIQUE(StepINum, StepNum));
CREATE TABLE StackWordsDelta(StepINum REFERENCES StackFrame(StepINum), MemAddr TEXT, MemContents TEXT);
CREATE TABLE RegistersDelta(StepINum REFERENCES StackFrame(StepINum), RegName TEXT, RegContents TEXT);
CREATE TABLE LocalVars(StepINum REFERENCES StackFrame(StepINum), VarName TEXT, VarValue TEXT, VarAddr TEXT);
CREATE TABLE FnArguments(StepINum REFERENCES StackFrame(StepINum), ArgName TEXT, ArgValue TEXT, ArgAddr TEXT);
CREATE TABLE CurrStep(StepINum INT, StepNum INT, FOREIGN KEY(StepINum, StepNum) REFERENCES StackFrame(StepINum, StepNum));

INSERT into CurrStep values (0, 0);
SELECT * FROM CurrStep;

