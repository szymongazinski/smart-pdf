"""Offline PP-OCRv5, DirectML acceleration and a Tesseract second opinion."""
import hashlib
import json
import os
import uuid
from functools import lru_cache


def configure_runtime():
    # RapidOCR passes OmegaConf mappings to ORT, which requires actual dicts.
    # DirectML also requires sequential execution without memory patterns.
    import onnxruntime as ort
    from rapidocr.inference_engine.onnxruntime.main import OrtInferSession
    from rapidocr.inference_engine.onnxruntime.provider_config import ProviderConfig
    if getattr(OrtInferSession,"_smartpdf_configured",False):
        return
    original_options = OrtInferSession._init_sess_opts
    original_providers = ProviderConfig.get_ep_list
    def options(cfg):
        value = original_options(cfg)
        value.enable_mem_pattern = False
        value.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        if os.environ.get("SMARTPDF_OCR_PROFILE"):
            value.enable_profiling = True
            value.profile_file_prefix = os.environ["SMARTPDF_OCR_PROFILE"]+"-"+uuid.uuid4().hex
        return value
    def providers(self):
        return [(entry[0],dict(entry[1])) if isinstance(entry,tuple) else entry
                for entry in original_providers(self)]
    OrtInferSession._init_sess_opts = staticmethod(options)
    ProviderConfig.get_ep_list = providers
    OrtInferSession._smartpdf_configured = True


@lru_cache(maxsize=2)
def get_engine(gpu):
    import numpy as np
    from rapidocr import RapidOCR,LangRec,ModelType,OCRVersion
    from smart_pdf.ocr import resources
    configure_runtime()
    directory = resources()/"ppocr"
    manifest = json.loads((resources()/"ppocr-models.json").read_text(encoding="utf-8"))
    for name,info in manifest.items():
        path = directory/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=info["sha256"]:
            raise RuntimeError("Brak lub uszkodzony model OCR: "+name)
    class OrientedOCR(RapidOCR):
        def build_final_output(self,ori_img,det_res,cls_res,rec_res,cropped_img_list,op_record):
            valid = [i for i,(text,score) in enumerate(zip(rec_res.txts or (),rec_res.scores or ()))
                     if text.strip() and score>=self.text_score]
            labels = cls_res.cls_res or []
            result = super().build_final_output(ori_img,det_res,cls_res,rec_res,cropped_img_list,op_record)
            if getattr(result,"boxes",None) is None:
                return result
            reading,words = [],[]
            for i,box in enumerate(result.boxes):
                quad = np.asarray(box,dtype=float)
                if np.linalg.norm(quad[3]-quad[0])>=1.5*np.linalg.norm(quad[1]-quad[0]):
                    quad = np.roll(quad,-1,axis=0)
                flipped = i<len(valid) and valid[i]<len(labels) and labels[valid[i]][0]=="180" and labels[valid[i]][1]>.9
                if flipped:
                    quad = np.roll(quad,-2,axis=0)
                reading.append(quad)
                direction = quad[1]-quad[0]
                line_words = []
                for entry in result.word_results[i]:
                    if not isinstance(entry,(tuple,list)) or len(entry)!=3 or entry[2] is None:
                        continue
                    text,score,word_box = entry
                    q = np.asarray(word_box,dtype=float)
                    if flipped:
                        q = 2*np.mean(box,axis=0)-q
                    rotations = [np.roll(q,-k,axis=0) for k in range(4)]
                    q = max(rotations,key=lambda v:float(np.dot(v[1]-v[0],direction))/max(np.linalg.norm(v[1]-v[0]),1))
                    line_words.append((text,score,q.tolist()))
                words.append(tuple(line_words))
            result.reading_quads = reading
            result.word_results = tuple(words)
            return result
    return OrientedOCR(params={
        "Global.log_level":"error", "Global.return_word_box":True,
        "Global.max_side_len":4000, "Global.text_score":.45,
        "Det.model_path":str(directory/"det.onnx"),
        "Det.model_type":ModelType.SERVER, "Det.ocr_version":OCRVersion.PPOCRV5,
        "Det.mean":[.485,.456,.406], "Det.std":[.229,.224,.225],
        "Det.limit_type":"max", "Det.limit_side_len":2016,
        "Rec.model_path":str(directory/"rec.onnx"), "Rec.lang_type":LangRec.LATIN,
        "Rec.model_type":ModelType.MOBILE, "Rec.ocr_version":OCRVersion.PPOCRV5,
        "Cls.model_path":str(directory/"cls.onnx"),
        "EngineConfig.onnxruntime.use_dml":gpu,
        "EngineConfig.onnxruntime.dml_ep_cfg":{"device_id":0},
        "EngineConfig.onnxruntime.intra_op_num_threads":2,
        "EngineConfig.onnxruntime.inter_op_num_threads":1,
    })


