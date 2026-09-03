import os
import pickle
import requests
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service(credentials_json_content=None):
    """
    Authenticates the user and returns a Google Drive service object.
    If credentials_json_content is None, it looks for 'credentials.json' on disk.
    """
    creds = None
    token_path = 'token.pickle'

    # 1. Try loading existing token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # 2. If no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Handle provided content or look for local file
            if credentials_json_content:
                with open('credentials.json', 'w') as f:
                    f.write(credentials_json_content)
            elif not os.path.exists('credentials.json'):
                raise FileNotFoundError("credentials.json not found in project root.")

            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            # For Streamlit, we use run_local_server which opens a browser window
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def list_public_folder_files(folder_id, api_key):
    """
    Lists all files in a public Google Drive folder.
    Supports Shared Drives.
    Returns a dictionary of {filename: file_id}.
    """
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
    """
    Finds 'Week 1', 'Week 2', 'Week 3', 'Week 4' folders inside the root folder
    and collects all files from them into a single map.
    Supports Shared Drives.
    """
    all_files_map = {}

    # 1. Find the sub-folders first
    url = f"https://www.googleapis.com/drive/v3/files?q='{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'&key={api_key}&fields=files(id,name)&supportsAllDrives=true&includeItemsFromAllDrives=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        folders = response.json().get('files', [])

        # 2. For each folder, if it matches "Week X", list its files
        for folder in folders:
            folder_name = folder['name']
            if folder_name.lower().startswith("week "):
                folder_id = folder['id']
                files_in_folder = list_public_folder_files(folder_id, api_key)
                all_files_map.update(files_in_folder)

    except Exception as e:
        st.error(f"Error scanning Google Drive sub-folders: {e}")

    return all_files_map

def download_public_file(file_id, api_key, destination_path):
    """
    Downloads a public file from Google Drive.
    Supports Shared Drives.
    """
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
    """
    Lists all files in a Google Drive folder using the authenticated service.
    Returns a dictionary of {filename: file_id}.
    """
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
    """
    Finds 'Week 1', 'Week 2', 'Week 3', 'Week 4' folders and collects files.
    """
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
    """
    Downloads a file from Google Drive using the authenticated service.
    """
    import io
    from googleapiclient.http import MediaIoBaseDownload

    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(destination_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return True, None
    except Exception as e:
        return False, str(e)
