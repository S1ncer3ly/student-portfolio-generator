import streamlit as st
from googleapiclient.discovery import build

def get_slides_service(drive_service):
    """
    Uses the credentials from the drive_service to create a Google Slides service.
    """
    return build('slides', 'v1', credentials=drive_service._http.credentials)

def convert_pptx_to_slides(drive_service, file_id, folder_id=None):
    """
    Converts a .pptx file to a Google Slides presentation.
    """
    try:
        file_metadata = {'mimeType': 'application/vnd.google-apps.presentation'}
        if folder_id:
            # Move the new presentation to the specified folder
            # First, remove from current parents
            file = drive_service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            file_metadata['parents'] = [folder_id]

        # Copy the file and convert it
        # Note: copy() doesn't convert. We use the Drive API's 'import' capability by creating a file with the content of the pptx.
        # Actually, the simplest way to convert is to use the drive_service.files().copy() and specify the new mimeType.
        # Wait, copy doesn't change mimeType. The correct way to convert is to upload as mimeType 'application/vnd.google-apps.presentation'.
        # Since the file is already on Drive, we can't just 'convert' it in place.
        # We can use the drive_service.files().copy(fileId=file_id, body={'mimeType': '...'}) if it were supported, but it's not.

        # CORRECT WAY to convert on Drive:
        # Use drive_service.files().copy(fileId=file_id) and then the converted file is usually a copy.
        # Actually, the standard way is to use the Drive API's upload with convert=True.
        # Since we already have the file on Drive, we can use drive_service.files().copy(fileId=file_id)
        # but it keeps the .pptx format.

        # Let's use the workaround:
        # 1. Download .pptx
        # 2. Upload as Google Slides
        # But that's slow.

        # Better way:
        # Use drive_service.files().copy(fileId=file_id) but that won't convert.
        # The Drive API doesn't have a simple 'convert' method for existing files.
        # We must upload the file with mimeType 'application/vnd.google-apps.presentation'.

        # Wait, if the user is okay with the .pptx file being uploaded and then they open it, maybe they don't need the conversion?
        # No, the Slides API requires a Google Slides presentation ID.

        # I will use the "export/import" flow if needed, but let's check if we can use a simpler method.
        # Actually, there's a trick: use the Drive API to copy and specify the destination mimeType in the request if supported? No.

        # Let's use the most reliable method:
        # 1. We have the local temp_pptx.
        # 2. Upload it using drive_service.files().create(..., media_body=..., fields='id')
        #    and set the mimeType in the metadata to 'application/vnd.google-apps.presentation'.

        # I'll modify the upload logic in presentation_generator.py to do this.
        return None
    except Exception as e:
        st.error(f"Conversion failed: {e}")
        return None

def find_placeholder_on_slide(slides_service, presentation_id, slide_index):
    """
    Finds the best candidate for a video placeholder on the specified slide, including inside groups.
    Returns its element properties (size and position).
    """
    try:
        presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
        slides = presentation.get('slides', [])
        if slide_index >= len(slides):
            st.error(f"Slide index {slide_index} is out of bounds for presentation {presentation_id}")
            return None

        slide = slides[slide_index]
        page_elements = slide.get('pageElements', [])

        if not page_elements:
            st.warning(f"No elements found on slide {slide_index + 1}")
            return None

        def search_elements(elements_to_check):
            # Priority 1: Technical placeholders
            for element in elements_to_check:
                if 'placeholder' in element:
                    size = element.get('size', {})
                    st.info(f"Found technical placeholder: {element['objectId']} (Size: {size.get('width')}x{size.get('height')})")
                    return {
                        'objectId': element['objectId'],
                        'size': size,
                        'transform': element.get('transform')
                    }

            # Priority 2: Shapes that might be placeholders but lost the tag
            for element in elements_to_check:
                if 'shape' in element:
                    text_content = ""
                    if 'text' in element['shape']:
                        text_content = str(element['shape'].get('text', ''))
                    if "video" in text_content.lower() or "placeholder" in text_content.lower():
                        size = element.get('size', {})
                        st.info(f"Found shape-based placeholder: {element['objectId']} (Size: {size.get('width')}x{size.get('height')})")
                        return {
                            'objectId': element['objectId'],
                            'size': size,
                            'transform': element.get('transform')
                        }

            # Priority 3: Recurse into groups
            for element in elements_to_check:
                if 'group' in element:
                    child_ids = [c['objectId'] for c in element['group'].get('children', [])]
                    child_elements = [e for e in page_elements if e['objectId'] in child_ids]
                    res = search_elements(child_elements)
                    if res: return res

            return None

        result = search_elements(page_elements)
        if result:
            return result

        # Final Fallback: The largest shape on the slide
        best_candidate = None
        max_area = 0
        for element in page_elements:
            size = element.get('size', {})
            width = size.get('width', 0)
            height = size.get('height', 0)
            area = width * height
            if area > max_area:
                max_area = area
                best_candidate = {
                    'objectId': element['objectId'],
                    'size': size,
                    'transform': element.get('transform')
                }

        if best_candidate:
            st.info(f"No formal placeholder found on slide {slide_index + 1}, using largest shape: {best_candidate['objectId']} (Area: {max_area})")
            return best_candidate

        return None
    except Exception as e:
        st.error(f"Error finding placeholder: {e}")
        return None

