import os
import pickle
import requests
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive'] # Changed to 'drive' (full access) to allow uploads

def get_drive_service(client_config=None):
    """
    Authenticates the user and returns a Google Drive service object.
    If client_config is provided (as a dict), it uses that.
    Otherwise, it looks for 'google_auth' in st.secrets or 'credentials.json' on disk.
    """
    creds = None
    token_path = 'token.pickle'

    # 1. Resolve configuration
    if client_config is None:
        # Try Streamlit secrets first
        try:
            client_config = st.secrets.get("google_auth")
        except Exception:
            client_config = None

    # 2. Try loading existing token for OAuth (if not a service account)
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # 3. Authenticate
    if not creds or not creds.valid:
        # Check if it's a Service Account (has client_email)
        if client_config and "client_email" in client_config:
            try:
                creds = service_account.Credentials.from_service_account_info(
                    client_config, scopes=SCOPES
                )
            except Exception as e:
                raise ValueError(f"Failed to authenticate with Service Account: {e}")

        # Otherwise, try OAuth flow
        else:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if client_config:
                    # Use the config dict directly from secrets or params
                    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                elif os.path.exists('credentials.json'):
                    # Fallback to local file
                    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                else:
                    raise FileNotFoundError("Google credentials not found. Please upload credentials.json or set st.secrets['google_auth'].")

                # IMPORTANT: run_local_server only works on local machines.
                creds = flow.run_local_server(port=0)

        # Save token for OAuth (Service Accounts don't need token.pickle)
        if not (client_config and "client_email" in client_config):
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def list_public_folder_files(folder_id, api_key):
    url = f"https://www.googleapis.com/drive/v3/files?q='{folder_id}' in parents&key={api_key}&fields=files(id,name)&supportsAllDrives=true&includeItemsFromAllDrives=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {file['name']: file['id'] for file in data.get('files', [])}
    except Exception as e:
        st.error(f"Error listing Google Drive folder: {e}")
        return {}

def get_all_photos_from_weeks(root_folder_id, api_key):
    all_files_map = {}
    url = f"https://www.googleapis.com/drive/v3/files?q='{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'&key={api_key}&fields=files(id,name)&supportsAllDrives=true&includeItemsFromAllDrives=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        folders = response.json().get('files', [])
        for folder in folders:
            if folder['name'].lower().startswith("week "):
                folder_id = folder['id']
                files_in_folder = list_public_folder_files(folder_id, api_key)
                all_files_map.update(files_in_folder)
    except Exception as e:
        st.error(f"Error scanning Google Drive sub-folders: {e}")
    return all_files_map

def download_public_file(file_id, api_key, destination_path):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={api_key}"
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(destination_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True, None
    except Exception as e:
        return False, str(e)

def list_drive_folder_files(service, folder_id):
    query = f"'{folder_id}' in parents"
    try:
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        items = results.get('files', [])
        return {file['name']: file['id'] for file in items}
    except Exception as e:
        st.error(f"Error listing Drive folder: {e}")
        return {}

def get_all_photos_from_weeks_oauth(service, root_folder_id):
    all_files_map = {}
    query = f"'{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'"
    try:
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        folders = results.get('files', [])
        for folder in folders:
            if folder['name'].lower().startswith("week "):
                folder_id = folder['id']
                files_in_folder = list_drive_folder_files(service, folder_id)
                all_files_map.update(files_in_folder)
    except Exception as e:
        st.error(f"Error scanning Drive sub-folders: {e}")
    return all_files_map

def download_drive_file(service, file_id, destination_path):
    import io
    from googleapiclient.http import MediaIoBaseDownload
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(destination_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return True, None
    except Exception as e:
        return False, str(e)

def create_drive_folder(service, folder_name, parent_id=None):
    """
    Creates a folder in Google Drive and returns its ID.
    """
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]

    try:
        folder = service.files().create(body=file_metadata, fields='id', supportsAllDrives=True).execute()
        return folder.get('id')
    except Exception as e:
        st.error(f"Error creating folder {folder_name}: {e}")
        return None

def upload_drive_file(service, local_path, folder_id, file_name):
    """
    Uploads a file to a specific Google Drive folder.
    """
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    try:
        media = MediaFileUpload(local_path, resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()
        return True, file.get('id')
    except Exception as e:
        return False, str(e)
