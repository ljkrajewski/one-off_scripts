#!/usr/bin/env python3
"""
embed_image.py
Usage: embed_image.py <image_file>

Converts a PNG image to a data:image/png URI, then wraps it inside an HTML template.

Requires pillow ($ pip install pillow)
"""

import base64
from PIL import Image
import sys
import os

def convert_to_data_uri(image_path):
  """
  Converts a PNG image to a data:image/png URI.

  Args:
      image_path: Path to the PNG image file.

  Returns:
      A string containing the data:image/png URI.
  """
  with open(image_path, "rb") as image_file:
    image_data = image_file.read()
  base64_encoded_data = base64.b64encode(image_data).decode("utf-8")
  return f"data:image/png;base64,{base64_encoded_data}"

def create_html_template(image_uri):
  """
  Creates a basic HTML template with the image embedded using the data URI.

  Args:
      image_uri: The data URI of the image.

  Returns:
      A string containing the HTML code.
  """
  html_template = f"""
<!DOCTYPE html>
<html>
<head>
  <title>Embedded Image</title>
</head>
<body>
  <img src="{image_uri}" alt="Embedded Image">
</body>
</html>
"""
  return html_template

def main():
  """
  Main function that reads the image path from command line,
  converts it to data URI, creates the HTML template, and writes it to a file.
  """
  if len(sys.argv) != 2:
    print("Usage: python embed_image.py <image_path>")
    sys.exit(1)

  image_path = sys.argv[1]
  filename, _ = os.path.splitext(image_path)  # Separate filename and extension
  output_file = f"{filename}.html"


  image_uri = convert_to_data_uri(image_path)
  html_content = create_html_template(image_uri)
  with open(output_file, "w") as f:
    f.write(html_content)

  print(f"HTML file with embedded image created: {output_file}")

if __name__ == "__main__":
  main()
