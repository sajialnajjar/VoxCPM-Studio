"""
╔══════════════════════════════════════════════════════════╗
║     VoxCPM Voice Cloning Studio  v2.0                  ║
║  Features: Voice Library · A/B Compare · Quality Stats ║
╚══════════════════════════════════════════════════════════╝
"""
import os, sys, threading, time, json, queue, traceback, tempfile, shutil
import numpy as np
import soundfile as sf
from pathlib import Path
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import tkinter as tk

try:
    import pygame; PYGAME_OK = True
except ImportError:
    PYGAME_OK = False
try:
    import sounddevice as sd; SD_OK = True
except ImportError:
    SD_OK = False

# ── Theme ──────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
ACCENT  = "#6C63FF"; ACCENT2 = "#A78BFA"; BG_DARK = "#0D0D1A"
BG_CARD = "#13132B"; BG_INPUT= "#1A1A35"; BG_HOVER= "#1F1F40"
SUCCESS = "#22D3A0"; WARNING = "#FBBF24"; ERROR   = "#F87171"
TEXT_DIM= "#8B8BAE"; TEAL    = "#0EA5E9"

def fmt_dur(s):
    m,s=divmod(int(s),60); return f"{m:02d}:{s:02d}"

def dbfs(data):
    rms = np.sqrt(np.mean(data.astype(float)**2))
    return 20*np.log10(rms+1e-12)

# ── Engine ─────────────────────────────────────────────────────────
class VoxCPMEngine:
    def __init__(self, log_cb=None):
        self.model=None; self.asr_model=None
        self.loaded=False; self.asr_loaded=False
        self.log=log_cb or print

    def load_tts(self, model_path=None, hf_id=None):
        import torch, os
        from voxcpm import VoxCPM
        mid = model_path or hf_id or "openbmb/VoxCPM1.5"
        if torch.cuda.is_available():
            dev = "cuda"
            self.log(f"🖥️  GPU: {torch.cuda.get_device_name(0)}")
        else:
            dev = "cpu"
            self.log("⚠️  CUDA not available — using CPU (slow)")
        os.environ["VOXCPM_DEVICE"] = dev          # hint for voxcpm internals
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"   # ensure GPU 0 is visible
        self.log(f"⏳ Loading TTS on [{dev.upper()}]: {mid}")
        self.model = VoxCPM.from_pretrained(mid)
        self.loaded = True
        self.log("✅ TTS ready!")


    def load_asr(self, path="iic/SenseVoiceSmall"):
        try:
            from funasr import AutoModel
            self.asr_model=AutoModel(model=path,trust_remote_code=True,
                vad_model="fsmn-vad",vad_kwargs={"max_single_segment_time":30000},device="cpu")
            self.asr_loaded=True; self.log("✅ ASR ready!")
        except Exception as e:
            self.log(f"⚠️ ASR failed: {e}")

    def transcribe(self, path):
        if self.asr_model:
            import re
            res=self.asr_model.generate(input=path,cache={},language="auto",use_itn=True)
            txt=res[0]["text"] if res else ""
            return re.sub(r"<\|[^|]+\|>","",txt).strip()
        try:
            from faster_whisper import WhisperModel
            wm=WhisperModel("small",device="cpu",compute_type="int8")
            segs,_=wm.transcribe(path,beam_size=5)
            return " ".join(s.text for s in segs).strip()
        except: return ""

    def synthesize(self, text, prompt_wav=None, prompt_text=None,
                   cfg=2.0, steps=10, normalize=False, denoise=False):
        if not self.loaded: raise RuntimeError("Model not loaded")
        return self.model.generate(text=text,
            prompt_wav_path=prompt_wav or None,
            prompt_text=prompt_text or None,
            cfg_value=cfg, inference_timesteps=steps,
            normalize=normalize, denoise=denoise)

    @property
    def sample_rate(self):
        return self.model.tts_model.sample_rate if self.loaded else 44100

# ── Icon Button ────────────────────────────────────────────────────
class IconBtn(ctk.CTkButton):
    def __init__(self, master, em, lbl, **kw):
        super().__init__(master, text=f" {em}  {lbl}", corner_radius=10,
            border_width=1, border_color=ACCENT, fg_color=BG_INPUT,
            hover_color=BG_HOVER, font=ctk.CTkFont("Segoe UI",12,"bold"), **kw)

