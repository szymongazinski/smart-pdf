"""Fetch pinned, SHA256-verified PP-OCRv5 ONNX models for offline inference."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.10.0/onnx/"
MODELS = {
    "det.onnx": ("PP-OCRv5/det/ch_PP-OCRv5_det_server.onnx", "0f8846b1d4bba223a2a2f9d9b44022fbc22cc019051a602b41a7fda9667e4cad"),
    "rec.onnx": ("PP-OCRv5/rec/latin_PP-OCRv5_rec_mobile.onnx", "b20bd37c168a570f583afbc8cd7925603890efbcdc000a59e22c269d160b5f5a"),
    "cls.onnx": ("PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx", "e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c"),
}

def main():
    target = ROOT/"assets"/"ppocr"
    target.mkdir(parents=True,exist_ok=True)
    manifest = {}
    for name,(relative,expected) in MODELS.items():
        path = target/name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            temporary = path.with_suffix(".part")
            print("Pobieranie",name,flush=True)
            try:
                with urlopen(BASE+relative,timeout=60) as response,temporary.open("wb") as stream:
                    while chunk:=response.read(1024*1024):
                        stream.write(chunk)
                if hashlib.sha256(temporary.read_bytes()).hexdigest()!=expected:
                    raise ValueError("Nieprawidłowa suma SHA256: "+name)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
        manifest[name] = {"url":BASE+relative,"sha256":expected,"bytes":path.stat().st_size}
        print(name,path.stat().st_size,flush=True)
    (ROOT/"assets"/"ppocr-models.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
