#!/usr/bin/env python3

import os
import io
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.oauth2 import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

def authenticate():
    """Authenticates with Google Drive API."""
    creds = None
    if os.path.exists('token.json'):
        creds = credentials.Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('/home/leo/.ssh/client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_drive_service():
    """Builds and returns the Google Drive API service."""
    creds = authenticate()
    return build('drive', 'v3', credentials=creds)

def get_file_id(service, file_name, parent_id=None):
    """Gets the file ID of a file or directory on Google Drive."""
    query = f"name='{file_name}'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    results = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    files = results.get('files', [])
    if files:
        return files[0].get('id')
    return None

def create_folder(service, folder_name, parent_id=None):
    """Creates a folder on Google Drive."""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
    file = service.files().create(body=file_metadata, fields='id').execute()
    return file.get('id')

def download_file(service, file_id, local_path):
    """Downloads a file from Google Drive."""
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.seek(0)
    with open(local_path, 'wb') as f:
        f.write(fh.read())

def upload_file(service, local_path, file_name, parent_id=None):
    """Uploads a file to Google Drive."""
    file_metadata = {'name': file_name}
    if parent_id:
        file_metadata['parents'] = [parent_id]
    media = MediaFileUpload(local_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def synchronize_directory(service, drive_folder_id, local_dir):
    """Recursively synchronizes a directory between Google Drive and local."""
    local_files = os.listdir(local_dir)
    drive_files = service.files().list(q=f"'{drive_folder_id}' in parents", fields='files(id, name, mimeType)').execute().get('files', [])

    drive_file_map = {f['name']: f for f in drive_files}

    # Download from Drive to Local
    for drive_file in drive_files:
        local_path = os.path.join(local_dir, drive_file['name'])
        if drive_file['mimeType'] == 'application/vnd.google-apps.folder':
            if not os.path.exists(local_path):
                os.makedirs(local_path)
            synchronize_directory(service, drive_file['id'], local_path)
        else:
            if not os.path.exists(local_path) or os.path.getsize(local_path) == 0:
                download_file(service, drive_file['id'], local_path)

    # Upload from Local to Drive
    for local_file in local_files:
        local_path = os.path.join(local_dir, local_file)
        if os.path.isdir(local_path):
            drive_folder_id_local = get_file_id(service, local_file, drive_folder_id)
            if not drive_folder_id_local:
                drive_folder_id_local = create_folder(service, local_file, drive_folder_id)
            synchronize_directory(service, drive_folder_id_local, local_path)
        else:
            if local_file not in drive_file_map:
                upload_file(service, local_path, local_file, drive_folder_id)

def main():
    service = get_drive_service()
    drive_folder_name = 'morbid_merch_images' # Change this to the folder name on Drive
    local_directory = '/home/leo/src/morbid_merch/images' # Change this to your local directory

    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    drive_folder_id = get_file_id(service, drive_folder_name)
    if not drive_folder_id:
        drive_folder_id = create_folder(service, drive_folder_name)

    synchronize_directory(service, drive_folder_id, local_directory)
    print("Synchronization complete.")

if __name__ == '__main__':
    main()