# ── Waveform Canvas ────────────────────────────────────────────────
class Waveform(tk.Canvas):
    def __init__(self, master, color="#6C63FF", **kw):
        super().__init__(master, bg="#080815", highlightthickness=0, **kw)
        self._d=None; self._sr=44100; self._color=color
        self.bind("<Configure>", lambda e: self._draw())

    def load(self, data, sr):
        self._d = data.mean(axis=1) if data.ndim>1 else data
        self._sr=sr; self._draw()

    def clear(self):
        self._d=None; self.delete("all")
        w,h=self.winfo_width(),self.winfo_height()
        if w>10: self.create_text(w//2,h//2,text="🎵 No audio",fill=TEXT_DIM,font=("Segoe UI",11))

    def _draw(self):
        self.delete("all")
        if self._d is None: return self.clear()
        w,h=self.winfo_width(),self.winfo_height()
        if w<10 or h<10: return
        d=self._d; pts=min(len(d),w*2); step=max(1,len(d)//pts)
        mid=h//2; xs=np.linspace(0,w,pts)
        amps=np.abs(d[::step][:pts])
        if amps.max()>0: amps=amps/amps.max()
        base=int(self._color[1:],16)
        r0,g0,b0=(base>>16)&255,(base>>8)&255,base&255
        for i in range(len(xs)-1):
            a=float(amps[i]); y1=mid-int(a*(mid-4)); y2=mid+int(a*(mid-4))
            r=min(255,r0+int(a*80)); g=min(255,g0+int(a*40)); b=min(255,b0)
            self.create_line(xs[i],y1,xs[i],y2,fill=f"#{r:02x}{g:02x}{b:02x}",width=1)

# ── Log Panel ──────────────────────────────────────────────────────
class LogPanel(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=BG_CARD, corner_radius=12, **kw)
        self._q=queue.Queue()
        ctk.CTkLabel(self,text="📋 Activity Log",
            font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=ACCENT2).pack(anchor="w",padx=12,pady=(8,0))
        self.txt=ctk.CTkTextbox(self,corner_radius=8,fg_color="#080815",
            text_color="#C0C0E0",font=ctk.CTkFont("Consolas",11),state="disabled")
        self.txt.pack(fill="both",expand=True,padx=8,pady=8)
        self._poll()

    def log(self, msg):
        self._q.put(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")

    def _poll(self):
        while not self._q.empty():
            self.txt.configure(state="normal")
            self.txt.insert("end",self._q.get_nowait())
            self.txt.see("end"); self.txt.configure(state="disabled")
        self.after(100,self._poll)

# ── Settings Panel ─────────────────────────────────────────────────
class SettingsPanel(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color=BG_CARD, corner_radius=12, **kw)
        ctk.CTkLabel(self,text="⚙️ Model & Parameters",
            font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=ACCENT2).pack(anchor="w",padx=12,pady=(10,4))
        self._row("HF Model ID:","model_id","openbmb/VoxCPM1.5",placeholder="openbmb/VoxCPM1.5")
        self._row("Local Path:","local_path","",placeholder="(optional) local folder",browse=True)
        ctk.CTkFrame(self,height=1,fg_color=ACCENT).pack(fill="x",padx=12,pady=6)
        self._slider("CFG Value","cfg",2.0,1.0,5.0,0.1)
        self._slider("Steps","steps",10,1,50,1)
        tf=ctk.CTkFrame(self,fg_color="transparent"); tf.pack(fill="x",padx=12,pady=4)
        for attr,lbl in [("normalize","Normalize"),("denoise","Denoise"),("streaming","Streaming")]:
            sw=ctk.CTkSwitch(tf,text=lbl,font=ctk.CTkFont("Segoe UI",11),
                progress_color=ACCENT,button_color=ACCENT2); sw.pack(side="left",padx=(0,12))
            setattr(self,attr,sw)

    def _row(self, lbl, attr, val, placeholder="", browse=False):
        r=ctk.CTkFrame(self,fg_color="transparent"); r.pack(fill="x",padx=12,pady=2)
        ctk.CTkLabel(r,text=lbl,width=120,font=ctk.CTkFont("Segoe UI",11),
            text_color=TEXT_DIM).pack(side="left")
        e=ctk.CTkEntry(r,fg_color=BG_INPUT,border_color=ACCENT,placeholder_text=placeholder)
        e.pack(side="left",fill="x",expand=True); e.insert(0,val)
        setattr(self,attr,e)
        if browse:
            ctk.CTkButton(r,text="📂",width=34,fg_color=BG_INPUT,hover_color=BG_HOVER,
                border_width=1,border_color=ACCENT,
                command=lambda a=attr: self._browse(a)).pack(side="left",padx=(4,0))

    def _browse(self, attr):
        d=filedialog.askdirectory(title="Select model folder")
        if d: e=getattr(self,attr); e.delete(0,"end"); e.insert(0,d)

    def _slider(self, lbl, attr, default, lo, hi, step):
        row=ctk.CTkFrame(self,fg_color="transparent"); row.pack(fill="x",padx=12,pady=2)
        ctk.CTkLabel(row,text=lbl+":",width=120,font=ctk.CTkFont("Segoe UI",11),
            text_color=TEXT_DIM).pack(side="left")
        var=ctk.DoubleVar(value=default)
        vl=ctk.CTkLabel(row,text=str(default),width=38,
            font=ctk.CTkFont("Consolas",11),text_color=ACCENT2); vl.pack(side="right")
        ctk.CTkSlider(row,variable=var,from_=lo,to=hi,
            number_of_steps=int((hi-lo)/step),button_color=ACCENT,
            progress_color=ACCENT2,fg_color=BG_INPUT).pack(side="left",fill="x",expand=True,padx=(0,4))
        var.trace_add("write",lambda *_: vl.configure(text=f"{var.get():.1f}"))
        setattr(self,f"{attr}_var",var)

    @property
    def cfg(self): return float(self.cfg_var.get())
    @property
    def steps(self): return int(self.steps_var.get())

# ── Voice Library ──────────────────────────────────────────────────
LIBRARY_DIR = Path("voice_library")
LIBRARY_JSON = LIBRARY_DIR / "index.json"

class VoiceLibrary:
    """Persists named voice profiles to disk."""
    def __init__(self):
        LIBRARY_DIR.mkdir(exist_ok=True)
        self._data = {}
        if LIBRARY_JSON.exists():
            try: self._data=json.loads(LIBRARY_JSON.read_text())
            except: pass

    def save(self):
        LIBRARY_JSON.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))

    def add(self, name, wav_path, transcript, notes=""):
        dest = LIBRARY_DIR / f"{name.replace(' ','_')}.wav"
        shutil.copy2(wav_path, dest)
        self._data[name] = {"wav": str(dest), "transcript": transcript,
                            "notes": notes, "added": datetime.now().isoformat()}
        self.save()

    def remove(self, name):
        entry = self._data.pop(name, None)
        if entry:
            try: Path(entry["wav"]).unlink()
            except: pass
            self.save()

    def names(self): return list(self._data.keys())
    def get(self, name): return self._data.get(name)
    def __len__(self): return len(self._data)


# ── Voice Library Panel ────────────────────────────────────────────
class VoiceLibraryPanel(ctk.CTkFrame):
    def __init__(self, master, library, load_cb=None, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.lib = library
        self.load_cb = load_cb
        self._sel_name = None

        top = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=14)
        top.pack(fill="x", pady=(0,8), padx=4)
        ctk.CTkLabel(top, text="📚  Voice Library",
            font=ctk.CTkFont("Segoe UI",15,"bold"), text_color=ACCENT2).pack(anchor="w",padx=14,pady=(10,2))
        ctk.CTkLabel(top, text="Save reference voices with transcripts for quick reuse.",
            font=ctk.CTkFont("Segoe UI",11), text_color=TEXT_DIM).pack(anchor="w",padx=14,pady=(0,10))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=4)

        left = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=14, width=270)
        left.pack(side="left", fill="y", padx=(0,8)); left.pack_propagate(False)
        ctk.CTkLabel(left, text="Saved Voices", font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=ACCENT2).pack(anchor="w", padx=12, pady=(10,4))
        self.vlist = tk.Listbox(left, bg="#0A0A1A", fg="#C0C0E0",
            selectbackground=ACCENT, selectforeground="white",
            font=("Segoe UI",12), bd=0, highlightthickness=0, activestyle="none")
        self.vlist.pack(fill="both", expand=True, padx=8, pady=(0,4))
        self.vlist.bind("<<ListboxSelect>>", self._on_select)
        IconBtn(left, "🗑️", "Delete", command=self._delete, width=120).pack(padx=8, pady=(0,8))

        right = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=14)
        right.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(right, text="Voice Details", font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=ACCENT2).pack(anchor="w", padx=14, pady=(10,4))
        r1 = ctk.CTkFrame(right, fg_color="transparent"); r1.pack(fill="x", padx=14)
        ctk.CTkLabel(r1, text="Name:", width=90, font=ctk.CTkFont("Segoe UI",11),
            text_color=TEXT_DIM).pack(side="left")
        self.name_lbl = ctk.CTkLabel(r1, text="—",
            font=ctk.CTkFont("Segoe UI",11,"bold"), text_color="white")
        self.name_lbl.pack(side="left")
        r2 = ctk.CTkFrame(right, fg_color="transparent"); r2.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(r2, text="Added:", width=90, font=ctk.CTkFont("Segoe UI",11),
            text_color=TEXT_DIM).pack(side="left")
        self.date_lbl = ctk.CTkLabel(r2, text="—", font=ctk.CTkFont("Segoe UI",11),
            text_color=TEXT_DIM); self.date_lbl.pack(side="left")
        ctk.CTkLabel(right, text="Transcript:", font=ctk.CTkFont("Segoe UI",11),
            text_color=TEXT_DIM).pack(anchor="w", padx=14, pady=(4,0))
        self.trans_box = ctk.CTkTextbox(right, height=90, fg_color=BG_INPUT,
            border_color=ACCENT, border_width=1, corner_radius=8,
            font=ctk.CTkFont("Segoe UI",11), state="disabled")
        self.trans_box.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(right, text="Notes:", font=ctk.CTkFont("Segoe UI",11),
            text_color=TEXT_DIM).pack(anchor="w", padx=14)
        self.notes_box = ctk.CTkTextbox(right, height=55, fg_color=BG_INPUT,
            border_color=ACCENT, border_width=1, corner_radius=8,
            font=ctk.CTkFont("Segoe UI",11))
        self.notes_box.pack(fill="x", padx=14, pady=(0,6))
        self.prev_wave = Waveform(right, color=ACCENT, height=65)
        self.prev_wave.pack(fill="x", padx=14, pady=(0,8))
        dbtns = ctk.CTkFrame(right, fg_color="transparent"); dbtns.pack(fill="x", padx=14, pady=(0,12))
        IconBtn(dbtns, "▶️", "Play", command=self._play, width=100).pack(side="left", padx=(0,6))
        IconBtn(dbtns, "📥", "Load to Main", command=self._load_to_main, width=150).pack(side="left")
        self._refresh()

    def _refresh(self):
        self.vlist.delete(0, "end")
        for n in self.lib.names(): self.vlist.insert("end", f"  🎤  {n}")

    def _on_select(self, _=None):
        idx = self.vlist.curselection()
        if not idx: return
        name = self.lib.names()[idx[0]]; self._sel_name = name
        entry = self.lib.get(name)
        self.name_lbl.configure(text=name)
        self.date_lbl.configure(text=entry.get("added","?")[:10])
        self.trans_box.configure(state="normal")
        self.trans_box.delete("1.0","end"); self.trans_box.insert("1.0",entry.get("transcript",""))
        self.trans_box.configure(state="disabled")
        self.notes_box.delete("1.0","end"); self.notes_box.insert("1.0",entry.get("notes",""))
        wav_path = entry.get("wav","")
        if wav_path and Path(wav_path).exists():
            try: d,sr=sf.read(wav_path,dtype="float32",always_2d=False); self.prev_wave.load(d,sr)
            except: self.prev_wave.clear()
        else: self.prev_wave.clear()

    def _play(self):
        if not self._sel_name: return
        entry = self.lib.get(self._sel_name); wav = entry.get("wav","") if entry else None
        if wav and Path(wav).exists():
            if PYGAME_OK:
                def _p(): pygame.mixer.init(); pygame.mixer.music.load(wav); pygame.mixer.music.play()
                threading.Thread(target=_p, daemon=True).start()
            else: os.startfile(wav)

    def _load_to_main(self):
        if not self._sel_name: return
        entry = self.lib.get(self._sel_name)
        if entry and self.load_cb: self.load_cb(entry["wav"], entry["transcript"])

    def _delete(self):
        if not self._sel_name: return
        if messagebox.askyesno("Delete", f"Delete voice '{self._sel_name}'?"):
            self.lib.remove(self._sel_name); self._sel_name=None; self._refresh()
            self.prev_wave.clear(); self.name_lbl.configure(text="—")

    def add_voice(self, wav_path, transcript):
        name = simpledialog.askstring("Save Voice","Name for this voice:",initialvalue=Path(wav_path).stem)
        if not name: return
        notes = simpledialog.askstring("Notes","Optional notes (language, speaker, etc.):") or ""
        self.lib.add(name, wav_path, transcript, notes)
        self._refresh()
        messagebox.showinfo("Saved", f"Voice '{name}' saved to library!")


