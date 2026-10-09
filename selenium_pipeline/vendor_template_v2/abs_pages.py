from pypdf import PdfReader, PdfWriter

input_file = "source_orig.pdf"
output_file = "problems.pdf"

pini = 5
plast = 9

reader = PdfReader(input_file)
writer = PdfWriter()

# PDF pages in pypdf are 0-indexed, so page 1 -> index 0
for page_num in range(pini - 1, plast):
    writer.add_page(reader.pages[page_num])

with open(output_file, "wb") as f:
    writer.write(f)

print(f"Saved pages {pini} to {plast} from '{input_file}' into '{output_file}'")
