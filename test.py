import tqdm
import io
import requests
import subprocess

def download_as_bytes_with_progress(url: str) -> bytes:
    resp = requests.get(url, stream=True)
    total = int(resp.headers.get('content-length', 0))
    bio = io.BytesIO()
    with tqdm.tqdm(
        desc=url,
        total=total,
        unit='b',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for chunk in resp.iter_content(chunk_size=65536):
            bar.update(len(chunk))
            bio.write(chunk)
    return bio.getvalue()
url = "https://www.trbimg.com/img-563bb6ac/turbine/ct-tests-ten-things-perspec-1108-20151105"