def insert_video_at_fixed_coords(slides_service, presentation_id, slide_index, video_file_id, coords):
    """
    Inserts a video from Drive into a slide using fixed coordinates (left, top, width, height).
    Coords are in EMUs (from COORD_MAP).
    Returns (True, None) on success, or (False, error_message) on failure.
    """
    try:
        import uuid
        import traceback
        unique_id = f"video_{uuid.uuid4().hex[:8]}"

        # Coordinate conversion: python-pptx EMUs to Google Slides API units.
        # 1 EMU = 1/914400 inch.
        # Google Slides API 'size' and 'transform' use 'points' (1/72 inch).
        # Conversion factor: EMUs to Points = EMU / (914400 / 72) = EMU / 12700.

        left, top, width, height = coords
        conv = 12700.0

        requests = [{
            'createVideo': {
                'objectId': unique_id,
                'source': 'DRIVE',
                'id': video_file_id,
                'elementProperties': {
                    'size': {
                        'width': {'magnitude': float(width / conv), 'unit': 'PT'},
                        'height': {'magnitude': float(height / conv), 'unit': 'PT'}
                    },
                    'transform': {
                        'scaleX': 1.0,
                        'scaleY': 1.0,
                        'translateX': float(left / conv),
                        'translateY': float(top / conv),
                        'unit': 'PT'
                    }
                }
            }
        }]

        presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
        if slide_index >= len(presentation['slides']):
            return False, f"Slide index {slide_index} is out of bounds (Presentation has {len(presentation['slides'])} slides)"

        slide_id = presentation['slides'][slide_index]['objectId']
        requests[0]['createVideo']['elementProperties']['pageObjectId'] = slide_id

        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()
        return True, None
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return False, f"{str(e)}\n{error_details}"

def insert_video_at_placeholder(slides_service, presentation_id, slide_index, video_file_id):
    """
    Inserts a video from Drive into a slide, matching a placeholder's position and size.
    Returns (True, None) on success, or (False, error_message) on failure.
    """
    placeholder = find_placeholder_on_slide(slides_service, presentation_id, slide_index)
    if not placeholder:
        return False, f"No placeholder found on slide {slide_index + 1}"

    try:
        import uuid
        unique_id = f"video_{uuid.uuid4().hex[:8]}"

        requests = [{
            'createVideo': {
                'objectId': unique_id,
                'source': 'DRIVE',
                'id': video_file_id,
                'elementProperties': {
                    'size': placeholder['size'],
                    'transform': placeholder['transform']
                }
            }
        }]

        presentation = slides_service.presentations().get(presentationId=presentation_id).execute()
        slide_id = presentation['slides'][slide_index]['objectId']
        requests[0]['createVideo']['elementProperties']['pageObjectId'] = slide_id

        slides_service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()
        return True, None
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return False, f"{str(e)}\n{error_details}"
