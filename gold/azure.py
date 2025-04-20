import os, pandas as pd
from io import BytesIO
from pathlib import Path
from azure.storage.blob import BlobServiceClient
from gold.config import AZ_CONTAINER, CACHE_DIR

def _client():
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if conn:
        return BlobServiceClient.from_connection_string(conn)
    acct = os.getenv("AZURE_STORAGE_ACCOUNT")
    key  = os.getenv("AZURE_STORAGE_KEY")
    if not (acct and key):
        raise RuntimeError("Azure credentials missing")
    return BlobServiceClient(account_url=f"https://{acct}.blob.core.windows.net",
                             credential=key)

def load_csv(blob: str) -> pd.DataFrame:
    cache = CACHE_DIR / (Path(blob).stem + ".parquet")
    if cache.exists():
        return pd.read_parquet(cache)
    data = _client().get_container_client(AZ_CONTAINER).download_blob(blob).readall()
    df   = pd.read_csv(BytesIO(data))
    df.to_parquet(cache)
    return df
