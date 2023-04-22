from file import instructor, coder, writer, calculator, illustrator, researcher


def executor(instructions, prompt):
    # create a file to write the instructions to 
    with open(f'{prompt}.txt', 'w') as f:
      for i, instruction in enumerate(instructions):
          print(str(i) +". " + instruction['label'] +": " + instruction['instruction'] + "\n" + "Dependencies: " + str(instruction['dependencies']))
          f.write(str(i) +". " + instruction['label'] +": " + instruction['instruction'] + "\n" + "Dependencies: " + str(instruction['dependencies']) + "\n")
          if instruction['label'] == 'CALCULATE':
              try: 
                  print('Starting to load the calculator script')
                  answer = calculator(i, instructions)
                  print('Ending to load the calculator script')
                  f.write(answer)
                  print(answer)
                  instruction['response'] = answer
              except Exception as e:
                  print(f'Error in calculator: {e}')
                  instruction['response'] = 'Error'
                  f.write('Error')
          elif instruction['label'] == 'WRITE':
              try:
                  print('Starting to load the writer script')
                  answer = writer(i, instructions)
                  print('Ending to load the writer script')
                  f.write(answer)
                  print(answer)
                  instruction['response'] = answer
              except Exception as e:
                  print(f'Error in writer: {e}')
                  instruction['response'] = 'Error'
                  f.write('Error')
          elif instruction['label'] == 'CODE':
              try:
                  print('Starting to load the coder script')
                  answer = coder(i, instructions)
                  print('Ending to load the coder script')
                  f.write(answer)
                  print(answer)
                  instruction['response'] = answer
              except Exception as e:
                  print(f'Error in coder: {e}')
                  instruction['response'] = 'Error'
                  f.write('Error')
          elif instruction['label'] == 'ILLUSTRATE':
              try:
                  print('Starting to load the illustrator script')
                  answer = illustrator(i, instructions)
                  print('Ending to load the illustrator script')
                  f.write(answer)
                  print(answer)
                  instruction['response'] = answer
              except Exception as e:
                  print(f'Error in illustrator: {e}')
                  instruction['response'] = 'Error'
                  f.write('Error')
          elif instruction['label'] == 'RESEARCH':
              try:
                  print('Starting to load the researcher script')
                  answer = researcher(i, instructions)
                  print('Ending to load the researcher script')
                  f.write(answer)
                  print(answer)
                  instruction['response'] = answer
              except Exception as e:
                  print(f'Error in researcher: {e}')
                  instruction['response'] = 'Error'
                  f.write('Error')
          else:
              print(f'Error: Unknown instruction label - {instruction["label"]}')
              instruction['response'] = 'Error'
              f.write('Error')
          print('\n')
          f.write('\n')
    f.close()
    return instructions


if __name__ == "__main__":
    prompt = """write a research project on the implications of LLM technology on american society."""
    instructions = instructor(prompt)
    for instruction in instructions:
        print(instruction['label'] + ': ' + instruction['instruction'] + '\n' + 'Dependencies: ' + str(instruction['dependencies']))
    executor(instructions, prompt)