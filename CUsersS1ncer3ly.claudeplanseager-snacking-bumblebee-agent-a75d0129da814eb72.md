# Implementation Plan: Service Account Authentication for Google Drive

## Overview
The goal is to replace the OAuth-based authentication (which requires a browser for login) with Service Account authentication to enable seamless operation on Streamlit Cloud. We will maintain backward compatibility for local developers using `credentials.json`.

## Requirements
- Support Service Account JSON keys via `st.secrets`.
- Backward compatibility for local `credentials.json`.
- Ensure `drive_service` compatibility with all existing functions.
- Plug-and-play for Streamlit Cloud.

## Technical Design

### 1. `core/utils/google_drive.py` Modifications
The `get_drive_service` function will be updated to handle two distinct authentication paths:

- **Service Account Path**: Triggered if `client_config` is provided and contains a `client_email`. This is the preferred method for cloud deployments.
- **OAuth Path**: The existing logic using `InstalledAppFlow` and `token.pickle`. This remains for local development.

**Changes:**
- Import `service_account` from `google.oauth2`.
- Logic update in `get_drive_service`:
    ```python
    if client_config and "client_email" in client_config:
        # Service Account Authentication
        creds = service_account.Credentials.from_service_account_info(
            client_config, scopes=SCOPES
        )
    else:
        # Existing OAuth Flow (token.pickle -> InstalledAppFlow)
        # ... (current implementation)
    ```
- This ensures the `build('drive', 'v3', credentials=creds)` call receives valid credentials regardless of the method.

### 2. `app.py` Modifications
Minor UI and error message updates to reflect the change in authentication capabilities.

- **UI Change**: Change the "Photo Source" radio option from `"Google Drive (OAuth)"` to `"Google Drive"`.
- **Error Message**: Update the guidance for missing credentials to explicitly mention Service Account keys in Streamlit Secrets.

### 3. Streamlit Secrets Format
The user will provide the Service Account JSON key as a TOML table in `st.secrets`.

**Format:**
```toml
[google_auth]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR-KEY-HERE\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

### 4. User Instructions (Setup Guide)
The user must follow these steps to enable the Service Account:

1. **Create Service Account**:
    - Go to [Google Cloud Console](https://console.cloud.google.com/).
    - Select your project -> **IAM & Admin** -> **Service Accounts**.
    - Click **Create Service Account**, name it (e.g., "portfolio-generator"), and assign the **Editor** role (or specific Drive roles).
2. **Generate JSON Key**:
    - Select the newly created Service Account -> **Keys** tab -> **Add Key** -> **Create new key** -> **JSON**.
    - Download the file.
3. **Configure Streamlit Secrets**:
    - Open the downloaded JSON file.
    - Copy its contents into the Streamlit Cloud Secrets dashboard under the `[google_auth]` header as shown in the TOML format above.
4. **Share Drive Folder (CRITICAL)**:
    - The Service Account does not have access to the user's personal Drive files by default.
    - Copy the `client_email` from the JSON key.
    - Open the Google Drive folder containing the student photos.
    - Click **Share** and add the `client_email` as an **Editor**.

## Implementation Steps
1. Update `core/utils/google_drive.py` with the dual-auth logic.
2. Update `app.py` UI labels and error messages.
3. Verify that `list_drive_folder_files` and `upload_drive_file` still work (they use the `service` object, which remains consistent).
PLAN_EOF`
