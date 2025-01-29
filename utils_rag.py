import base64
from IPython.display import Image, display
import fitz
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from PIL import Image as Image2 
from langchain_core.documents import Document

from unstructured.partition.pdf import partition_pdf
from unstructured.staging.base import dict_to_elements, elements_to_json
import json


def display_base64_image(base64_code):
    # Decode the base64 string to binary
    image_data = base64.b64decode(base64_code)
    # Display the image
    display(Image(data=image_data))


def data_general(chunks):
    # separate tables from texts
    tables = []
    texts = []
    images_b64 = []
    for chunk in chunks:
        if "Table" in str(type(chunk)):
            tables.append(chunk)

        if "CompositeElement" in str(type((chunk))):
            texts.append(chunk)
            chunk_els = chunk.metadata.orig_elements
            for el in chunk_els:
                if "Image" in str(type(el)):
                    images_b64.append(el.metadata.image_base64)
    
    return tables, texts, images_b64



def plot_pdf_with_boxes(pdf_page, segments) :
  pix = pdf_page.get_pixmap()
  pil_image = Image2.frombytes ("RGB", [pix.width, pix.height], pix.samples)
  fig, ax = plt.subplots(1, figsize=(10, 10))
  ax. imshow (pil_image)
  categories = set()
  category_to_color = {
      'Title': 'blue',
      'Image': 'green',
      'Table': 'red',
  }
  for segment in segments:
    points = segment ["coordinates"] ["points"]
    layout_width = segment ["coordinates"] ["layout_width"]
    layout_height = segment ["coordinates" ] ["layout_height"]
    scaled_points = [
        (x * pix.width / layout_width, y * pix.height / layout_height)
        for x, y in points
        ]
    box_color = category_to_color.get(segment["category"], "deepskyblue")
    categories.add(segment["category"])
    rect = patches.Polygon(scaled_points, linewidth=1, edgecolor=box_color, facecolor="none")
    ax.add_patch(rect)

  # Make legend
  legend_handles = [patches.Patch(color="deepskyblue", label="Text" )]
  for category in ["Title", "Image", "Table"]:
    if category in categories:
      legend_handles.append(
          patches.Patch(color=category_to_color[category], label=category)
      )
  ax.axis("off")
  ax.legend(handles=legend_handles, loc="upper right")
  plt.tight_layout()
  plt.show()

def render_page(doc_list: list, page_number: int,file_path, print_text=True) -> None:

  pdf_page = fitz.open(file_path).load_page(page_number - 1)
  page_docs = [
      doc for doc in doc_list if doc.metadata.get ("page_number") == page_number
  ]
  segments = [doc.metadata for doc in page_docs]
  plot_pdf_with_boxes(pdf_page, segments)
  if print_text:
    for doc in page_docs:
      print(f"{doc. page_content}\n" )


from langchain_core.documents import Document

def extract_page_numbers_from_chunks(chunk):
  
  elements = chunk.metadata.orig_elements
  page_numbers = set()

  for element in elements:
    page_numbers.add(element.metadata.page_number)
  
  return page_numbers

def display_chunk_pages(chunk,file_path):
  
  
  page_numbers = extract_page_numbers_from_chunks(chunk)
  
  docs = []

  for element in chunk.metadata.orig_elements:
    metadata = element.metadata.to_dict()
    if "Table" in str(type(element)):
      metadata["category"] = "Table"
    elif "Image" in str(type(element)):
      metadata["category"] = "Image"
    else:
      metadata["category"] = "Text"

    metadata["page_number"] = element.metadata.page_number

    docs.append(Document(page_content=element.text, metadata=metadata))

  for page_number in page_numbers:
    render_page(docs, page_number,file_path, False)


def ejecutar_chunking_pdf(dict_pdfs,ejecutar_pdf=False):
    
    if ejecutar_pdf:
        output_path = "data/"

        chunks = partition_pdf(
            filename=dict_pdfs['file_path'],
            infer_table_structure=True,            # extract tables
            strategy="hi_res",                     # mandatory to infer tables

            extract_image_block_types=["Image"],   # Add 'Table' to list to extract image of tables
            image_output_dir_path=output_path,   # if None, images and tables will saved in base64

            extract_image_block_to_payload=True,   # if true, will extract base64 for API usage

            chunking_strategy="by_title",          # or 'basic'
            max_characters=10000,                  # defaults to 500
            combine_text_under_n_chars=2000,       # defaults to 0
            new_after_n_chars=6000,

            # extract_images_in_pdf=True,          # deprecated
        )

        json_data = elements_to_json(chunks)

        
        with open(dict_pdfs['output_path'], 'w', encoding='utf-8') as f:
            f.write(json_data)

    else:
        with open(dict_pdfs['output_path'], 'r', encoding='utf-8') as f:
            json_data = f.read()

        # Convertir la cadena JSON en una lista de diccionarios
        element_dicts = json.loads(json_data)

        # Verificar que element_dicts es una lista de diccionarios
        if isinstance(element_dicts, list) and all(isinstance(d, dict) for d in element_dicts):
            # Convertir los diccionarios en elementos utilizando dict_to_elements
            chunks = dict_to_elements(element_dicts)
        else:
            raise ValueError("El contenido del archivo JSON no es una lista de diccionarios válida.")

    return chunks




def extract_text_with_page_mapping(chunks):
    """
    Extrae únicamente el texto de los chunks y mapea cada fragmento al número de página correspondiente.

    Args:
        chunks: Lista de elementos generados por ejecutar_chunking_pdf.

    Returns:
        List[Dict]: Lista de diccionarios con 'text' y 'page_number'.
    """
    text_chunks = []
    tables_html_chunks = []
    images_b64_chunks = []
    if len(chunks) > 0:
        file_name_pdf = chunks[0].to_dict()['metadata']['filename']


    for chunk in chunks:
        # Verificar si el chunk es un CompositeElement
        text_chunk = ''
        if "CompositeElement" in str(type(chunk)):
            for elem in chunk.metadata.orig_elements:
                page_numbers = extract_page_numbers_from_chunks(chunk)
                # Ignorar elementos de tipo Table e Image
                if "Table" not in str(type(elem)) and "Image" not in str(type(elem)):
                    texto = elem.text.strip()
                    text_chunk += texto + '\n'
                elif "Table" in str(type(elem)):
                    # Si el elemento es una tabla o una imagen, extraer los números de página
                    #tables_html_chunks.append(elem.metadata.text_as_html)
                    tables_html_chunks.append({
                            'text_html': elem.metadata.text_as_html,
                            'page_number': page_numbers,
                            'filename': file_name_pdf

                        })
                elif "Image" in str(type(elem)):

                    images_b64_chunks.append(
                        {
                            'images_b64': elem.metadata.image_base64,
                            'page_number': page_numbers,
                            'filename': file_name_pdf
                        }
                        )

            text_chunks.append({
                            'text': text_chunk,
                            'page_number': page_numbers,
                            'filename': file_name_pdf
                        })
            
        else:
            # Si el chunk no es CompositeElement, asumir que es un texto simple
            texto = chunk.text.strip()
            if texto:
                numero_pagina = chunk.metadata.page_number
                text_chunks.append({
                    'text': texto,
                    'page_number': numero_pagina
                })

    return text_chunks, tables_html_chunks, images_b64_chunks