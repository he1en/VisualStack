DROP TABLE if exists Code;
DROP TABLE if exists StackFrame;
DROP TABLE if exists Assembly;
DROP TABLE if exists StackWordsDelta;
DROP TABLE if exists RegistersDelta;
DROP TABLE if exists LocalVars;
DROP TABLE if exists FnArguments;
DROP TABLE if exists CurrStep;


CREATE TABLE Code(LineNum INT PRIMARY KEY, LineContents TEXT);
CREATE TABLE StackFrame(StepNum INT, StepINum INT, LineNum REFERENCES Code(LineNum), LineContents TEXT, HighestArgAddr TEXT, UNIQUE(StepNum, StepINum));
CREATE TABLE Assembly(StepNum INT, StepINum INT, InstrContents TEXT, FOREIGN KEY(StepNum, StepINum) REFERENCES StackFrame(StepNum, StepINum));
CREATE TABLE StackWordsDelta(StepNum INT, StepINum INT, MemAddr TEXT, MemContents TEXT, FOREIGN KEY(StepNum, StepINum) REFERENCES StackFrame(StepNum, StepINum));
CREATE TABLE RegistersDelta(StepNum INT, StepINum INT, RegName TEXT, RegContents TEXT, FOREIGN KEY(StepNum, StepINum) REFERENCES StackFrame(StepNum, StepINum));
CREATE TABLE LocalVars(StepNum INT, StepINum INT, VarName TEXT, VarValue TEXT, VarAddr TEXT, FOREIGN KEY(StepNum, StepINum) REFERENCES StackFrame(StepNum, StepINum));
CREATE TABLE FnArguments(StepNum INT, StepINum INT, ArgName TEXT, ArgValue TEXT, ArgAddr TEXT, FOREIGN KEY(StepNum, StepINum) REFERENCES StackFrame(StepNum, StepINum));
CREATE TABLE CurrStep(StepNum INT, StepINum INT, FOREIGN KEY(StepNum, StepINum) REFERENCES StackFrame(StepNum, StepINum));

INSERT into CurrStep values (0, 0);
SELECT * FROM CurrStep;