def recognize(pixmap,mode):
    import numpy as np
    image = np.frombuffer(pixmap.samples,dtype=np.uint8).reshape(pixmap.height,pixmap.width,3)
    image = image[:,:,::-1].copy()  # RapidOCR's ndarray input uses BGR.
    fallback = ""
    if mode not in {"auto","cpu","gpu"}:
        raise ValueError("Nieznany silnik OCR: "+mode)
    for gpu in ([True,False] if mode=="auto" else [mode=="gpu"]):
        try:
            engine = get_engine(gpu)
            result = engine(image,return_word_box=True)
            providers = {name: getattr(engine,name).session.session.get_providers()
                         for name in ("text_det","text_rec","text_cls")
                         if getattr(engine,name) is not None}
            if gpu and not all("DmlExecutionProvider" in p for p in providers.values()):
                raise RuntimeError("Sterownik nie udostępnił przyspieszenia DirectML.")
            return result,{"backend":"gpu" if gpu else "cpu", "providers":providers,
                           "fallback":fallback, "assisted_lines":0}
        except Exception as error:
            if mode!="auto" or not gpu:
                raise
            fallback = "GPU niedostępne; użyto CPU: "+str(error)[:180]
    raise RuntimeError("Nie udało się uruchomić OCR.")


def write_word(page,font,text,quad):
    """Fit invisible Unicode text to the actual word quadrilateral."""
    import pymupdf
    points = [pymupdf.Point(*p) for p in quad]
    horizontal,vertical = points[1]-points[0],points[3]-points[0]
    width,height = abs(horizontal),abs(vertical)
    if not text.strip() or width<.1 or height<.1:
        return
    fontsize = height/(font.ascender-font.descender)
    sx = width/max(font.text_length(text,fontsize=fontsize),.1)
    h,v = horizontal/width,vertical/height
    baseline = points[3]+v*(fontsize*font.descender)
    # Text morphs use PDF's upward Y axis; detected boxes use downward Y.
    matrix = pymupdf.Matrix(h.x*sx,-h.y*sx,-v.x,v.y,0,0)
    page.insert_text(baseline,text,fontname="smartocr",fontsize=fontsize,
                     render_mode=3,morph=(baseline,matrix),overlay=True)


def make_layer(pixmap,languages,mode,width,height):
    import pymupdf
    from smart_pdf.ocr import tessdata,resources
    result,report = recognize(pixmap,mode)
    sx,sy = width/pixmap.width,height/pixmap.height
    with pymupdf.open() as layer:
        page = layer.new_page(width=width,height=height)
        font = pymupdf.Font(fontfile=str(resources()/"NotoSans-Regular.ttf"))
        page.insert_font(fontname="smartocr",fontbuffer=font.buffer)
        written = 0
        for i,line in enumerate(result.txts or ()):
            reading = result.reading_quads[i]
            quad = [[float(x)*sx,float(y)*sy] for x,y in reading]
            words = []
            if result.scores[i]<.96:
                try:
                    words = second_opinion(pixmap,reading,languages,sx,sy)
                    if words:
                        report["assisted_lines"] += 1
                except Exception:
                    report["second_opinion"] = "Tesseract niedostępny"
            if not words and result.word_results and i<len(result.word_results):
                for entry in result.word_results[i]:
                    if len(entry)==3 and entry[2] is not None:
                        words.append((entry[0],[[float(x)*sx,float(y)*sy] for x,y in entry[2]]))
            if not words:
                words = [(line,quad)]
            for text,box in words:
                write_word(page,font,text,box)
                written += 1
        report["words"] = written
        report["low_confidence_lines"] = sum(s<.8 for s in (result.scores or ()))
        return layer.tobytes(garbage=4,deflate=True),report


def second_opinion(pixmap,quad,languages,sx,sy):
    """Recognize an upright line, then map its words back to the source page."""
    import cv2
    import numpy as np
    import pymupdf
    from smart_pdf.ocr import tessdata
    quad = np.asarray(quad,dtype=np.float32)
    width = max(1,round(float(np.linalg.norm(quad[1]-quad[0]))))
    height = max(1,round(float(np.linalg.norm(quad[3]-quad[0]))))
    destination = np.asarray([[0,0],[width,0],[width,height],[0,height]],dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(quad,destination)
    image = np.frombuffer(pixmap.samples,dtype=np.uint8).reshape(pixmap.height,pixmap.width,3)
    cropped = cv2.warpPerspective(image,matrix,(width,height),flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_CONSTANT,borderValue=(255,255,255))
    padding = max(12,round(height*.3))
    cropped = cv2.copyMakeBorder(cropped,padding,padding,padding,padding,cv2.BORDER_CONSTANT,value=(255,255,255))
    pix = pymupdf.Pixmap(pymupdf.csRGB,cropped.shape[1],cropped.shape[0],cropped.tobytes(),False)
    pix.set_dpi(pixmap.xres,pixmap.yres)
    data = pix.pdfocr_tobytes(language=languages,tessdata=str(tessdata()))
    inverse = np.linalg.inv(matrix)
    words = []
    with pymupdf.open(stream=data,filetype="pdf") as doc:
        tx,ty = pix.width/doc[0].rect.width,pix.height/doc[0].rect.height
        for w in doc[0].get_text("words"):
            box = np.asarray([[[w[0]*tx-padding,w[1]*ty-padding],[w[2]*tx-padding,w[1]*ty-padding],
                               [w[2]*tx-padding,w[3]*ty-padding],[w[0]*tx-padding,w[3]*ty-padding]]],dtype=np.float32)
            original = cv2.perspectiveTransform(box,inverse)[0]
            words.append((w[4],[[float(x)*sx,float(y)*sy] for x,y in original]))
    return words
