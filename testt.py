import subprocess

input_file = "test_file.pdf"
output_file = "test_file.pdf"

process = subprocess.Popen(["ocrmypdf", "--force-ocr", input_file, output_file], stderr=subprocess.PIPE)
for line in iter(process.stderr.readline, b""):
    update = line.decode("utf-8").split()
    if len(update):
        print('update[0]', update[0])
process.communicate()
