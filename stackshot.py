########################################
# Stack Shot Class
# 
########################################

class StackShot:

  def __init__(self):
    self.line = None  # String, last line number
    self.rsp = None
    self.rbp = None
    self.words_below = []
    self.words_above = []
    
  def stringify(self):
    return self.line

  def ingest_step(self, new_data):
    last_line = new_data.split('\n')[-2] # actual last line is (gdb)
    self.line = last_line

       

    # ingestion methods from raw gdb output

    # formatting of register / stack info as different lengths of memory,
    # ptrs, etc
        