# ── A/B Comparison Panel ───────────────────────────────────────────
class ABComparePanel(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._a_data=None; self._a_sr=44100; self._a_path=None
        self._b_data=None; self._b_sr=44100; self._b_path=None

        top = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=14)
        top.pack(fill="x", pady=(0,8), padx=4)
        ctk.CTkLabel(top, text="🔁  A/B Comparison",
            font=ctk.CTkFont("Segoe UI",15,"bold"), text_color=ACCENT2).pack(anchor="w",padx=14,pady=(10,2))
        ctk.CTkLabel(top, text="Compare two audio clips side by side — reference vs cloned voice.",
            font=ctk.CTkFont("Segoe UI",11), text_color=TEXT_DIM).pack(anchor="w",padx=14,pady=(0,10))

        cols = ctk.CTkFrame(self, fg_color="transparent")
        cols.pack(fill="both", expand=True, padx=4)
        self._sA = self._make_side(cols, "A", "#6C63FF", self._load_a)
        self._sB = self._make_side(cols, "B", "#0EA5E9", self._load_b)

        diff = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=14)
        diff.pack(fill="x", padx=4, pady=(8,0))
        ctk.CTkLabel(diff, text="📊  Difference Metrics",font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=ACCENT2).pack(anchor="w",padx=14,pady=(10,4))
        self.diff_lbl = ctk.CTkLabel(diff, text="Load both A and B to see metrics.",
            font=ctk.CTkFont("Consolas",11), text_color=TEXT_DIM)
        self.diff_lbl.pack(anchor="w", padx=14, pady=(0,10))

    def _make_side(self, parent, letter, color, load_fn):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=14)
        card.pack(side="left", fill="both", expand=True,
            padx=(0,4) if letter=="A" else (4,0))
        ctk.CTkLabel(card, text=f"🎵  Track {letter}",
            font=ctk.CTkFont("Segoe UI",13,"bold"), text_color=color).pack(anchor="w",padx=14,pady=(10,4))
        name_lbl = ctk.CTkLabel(card, text="No file loaded",
            font=ctk.CTkFont("Segoe UI",11), text_color=TEXT_DIM); name_lbl.pack(anchor="w",padx=14)
        wave = Waveform(card, color=color, height=130)
        wave.pack(fill="both", expand=True, padx=14, pady=8)
        stats_lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont("Consolas",10), text_color=TEXT_DIM)
        stats_lbl.pack(anchor="w", padx=14)
        btns = ctk.CTkFrame(card, fg_color="transparent"); btns.pack(fill="x",padx=14,pady=(4,12))
        IconBtn(btns, "📂", f"Load {letter}", command=load_fn, width=120).pack(side="left",padx=(0,6))
        IconBtn(btns, "▶️", "Play", command=lambda: self._play(letter), width=80).pack(side="left")
        return {"name": name_lbl, "wave": wave, "stats": stats_lbl}

    def _pick(self):
        return filedialog.askopenfilename(
            filetypes=[("Audio","*.wav *.mp3 *.flac *.ogg"),("All","*.*")])

    def _load_a(self):
        path = self._pick()
        if not path: return
        data,sr = sf.read(path, dtype="float32", always_2d=False)
        self._a_data=data; self._a_sr=sr; self._a_path=path
        self._sA["wave"].load(data,sr); self._sA["name"].configure(text=Path(path).name,text_color="white")
        self._sA["stats"].configure(text=f"Dur: {fmt_dur(len(data)/sr)}  |  {sr} Hz  |  RMS: {dbfs(data):.1f} dBFS")
        self._refresh_diff()

    def _load_b(self):
        path = self._pick()
        if not path: return
        data,sr = sf.read(path, dtype="float32", always_2d=False)
        self._b_data=data; self._b_sr=sr; self._b_path=path
        self._sB["wave"].load(data,sr); self._sB["name"].configure(text=Path(path).name,text_color="white")
        self._sB["stats"].configure(text=f"Dur: {fmt_dur(len(data)/sr)}  |  {sr} Hz  |  RMS: {dbfs(data):.1f} dBFS")
        self._refresh_diff()

    def _refresh_diff(self):
        if self._a_data is None or self._b_data is None: return
        da=len(self._a_data)/self._a_sr; db=len(self._b_data)/self._b_sr
        ra=dbfs(self._a_data); rb=dbfs(self._b_data)
        self.diff_lbl.configure(text_color=WARNING,
            text=f"Δ Duration: {abs(db-da):.2f}s   |   Δ RMS: {rb-ra:+.1f} dBFS   |   SR-A: {self._a_sr} Hz  ↔  SR-B: {self._b_sr} Hz")

    def _play(self, letter):
        path = self._a_path if letter=="A" else self._b_path
        if not path: return
        if PYGAME_OK:
            def _p(): pygame.mixer.init(); pygame.mixer.music.load(path); pygame.mixer.music.play()
            threading.Thread(target=_p, daemon=True).start()
        else: os.startfile(path)

    def load_output(self, wav_path, data, sr):
        self._b_data=data; self._b_sr=sr; self._b_path=wav_path
        self._sB["wave"].load(data,sr)
        self._sB["name"].configure(text=f"[Generated] {Path(wav_path).name}",text_color=SUCCESS)
        self._sB["stats"].configure(text=f"Dur: {fmt_dur(len(data)/sr)}  |  {sr} Hz  |  RMS: {dbfs(data):.1f} dBFS")
        self._refresh_diff()

    def load_reference(self, wav_path):
        try:
            data,sr=sf.read(wav_path,dtype="float32",always_2d=False)
            self._a_data=data; self._a_sr=sr; self._a_path=wav_path
            self._sA["wave"].load(data,sr)
            self._sA["name"].configure(text=Path(wav_path).name,text_color="white")
            self._sA["stats"].configure(text=f"Dur: {fmt_dur(len(data)/sr)}  |  {sr} Hz  |  RMS: {dbfs(data):.1f} dBFS")
            self._refresh_diff()
        except: pass


