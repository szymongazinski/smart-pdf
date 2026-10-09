"""Download pinned official Tesseract best models; no runtime network needed."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REVISION = "e12c65a915945e4c28e237a9b52bc4a8f39a0cec"


def main():
    target = ROOT / "assets" / "tessdata"
    target.mkdir(parents=True,exist_ok=True)
    manifest_path = ROOT / "assets" / "ocr-models.json"
    expected = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    actual = {}
    for lang in ("pol","eng"):
        path = target / f"{lang}.traineddata"
        if not path.exists():
            url = f"https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/{REVISION}/{lang}.traineddata"
            print(f"Pobieranie modelu {lang}...",flush=True)
            with urlopen(url,timeout=120) as response:
                data = response.read()
            if len(data)<100_000:
                raise RuntimeError("Pobrany model jest nieprawidłowy.")
            digest = hashlib.sha256(data).hexdigest()
            if lang in expected and digest!=expected[lang]["sha256"]:
                raise RuntimeError(f"Błędna suma SHA256 modelu {lang}")
            path.write_bytes(data)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if lang in expected and digest!=expected[lang]["sha256"]:
            raise RuntimeError(f"Błędna suma SHA256 modelu {lang}")
        actual[lang] = {"revision":REVISION,"sha256":digest,"bytes":path.stat().st_size}
        print(f"{lang}: {path.stat().st_size:,} bajtów / SHA256 {digest}",flush=True)
    if not expected:
        manifest_path.write_text(json.dumps(actual,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
