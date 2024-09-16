import random

def create_code(code_len):                      #creates a random join code for an organization
  chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
  code = ""
  for i in range(code_len):
    code += random.choice(chars)
  return code