# ── Quality Stats Panel ────────────────────────────────────────────
class QualityStatsPanel(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._history=[]

        top = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=14)
        top.pack(fill="x", pady=(0,8), padx=4)
        ctk.CTkLabel(top, text="📊  Quality Statistics",
            font=ctk.CTkFont("Segoe UI",15,"bold"), text_color=ACCENT2).pack(anchor="w",padx=14,pady=(10,2))
        ctk.CTkLabel(top, text="Audio metrics computed automatically after each generation.",
            font=ctk.CTkFont("Segoe UI",11), text_color=TEXT_DIM).pack(anchor="w",padx=14,pady=(0,10))

        meters_row = ctk.CTkFrame(self, fg_color="transparent")
        meters_row.pack(fill="x", padx=4, pady=(0,8))
        self._m = {}
        for key,lbl,unit,col in [("rtf","RTF","lower=faster",ACCENT),
                                   ("dur","Duration","seconds",SUCCESS),
                                   ("rms","RMS Level","dBFS",TEAL),
                                   ("peak","Peak","dBFS",WARNING),
                                   ("sr","Sample Rate","Hz",ACCENT2),
                                   ("zcr","ZCR","per frame",ERROR)]:
            self._m[key] = self._make_meter(meters_row, lbl, unit, col)
        IconBtn(meters_row,"🗑️","Clear",command=self._clear,width=100).pack(side="right",anchor="n",padx=8,pady=4)

        hist = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=14)
        hist.pack(fill="both", expand=True, padx=4)
        ctk.CTkLabel(hist, text="📋  Generation History",font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=ACCENT2).pack(anchor="w",padx=14,pady=(10,4))
        hrow = ctk.CTkFrame(hist, fg_color=BG_INPUT, corner_radius=8)
        hrow.pack(fill="x", padx=14, pady=(0,4))
        for h,w in [("#",28),("Time",80),("RTF",65),("Duration",80),
                    ("RMS dBFS",90),("Peak dBFS",90),("SR",70),("Steps",55),("CFG",50)]:
            ctk.CTkLabel(hrow,text=h,width=w,font=ctk.CTkFont("Consolas",11,"bold"),
                text_color=ACCENT2).pack(side="left",padx=4,pady=4)
        self.hist_frame = ctk.CTkScrollableFrame(hist,fg_color="transparent",corner_radius=0)
        self.hist_frame.pack(fill="both", expand=True, padx=14, pady=(0,10))

    def _make_meter(self, parent, lbl, unit, color):
        card = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=12)
        card.pack(side="left", fill="both", expand=True, padx=(0,6))
        ctk.CTkLabel(card,text=lbl,font=ctk.CTkFont("Segoe UI",10,"bold"),text_color=TEXT_DIM).pack(pady=(8,0),padx=8)
        vl = ctk.CTkLabel(card,text="—",font=ctk.CTkFont("Segoe UI",17,"bold"),text_color=color); vl.pack()
        ctk.CTkLabel(card,text=unit,font=ctk.CTkFont("Segoe UI",9),text_color=TEXT_DIM).pack(pady=(0,8),padx=8)
        return vl

    def update(self, data, sr, rtf, steps, cfg):
        mono = data.mean(axis=1) if data.ndim>1 else data
        dur=len(mono)/sr; rms=dbfs(mono)
        peak=20*np.log10(np.abs(mono).max()+1e-12)
        zcr=float(np.mean(np.abs(np.diff(np.sign(mono))))/2)
        for k,v in [("rtf",f"{rtf:.3f}"),("dur",f"{dur:.2f}"),("rms",f"{rms:.1f}"),
                    ("peak",f"{peak:.1f}"),("sr",f"{sr}"),("zcr",f"{zcr:.3f}")]:
            self._m[k].configure(text=v)
        n=len(self._history)+1; ts=datetime.now().strftime("%H:%M:%S")
        self._history.append((n,ts,rtf,dur,rms,peak,sr,steps,cfg))
        row=ctk.CTkFrame(self.hist_frame,fg_color=BG_INPUT if n%2==0 else "transparent",corner_radius=6)
        row.pack(fill="x", pady=1)
        for val,w in [(n,28),(ts,80),(f"{rtf:.3f}",65),(f"{dur:.2f}s",80),
                      (f"{rms:.1f}",90),(f"{peak:.1f}",90),(f"{sr}",70),(f"{steps}",55),(f"{cfg:.1f}",50)]:
            ctk.CTkLabel(row,text=str(val),width=w,font=ctk.CTkFont("Consolas",10),
                text_color="white").pack(side="left",padx=4,pady=3)

    def _clear(self):
        self._history.clear()
        for w in self.hist_frame.winfo_children(): w.destroy()
        for m in self._m.values(): m.configure(text="—")


