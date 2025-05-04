import os, pandas as pd
from io import BytesIO
from pathlib import Path
try:
    from azure.storage.blob import BlobServiceClient
except ImportError:
    BlobServiceClient = None   # Will fallback to local file access
from gold.config import AZ_CONTAINER, CACHE_DIR, TIMEFRAME_FILES

LOCAL_DATA_DIR = Path(__file__).resolve().parent.parent  # repo root contains CSVs

def _client():
    """Return an Azure BlobServiceClient or None if credentials are missing."""
    if BlobServiceClient is None:
        return None
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if conn:
        return BlobServiceClient.from_connection_string(conn)
    acct = os.getenv("AZURE_STORAGE_ACCOUNT")
    key  = os.getenv("AZURE_STORAGE_KEY")
    if not (acct and key):
        return None
    return BlobServiceClient(account_url=f"https://{acct}.blob.core.windows.net",
                             credential=key)

def _load_local(blob: str) -> pd.DataFrame:
    """Attempt to read the CSV directly from the local checkout."""
    # try root/<blob>  e.g. D.csv
    for root in [LOCAL_DATA_DIR, LOCAL_DATA_DIR.parent]:
        fpath = root / blob
        if fpath.exists():
            return pd.read_csv(fpath)
    raise FileNotFoundError(f"Could not locate {blob} locally and Azure credentials missing.")

def load_csv(blob: str) -> pd.DataFrame:
    """Load a CSV from Azure Blob Storage if credentials are available,
    otherwise fall back to the file on disk.  A parquet cache is maintained
    regardless of the source to speed up subsequent loads."""
    cache = CACHE_DIR / (Path(blob).stem + ".parquet")
    if cache.exists():
        return pd.read_parquet(cache)

    client = _client()
    if client is not None:
        try:
            data = client.get_container_client(AZ_CONTAINER).download_blob(blob).readall()
            df   = pd.read_csv(BytesIO(data))
        except Exception as e:
            # log and fall back
            print(f"[azure.py] Azure load failed, falling back to local file: {e}")
            df = _load_local(blob)
    else:
        df = _load_local(blob)

    df.to_parquet(cache)
    return df
