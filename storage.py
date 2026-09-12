"""
ClassCatch Storage Abstraction Layer
Provides unified file storage for PDFs, images, lecture notes, lab manuals, and PYQs.
Ensures zero binary BLOB storage inside Neon PostgreSQL.
Supports Local Filesystem Storage and S3 / Object Storage via standard configuration.
"""
import os
import uuid
import mimetypes
from abc import ABC, abstractmethod
from werkzeug.utils import secure_filename
from models import db, StorageFile

# Security configurations: Whitelist safe academic file extensions
ALLOWED_EXTENSIONS = {
    'pdf', 'png', 'jpg', 'jpeg', 'webp', 'gif',
    'docx', 'doc', 'pptx', 'ppt', 'xlsx', 'xls', 'txt', 'zip'
}

# Explicitly blocked dangerous/executable formats
BLOCKED_EXTENSIONS = {
    'exe', 'bat', 'cmd', 'ps1', 'sh', 'bin', 'msi', 'com',
    'js', 'vbs', 'pif', 'scr', 'jar', 'apk', 'py', 'php', 'dll'
}

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB limit


def is_allowed_file(filename: str) -> bool:
    """Check if the filename has an allowed extension and is not dangerous."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        return False
    return ext in ALLOWED_EXTENSIONS


def get_file_category(filename: str) -> str:
    """Categorize the file for filtering and UI presentation."""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in {'pdf'}:
        return 'pdf'
    elif ext in {'png', 'jpg', 'jpeg', 'webp', 'gif'}:
        return 'image'
    elif ext in {'docx', 'doc', 'txt', 'xlsx', 'xls', 'pptx', 'ppt'}:
        return 'document'
    elif ext in {'zip', 'tar', 'gz'}:
        return 'archive'
    return 'notes'


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    def save(self, file_storage, target_filename: str, mime_type: str = None) -> str:
        """Save file and return its relative/canonical storage path."""
        pass

    @abstractmethod
    def delete(self, storage_path: str) -> bool:
        """Delete file from storage."""
        pass

    @abstractmethod
    def get_path_or_url(self, storage_path: str) -> str:
        """Get local filesystem path or signed URL for downloading."""
        pass


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider for development, tests, and self-hosted deployments."""

    def __init__(self, base_dir: str = None):
        if not base_dir:
            base_dir = os.environ.get('STORAGE_LOCAL_DIR', os.path.join(os.getcwd(), 'uploads'))
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, file_storage, target_filename: str, mime_type: str = None) -> str:
        dest_path = os.path.join(self.base_dir, target_filename)
        # Ensure destination directory exists if subfolders are used
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        file_storage.seek(0)
        file_storage.save(dest_path)
        return os.path.relpath(dest_path, self.base_dir).replace('\\', '/')

    def delete(self, storage_path: str) -> bool:
        full_path = os.path.join(self.base_dir, storage_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                return True
            except OSError:
                return False
        return False

    def get_path_or_url(self, storage_path: str) -> str:
        return os.path.join(self.base_dir, storage_path)


class S3StorageProvider(StorageProvider):
    """S3-compatible Object Storage provider (AWS S3, Cloudflare R2, MinIO, Neon S3)."""

    def __init__(self):
        self.bucket = os.environ.get('STORAGE_BUCKET', 'classcatch-vault')
        self.endpoint_url = os.environ.get('STORAGE_ENDPOINT_URL')
        self.access_key = os.environ.get('STORAGE_ACCESS_KEY')
        self.secret_key = os.environ.get('STORAGE_SECRET_KEY')
        self.region = os.environ.get('STORAGE_REGION', 'us-east-1')

    def _get_client(self):
        try:
            import boto3
            return boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
        except ImportError:
            raise RuntimeError("boto3 is required for S3StorageProvider. Please install boto3.")

    def save(self, file_storage, target_filename: str, mime_type: str = None) -> str:
        client = self._get_client()
        key = f"vault/{target_filename}"
        file_storage.seek(0)
        extra_args = {}
        if mime_type:
            extra_args['ContentType'] = mime_type
        client.upload_fileobj(
            file_storage,
            self.bucket,
            key,
            ExtraArgs=extra_args if extra_args else None
        )
        return key

    def delete(self, storage_path: str) -> bool:
        client = self._get_client()
        try:
            client.delete_object(Bucket=self.bucket, Key=storage_path)
            return True
        except Exception:
            return False

    def get_path_or_url(self, storage_path: str, as_attachment: bool = False, filename: str = None) -> str:
        client = self._get_client()
        params = {'Bucket': self.bucket, 'Key': storage_path}
        if filename:
            disposition = 'attachment' if as_attachment else 'inline'
            params['ResponseContentDisposition'] = f'{disposition}; filename="{filename}"'
        return client.generate_presigned_url(
            'get_object',
            Params=params,
            ExpiresIn=3600
        )


def is_s3_configured() -> bool:
    """Check if minimum required credentials for S3/R2/Neon storage are present."""
    access_key = os.environ.get('STORAGE_ACCESS_KEY')
    secret_key = os.environ.get('STORAGE_SECRET_KEY')
    bucket = os.environ.get('STORAGE_BUCKET')
    return bool(access_key and secret_key and bucket)


def get_storage_provider() -> StorageProvider:
    """Factory function returning the configured storage provider with automatic fallback."""
    provider_name = os.environ.get('STORAGE_PROVIDER', 'local').lower()
    if provider_name in {'s3', 'r2', 'neon'}:
        if is_s3_configured():
            try:
                return S3StorageProvider()
            except Exception as e:
                import logging
                logging.getLogger('classcatch.storage').warning(f"Failed to initialize S3 provider, falling back to local: {e}")
                return LocalStorageProvider()
        else:
            return LocalStorageProvider()
    return LocalStorageProvider()


def handle_file_upload(file_storage, uploader_id: int, course_id: int = None, section: str = '2FE') -> tuple:
    """
    Validates, securely stores, and records metadata for an uploaded file.
    Returns: (StorageFile instance, None) on success, or (None, error_message) on failure.
    """
    if not file_storage or not file_storage.filename:
        return None, "No file selected."

    raw_filename = secure_filename(file_storage.filename)
    if not is_allowed_file(raw_filename):
        return None, "Invalid file format. Executable scripts and unsupported files are strictly prohibited."

    # Check file size
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)

    if size > MAX_FILE_SIZE_BYTES:
        return None, f"File size ({size / (1024*1024):.1f} MB) exceeds maximum allowed limit of 15 MB."

    if size == 0:
        return None, "Uploaded file cannot be empty."

    # Generate unique storage filename: <uuid>_<clean_name>
    ext = raw_filename.rsplit('.', 1)[1].lower() if '.' in raw_filename else 'bin'
    stored_name = f"{uuid.uuid4().hex}_{raw_filename}"

    mime_type, _ = mimetypes.guess_type(raw_filename)
    mime_type = mime_type or 'application/octet-stream'
    file_category = get_file_category(raw_filename)

    provider = get_storage_provider()
    storage_path = provider.save(file_storage, stored_name, mime_type=mime_type)
    actual_provider = 's3' if isinstance(provider, S3StorageProvider) else 'local'

    storage_record = StorageFile(
        uploader_id=uploader_id,
        course_id=course_id,
        section=section,
        filename=stored_name,
        original_filename=raw_filename,
        file_type=file_category,
        mime_type=mime_type,
        file_size=size,
        storage_path=storage_path,
        storage_provider=actual_provider,
        status='Active'
    )

    db.session.add(storage_record)
    db.session.commit()

    return storage_record, None