# ── Main Application Window ────────────────────────────────────────
class VoxCPMStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🎙️  VoxCPM Voice Cloning Studio v2.0")
        self.geometry("1260x860"); self.minsize(1000,720)
        self.configure(fg_color=BG_DARK)
        self.engine=None; self.model_loaded=False
        self.prompt_wav_path=None; self.output_wav_path=None
        self.output_data=None; self.output_sr=44100
        self._gen_thread=None; self._gen_start=None
        self.library=VoiceLibrary()
        self._build()

    def _build(self):
        hdr = ctk.CTkFrame(self, fg_color=BG_CARD, height=62, corner_radius=0)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr,text="🎙️  VoxCPM Voice Cloning Studio v2",
            font=ctk.CTkFont("Segoe UI",21,"bold"),text_color=ACCENT2).pack(side="left",padx=20)
        self.status_lbl=ctk.CTkLabel(hdr,text="● Model NOT loaded",
            font=ctk.CTkFont("Segoe UI",12),text_color=ERROR); self.status_lbl.pack(side="right",padx=20)
        self.load_btn=ctk.CTkButton(hdr,text="⚡ Load Model",width=148,height=38,
            fg_color=ACCENT,hover_color=ACCENT2,font=ctk.CTkFont("Segoe UI",13,"bold"),
            corner_radius=10,command=self._load_model_t)
        self.load_btn.pack(side="right",padx=(0,10),pady=12)

        self.tabs=ctk.CTkTabview(self,fg_color=BG_DARK,
            segmented_button_fg_color=BG_CARD,segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT2,
            segmented_button_unselected_color=BG_CARD,
            text_color="white",text_color_disabled=TEXT_DIM)
        self.tabs.pack(fill="both",expand=True,padx=10,pady=(6,10))
        for t in ["🎙️  Main","📚  Voice Library","🔁  A/B Compare","📊  Quality Stats"]:
            self.tabs.add(t)
        self._build_main(self.tabs.tab("🎙️  Main"))
        self.lib_panel=VoiceLibraryPanel(self.tabs.tab("📚  Voice Library"),
            self.library,load_cb=self._load_from_lib)
        self.lib_panel.pack(fill="both",expand=True)
        self.ab_panel=ABComparePanel(self.tabs.tab("🔁  A/B Compare"))
        self.ab_panel.pack(fill="both",expand=True)
        self.stats_panel=QualityStatsPanel(self.tabs.tab("📊  Quality Stats"))
        self.stats_panel.pack(fill="both",expand=True)
        self.engine=VoxCPMEngine(log_cb=self.log)

    def _build_main(self, parent):
        body=ctk.CTkFrame(parent,fg_color="transparent"); body.pack(fill="both",expand=True)
        left=ctk.CTkFrame(body,fg_color="transparent",width=310)
        left.pack(side="left",fill="y",padx=(0,8)); left.pack_propagate(False)
        right=ctk.CTkFrame(body,fg_color="transparent"); right.pack(side="left",fill="both",expand=True)
        self._build_left(left); self._build_right(right)

    def _build_left(self, p):
        vc=ctk.CTkFrame(p,fg_color=BG_CARD,corner_radius=14); vc.pack(fill="x",pady=(0,8))
        ctk.CTkLabel(vc,text="🎤  Reference Voice",font=ctk.CTkFont("Segoe UI",13,"bold"),
            text_color=ACCENT2).pack(anchor="w",padx=12,pady=(10,4))
        drop=ctk.CTkFrame(vc,fg_color=BG_INPUT,corner_radius=10,height=70)
        drop.pack(fill="x",padx=12,pady=4); drop.pack_propagate(False)
        self.drop_lbl=ctk.CTkLabel(drop,text="📂  Click to upload\n(.wav / .mp3 / .flac)",
            font=ctk.CTkFont("Segoe UI",11),text_color=TEXT_DIM); self.drop_lbl.pack(expand=True)
        drop.bind("<Button-1>",lambda e:self._upload())
        self.drop_lbl.bind("<Button-1>",lambda e:self._upload())
        r=ctk.CTkFrame(vc,fg_color="transparent"); r.pack(fill="x",padx=12,pady=4)
        IconBtn(r,"📂","Upload",command=self._upload,width=90).pack(side="left",padx=(0,4))
        IconBtn(r,"🔊","Play",command=self._play_ref,width=80).pack(side="left",padx=(0,4))
        IconBtn(r,"💾","Save to Lib",command=self._save_to_lib,width=115).pack(side="left")
        ctk.CTkLabel(vc,text="📝  Reference Transcript:",font=ctk.CTkFont("Segoe UI",11),
            text_color=TEXT_DIM).pack(anchor="w",padx=12,pady=(6,0))
        self.prompt_txt=ctk.CTkTextbox(vc,height=80,fg_color=BG_INPUT,border_color=ACCENT,
            border_width=1,corner_radius=8,font=ctk.CTkFont("Segoe UI",11))
        self.prompt_txt.pack(fill="x",padx=12,pady=(2,4))
        IconBtn(vc,"🤖","Auto-Transcribe",command=self._transcribe_t,width=200).pack(pady=(0,10))
        self.settings=SettingsPanel(p); self.settings.pack(fill="x",pady=(0,8))

    def _build_right(self, p):
        tc=ctk.CTkFrame(p,fg_color=BG_CARD,corner_radius=14); tc.pack(fill="x",pady=(0,8))
        hdr=ctk.CTkFrame(tc,fg_color="transparent"); hdr.pack(fill="x",padx=12,pady=(10,0))
        ctk.CTkLabel(hdr,text="✍️  Text to Synthesize",font=ctk.CTkFont("Segoe UI",13,"bold"),
            text_color=ACCENT2).pack(side="left")
        self.char_lbl=ctk.CTkLabel(hdr,text="0 chars",font=ctk.CTkFont("Segoe UI",10),
            text_color=TEXT_DIM); self.char_lbl.pack(side="right")
        self.text_in=ctk.CTkTextbox(tc,height=110,fg_color=BG_INPUT,border_color=ACCENT,
            border_width=1,corner_radius=8,font=ctk.CTkFont("Segoe UI",13))
        self.text_in.pack(fill="x",padx=12,pady=4)
        self.text_in.bind("<KeyRelease>",
            lambda e:self.char_lbl.configure(text=f"{len(self.text_in.get('1.0','end').strip()):,} chars"))
        tb=ctk.CTkFrame(tc,fg_color="transparent"); tb.pack(fill="x",padx=12,pady=(0,10))
        IconBtn(tb,"🗑️","Clear",command=lambda:self.text_in.delete("1.0","end"),width=88).pack(side="left",padx=(0,6))
        IconBtn(tb,"📋","Paste Transcript",command=self._paste_trans,width=160).pack(side="left")
        self.gen_btn=ctk.CTkButton(p,text="✨  Generate Speech",height=50,
            font=ctk.CTkFont("Segoe UI",15,"bold"),fg_color=ACCENT,hover_color=ACCENT2,
            corner_radius=14,command=self._generate_t); self.gen_btn.pack(fill="x",pady=(0,8))
        self.progress=ctk.CTkProgressBar(p,height=6,progress_color=ACCENT,fg_color=BG_INPUT,corner_radius=3)
        self.progress.set(0); self.progress.pack(fill="x",pady=(0,8))
        oc=ctk.CTkFrame(p,fg_color=BG_CARD,corner_radius=14); oc.pack(fill="both",expand=True,pady=(0,8))
        oh=ctk.CTkFrame(oc,fg_color="transparent"); oh.pack(fill="x",padx=12,pady=(10,0))
        ctk.CTkLabel(oh,text="🔊  Output Waveform",font=ctk.CTkFont("Segoe UI",13,"bold"),
            text_color=ACCENT2).pack(side="left")
        self.dur_lbl=ctk.CTkLabel(oh,text="",font=ctk.CTkFont("Segoe UI",10),
            text_color=TEXT_DIM); self.dur_lbl.pack(side="right")
        self.out_wave=Waveform(oc,color=ACCENT,height=110)
        self.out_wave.pack(fill="both",expand=True,padx=12,pady=8)
        ob=ctk.CTkFrame(oc,fg_color="transparent"); ob.pack(fill="x",padx=12,pady=(0,10))
        IconBtn(ob,"▶️","Play Output",command=self._play_out,width=130).pack(side="left",padx=(0,6))
        IconBtn(ob,"⏹️","Stop",command=self._stop,width=80).pack(side="left",padx=(0,6))
        IconBtn(ob,"💾","Save As",command=self._save_out,width=100).pack(side="left",padx=(0,6))
        IconBtn(ob,"🔁","→ A/B",command=self._push_to_ab,width=90).pack(side="left")
        self.log_panel=LogPanel(p); self.log_panel.pack(fill="x")
        self.log=self.log_panel.log

    # ── Model ──────────────────────────────────────────────────────
    def _load_model_t(self):
        if self.model_loaded: return messagebox.showinfo("Info","Already loaded.")
        self.load_btn.configure(state="disabled",text="⏳ Loading…")
        threading.Thread(target=self._load_model_w,daemon=True).start()

    def _load_model_w(self):
        try:
            local=self.settings.local_path.get().strip()
            hf=self.settings.model_id.get().strip() or "openbmb/VoxCPM1.5"
            self.engine.load_tts(model_path=local or None,hf_id=hf if not local else None)
            self.engine.load_asr()
            self.model_loaded=True
            self.after(0,lambda:(
                self.status_lbl.configure(text="● Model READY",text_color=SUCCESS),
                self.load_btn.configure(state="normal",text="✅ Loaded",fg_color=SUCCESS),
                self.log("🎉 All models ready!")))
        except Exception as e:
            self.log(f"❌ {e}\n{traceback.format_exc()}")
            self.after(0,lambda:self.load_btn.configure(state="normal",text="⚡ Load Model"))

    # ── Upload & transcribe ────────────────────────────────────────
    def _upload(self):
        path=filedialog.askopenfilename(title="Reference audio",
            filetypes=[("Audio","*.wav *.mp3 *.flac *.ogg *.m4a"),("All","*.*")])
        if not path: return
        self.prompt_wav_path=path
        self.drop_lbl.configure(text=f"✅  {Path(path).name}",text_color=SUCCESS)
        self.log(f"📂 Reference: {Path(path).name}")
        self.ab_panel.load_reference(path)

    def _transcribe_t(self):
        if not self.prompt_wav_path: return messagebox.showwarning("!","Upload audio first.")
        if not self.model_loaded: return messagebox.showwarning("!","Load model first.")
        self.log("🤖 Transcribing…")
        def _w():
            txt=self.engine.transcribe(self.prompt_wav_path)
            self.after(0,lambda:(self.prompt_txt.delete("1.0","end"),
                self.prompt_txt.insert("1.0",txt),
                self.log(f"📝 Transcript ready ({len(txt)} chars)")))
        threading.Thread(target=_w,daemon=True).start()

    def _paste_trans(self):
        t=self.prompt_txt.get("1.0","end").strip()
        if t: self.text_in.delete("1.0","end"); self.text_in.insert("1.0",t)

    # ── Generation ─────────────────────────────────────────────────
    def _generate_t(self):
        txt=self.text_in.get("1.0","end").strip()
        if not txt: return messagebox.showwarning("!","Enter text first.")
        if not self.model_loaded: return messagebox.showwarning("!","Load model first.")
        if self._gen_thread and self._gen_thread.is_alive(): return
        self.gen_btn.configure(state="disabled",text="⏳ Generating…")
        self.progress.set(0); self._anim()
        self._gen_start=time.time()
        self._gen_thread=threading.Thread(target=self._generate_w,args=(txt,),daemon=True)
        self._gen_thread.start()

    def _anim(self):
        if self._gen_thread and self._gen_thread.is_alive():
            self.progress.set((self.progress.get()+0.008)%1.0); self.after(30,self._anim)
        else: self.progress.set(1.0)

    def _generate_w(self, text):
        try:
            ptxt=self.prompt_txt.get("1.0","end").strip() or None
            cfg=self.settings.cfg; steps=self.settings.steps
            self.log(f"✨ Generating | cfg={cfg} steps={steps}")
            wav=self.engine.synthesize(text,self.prompt_wav_path,ptxt,cfg,steps,
                bool(self.settings.normalize.get()),bool(self.settings.denoise.get()))
            if wav is not None and len(wav)>0:
                sr=self.engine.sample_rate; elapsed=time.time()-self._gen_start
                dur=len(wav)/sr; rtf=elapsed/dur
                tmp=tempfile.NamedTemporaryFile(suffix=".wav",delete=False)
                sf.write(tmp.name,wav,sr)
                self.output_wav_path=tmp.name; self.output_data=wav; self.output_sr=sr
                self.log(f"✅ Done {fmt_dur(dur)} | RTF={rtf:.3f}")
                self.after(0,lambda w=wav,s=sr,r=rtf,st=steps,c=cfg:(
                    self.out_wave.load(w,s),
                    self.dur_lbl.configure(text=f"{fmt_dur(len(w)/s)} | {s} Hz | RTF {r:.3f}"),
                    self.gen_btn.configure(state="normal",text="✨  Generate Speech"),
                    self.progress.set(1.0),
                    self.stats_panel.update(w,s,r,st,c),
                    self.ab_panel.load_output(tmp.name,w,s)))
            else:
                self.log("⚠️ Empty output")
                self.after(0,lambda:self.gen_btn.configure(state="normal",text="✨  Generate Speech"))
        except Exception as e:
            self.log(f"❌ {e}\n{traceback.format_exc()}")
            self.after(0,lambda:self.gen_btn.configure(state="normal",text="✨  Generate Speech"))

    # ── Audio playback ─────────────────────────────────────────────
    def _play(self, path):
        if not path: return
        if PYGAME_OK:
            def _p(): pygame.mixer.init(); pygame.mixer.music.load(path); pygame.mixer.music.play()
            threading.Thread(target=_p,daemon=True).start()
        else: os.startfile(path)

    def _play_ref(self):
        if self.prompt_wav_path: self._play(self.prompt_wav_path)
        else: messagebox.showwarning("!","Upload reference first.")

    def _play_out(self):
        if self.output_wav_path: self._play(self.output_wav_path)
        else: messagebox.showwarning("!","Generate audio first.")

    def _stop(self):
        if PYGAME_OK:
            try: pygame.mixer.music.stop()
            except: pass
        if SD_OK: sd.stop()

    def _save_out(self):
        if self.output_data is None: return messagebox.showwarning("!","Generate audio first.")
        p=filedialog.asksaveasfilename(defaultextension=".wav",filetypes=[("WAV","*.wav")])
        if p: sf.write(p,self.output_data,self.output_sr); self.log(f"💾 Saved: {p}")

    def _push_to_ab(self):
        if self.output_data is None: return messagebox.showwarning("!","Generate audio first.")
        self.ab_panel.load_output(self.output_wav_path,self.output_data,self.output_sr)
        self.tabs.set("🔁  A/B Compare"); self.log("🔁 Sent to A/B Compare tab")

    def _save_to_lib(self):
        if not self.prompt_wav_path: return messagebox.showwarning("!","Upload reference first.")
        transcript=self.prompt_txt.get("1.0","end").strip()
        self.tabs.set("📚  Voice Library")
        self.lib_panel.add_voice(self.prompt_wav_path,transcript)

    def _load_from_lib(self, wav_path, transcript):
        self.prompt_wav_path=wav_path
        self.drop_lbl.configure(text=f"✅  {Path(wav_path).name} (library)",text_color=SUCCESS)
        self.prompt_txt.delete("1.0","end"); self.prompt_txt.insert("1.0",transcript)
        self.log(f"📚 Loaded from library: {Path(wav_path).name}")
        self.tabs.set("🎙️  Main")


if __name__ == "__main__":
    app = VoxCPMStudio()
    app.mainloop()
