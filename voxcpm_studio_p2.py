
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

        # Left list
        left = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=14, width=270)
        left.pack(side="left", fill="y", padx=(0,8)); left.pack_propagate(False)
        ctk.CTkLabel(left, text="Saved Voices", font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=ACCENT2).pack(anchor="w", padx=12, pady=(10,4))
        self.vlist = tk.Listbox(left, bg="#0A0A1A", fg="#C0C0E0",
            selectbackground=ACCENT, selectforeground="white",
            font=("Segoe UI",12), bd=0, highlightthickness=0, activestyle="none")
        self.vlist.pack(fill="both", expand=True, padx=8, pady=(0,4))
        self.vlist.bind("<<ListboxSelect>>", self._on_select)
        lbtns = ctk.CTkFrame(left, fg_color="transparent")
        lbtns.pack(fill="x", padx=8, pady=(0,8))
        IconBtn(lbtns, "🗑️", "Delete", command=self._delete, width=120).pack()

        # Right detail
        right = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=14)
        right.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(right, text="Voice Details", font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=ACCENT2).pack(anchor="w", padx=14, pady=(10,4))
        info = ctk.CTkFrame(right, fg_color="transparent"); info.pack(fill="x", padx=14)
        ctk.CTkLabel(info, text="Name:", width=90, font=ctk.CTkFont("Segoe UI",11),
            text_color=TEXT_DIM).pack(side="left")
        self.name_lbl = ctk.CTkLabel(info, text="—",
            font=ctk.CTkFont("Segoe UI",11,"bold"), text_color="white")
        self.name_lbl.pack(side="left")
        info2 = ctk.CTkFrame(right, fg_color="transparent"); info2.pack(fill="x", padx=14, pady=4)
        ctk.CTkLabel(info2, text="Added:", width=90, font=ctk.CTkFont("Segoe UI",11),
            text_color=TEXT_DIM).pack(side="left")
        self.date_lbl = ctk.CTkLabel(info2, text="—",
            font=ctk.CTkFont("Segoe UI",11), text_color=TEXT_DIM)
        self.date_lbl.pack(side="left")
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
        for n in self.lib.names():
            self.vlist.insert("end", f"  🎤  {n}")

    def _on_select(self, _=None):
        idx = self.vlist.curselection()
        if not idx: return
        name = self.lib.names()[idx[0]]; self._sel_name = name
        entry = self.lib.get(name)
        self.name_lbl.configure(text=name)
        self.date_lbl.configure(text=entry.get("added","?")[:10])
        self.trans_box.configure(state="normal")
        self.trans_box.delete("1.0","end")
        self.trans_box.insert("1.0", entry.get("transcript",""))
        self.trans_box.configure(state="disabled")
        self.notes_box.delete("1.0","end")
        self.notes_box.insert("1.0", entry.get("notes",""))
        wav_path = entry.get("wav","")
        if wav_path and Path(wav_path).exists():
            try: d,sr=sf.read(wav_path,dtype="float32",always_2d=False); self.prev_wave.load(d,sr)
            except: self.prev_wave.clear()
        else: self.prev_wave.clear()

    def _play(self):
        if not self._sel_name: return
        entry=self.lib.get(self._sel_name); wav=entry.get("wav","") if entry else None
        if wav and Path(wav).exists():
            if PYGAME_OK:
                def _p(): pygame.mixer.init(); pygame.mixer.music.load(wav); pygame.mixer.music.play()
                threading.Thread(target=_p, daemon=True).start()
            else: os.startfile(wav)

    def _load_to_main(self):
        if not self._sel_name: return
        entry=self.lib.get(self._sel_name)
        if entry and self.load_cb:
            self.load_cb(entry["wav"], entry["transcript"])

    def _delete(self):
        if not self._sel_name: return
        if messagebox.askyesno("Delete", f"Delete voice '{self._sel_name}'?"):
            self.lib.remove(self._sel_name); self._sel_name=None; self._refresh()
            self.prev_wave.clear(); self.name_lbl.configure(text="—")

    def add_voice(self, wav_path, transcript):
        name = simpledialog.askstring("Save Voice", "Name for this voice:", initialvalue=Path(wav_path).stem)
        if not name: return
        notes = simpledialog.askstring("Notes", "Optional notes (language, speaker, etc.):") or ""
        self.lib.add(name, wav_path, transcript, notes)
        self._refresh()
        messagebox.showinfo("Saved", f"Voice '{name}' saved to library!")


# ── A/B Comparison Panel ───────────────────────────────────────────
class ABComparePanel(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._a_data=None; self._a_sr=44100; self._a_path=None
        self._b_data=None; self._b_sr=44100; self._b_path=None

        top=ctk.CTkFrame(self,fg_color=BG_CARD,corner_radius=14)
        top.pack(fill="x",pady=(0,8),padx=4)
        ctk.CTkLabel(top,text="🔁  A/B Comparison",
            font=ctk.CTkFont("Segoe UI",15,"bold"),text_color=ACCENT2).pack(anchor="w",padx=14,pady=(10,2))
        ctk.CTkLabel(top,text="Compare two audio clips side by side — e.g. reference vs cloned voice.",
            font=ctk.CTkFont("Segoe UI",11),text_color=TEXT_DIM).pack(anchor="w",padx=14,pady=(0,10))

        cols=ctk.CTkFrame(self,fg_color="transparent")
        cols.pack(fill="both",expand=True,padx=4)
        self._sA=self._make_side(cols,"A","#6C63FF",self._load_a)
        self._sB=self._make_side(cols,"B","#0EA5E9",self._load_b)

        diff=ctk.CTkFrame(self,fg_color=BG_CARD,corner_radius=14)
        diff.pack(fill="x",padx=4,pady=(8,0))
        ctk.CTkLabel(diff,text="📊  Difference Metrics",font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=ACCENT2).pack(anchor="w",padx=14,pady=(10,4))
        self.diff_lbl=ctk.CTkLabel(diff,text="Load both A and B to see metrics.",
            font=ctk.CTkFont("Consolas",11),text_color=TEXT_DIM)
        self.diff_lbl.pack(anchor="w",padx=14,pady=(0,10))

    def _make_side(self, parent, letter, color, load_fn):
        card=ctk.CTkFrame(parent,fg_color=BG_CARD,corner_radius=14)
        card.pack(side="left",fill="both",expand=True,padx=(0,4) if letter=="A" else (4,0))
        ctk.CTkLabel(card,text=f"🎵  Track {letter}",
            font=ctk.CTkFont("Segoe UI",13,"bold"),text_color=color).pack(anchor="w",padx=14,pady=(10,4))
        name_lbl=ctk.CTkLabel(card,text="No file loaded",
            font=ctk.CTkFont("Segoe UI",11),text_color=TEXT_DIM); name_lbl.pack(anchor="w",padx=14)
        wave=Waveform(card,color=color,height=130)
        wave.pack(fill="both",expand=True,padx=14,pady=8)
        stats_lbl=ctk.CTkLabel(card,text="",font=ctk.CTkFont("Consolas",10),text_color=TEXT_DIM)
        stats_lbl.pack(anchor="w",padx=14)
        btns=ctk.CTkFrame(card,fg_color="transparent"); btns.pack(fill="x",padx=14,pady=(4,12))
        IconBtn(btns,f"📂",f"Load {letter}",command=load_fn,width=120).pack(side="left",padx=(0,6))
        IconBtn(btns,"▶️","Play",command=lambda:self._play(letter),width=80).pack(side="left")
        return {"name":name_lbl,"wave":wave,"stats":stats_lbl}

    def _pick_file(self):
        return filedialog.askopenfilename(
            filetypes=[("Audio","*.wav *.mp3 *.flac *.ogg"),("All","*.*")])

    def _load_a(self):
        path=self._pick_file()
        if not path: return
        data,sr=sf.read(path,dtype="float32",always_2d=False)
        self._a_data=data; self._a_sr=sr; self._a_path=path
        self._sA["wave"].load(data,sr); self._sA["name"].configure(text=Path(path).name,text_color="white")
        self._sA["stats"].configure(text=f"Duration: {fmt_dur(len(data)/sr)}  |  {sr} Hz  |  RMS: {dbfs(data):.1f} dBFS")
        self._refresh_diff()

    def _load_b(self):
        path=self._pick_file()
        if not path: return
        data,sr=sf.read(path,dtype="float32",always_2d=False)
        self._b_data=data; self._b_sr=sr; self._b_path=path
        self._sB["wave"].load(data,sr); self._sB["name"].configure(text=Path(path).name,text_color="white")
        self._sB["stats"].configure(text=f"Duration: {fmt_dur(len(data)/sr)}  |  {sr} Hz  |  RMS: {dbfs(data):.1f} dBFS")
        self._refresh_diff()

    def _refresh_diff(self):
        if self._a_data is None or self._b_data is None: return
        da=len(self._a_data)/self._a_sr; db=len(self._b_data)/self._b_sr
        ra=dbfs(self._a_data); rb=dbfs(self._b_data)
        self.diff_lbl.configure(text_color=WARNING,
            text=f"Δ Duration: {abs(db-da):.2f}s   |   Δ RMS: {rb-ra:+.1f} dBFS   |   SR A: {self._a_sr} Hz  ↔  SR B: {self._b_sr} Hz")

    def _play(self, letter):
        path=self._a_path if letter=="A" else self._b_path
        if not path: return
        if PYGAME_OK:
            def _p(): pygame.mixer.init(); pygame.mixer.music.load(path); pygame.mixer.music.play()
            threading.Thread(target=_p,daemon=True).start()
        else: os.startfile(path)

    def load_output(self, wav_path, data, sr):
        self._b_data=data; self._b_sr=sr; self._b_path=wav_path
        self._sB["wave"].load(data,sr)
        self._sB["name"].configure(text=f"[Generated] {Path(wav_path).name}",text_color=SUCCESS)
        self._sB["stats"].configure(text=f"Duration: {fmt_dur(len(data)/sr)}  |  {sr} Hz  |  RMS: {dbfs(data):.1f} dBFS")
        self._refresh_diff()

    def load_reference(self, wav_path):
        try:
            data,sr=sf.read(wav_path,dtype="float32",always_2d=False)
            self._a_data=data; self._a_sr=sr; self._a_path=wav_path
            self._sA["wave"].load(data,sr)
            self._sA["name"].configure(text=Path(wav_path).name,text_color="white")
            self._sA["stats"].configure(text=f"Duration: {fmt_dur(len(data)/sr)}  |  {sr} Hz  |  RMS: {dbfs(data):.1f} dBFS")
            self._refresh_diff()
        except: pass


# ── Quality Stats Panel ────────────────────────────────────────────
class QualityStatsPanel(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._history=[]

        top=ctk.CTkFrame(self,fg_color=BG_CARD,corner_radius=14)
        top.pack(fill="x",pady=(0,8),padx=4)
        ctk.CTkLabel(top,text="📊  Quality Statistics",
            font=ctk.CTkFont("Segoe UI",15,"bold"),text_color=ACCENT2).pack(anchor="w",padx=14,pady=(10,2))
        ctk.CTkLabel(top,text="Metrics computed automatically after each generation.",
            font=ctk.CTkFont("Segoe UI",11),text_color=TEXT_DIM).pack(anchor="w",padx=14,pady=(0,10))

        meters_row=ctk.CTkFrame(self,fg_color="transparent")
        meters_row.pack(fill="x",padx=4,pady=(0,8))
        self._m={}
        specs=[("rtf","RTF","lower=faster",ACCENT),("dur","Duration","seconds",SUCCESS),
               ("rms","RMS Level","dBFS",TEAL),("peak","Peak","dBFS",WARNING),
               ("sr","Sample Rate","Hz",ACCENT2),("zcr","ZCR","per frame",ERROR)]
        for key,lbl,unit,col in specs:
            self._m[key]=self._make_meter(meters_row,lbl,unit,col)

        IconBtn(meters_row,"🗑️","Clear",command=self._clear,width=110).pack(side="right",anchor="n",padx=8,pady=4)

        hist=ctk.CTkFrame(self,fg_color=BG_CARD,corner_radius=14)
        hist.pack(fill="both",expand=True,padx=4)
        ctk.CTkLabel(hist,text="📋  Generation History",font=ctk.CTkFont("Segoe UI",12,"bold"),
            text_color=ACCENT2).pack(anchor="w",padx=14,pady=(10,4))
        hdr_row=ctk.CTkFrame(hist,fg_color=BG_INPUT,corner_radius=8)
        hdr_row.pack(fill="x",padx=14,pady=(0,4))
        for h,w in [("#",28),("Time",80),("RTF",65),("Duration",80),
                    ("RMS dBFS",90),("Peak dBFS",90),("SR",70),("Steps",55),("CFG",50)]:
            ctk.CTkLabel(hdr_row,text=h,width=w,font=ctk.CTkFont("Consolas",11,"bold"),
                text_color=ACCENT2).pack(side="left",padx=4,pady=4)
        self.hist_frame=ctk.CTkScrollableFrame(hist,fg_color="transparent",corner_radius=0)
        self.hist_frame.pack(fill="both",expand=True,padx=14,pady=(0,10))

    def _make_meter(self, parent, lbl, unit, color):
        card=ctk.CTkFrame(parent,fg_color=BG_CARD,corner_radius=12)
        card.pack(side="left",fill="both",expand=True,padx=(0,6))
        ctk.CTkLabel(card,text=lbl,font=ctk.CTkFont("Segoe UI",10,"bold"),
            text_color=TEXT_DIM).pack(pady=(8,0),padx=8)
        vl=ctk.CTkLabel(card,text="—",font=ctk.CTkFont("Segoe UI",17,"bold"),text_color=color)
        vl.pack()
        ctk.CTkLabel(card,text=unit,font=ctk.CTkFont("Segoe UI",9),
            text_color=TEXT_DIM).pack(pady=(0,8),padx=8)
        return vl

    def update(self, data, sr, rtf, steps, cfg):
        mono=data.mean(axis=1) if data.ndim>1 else data
        dur=len(mono)/sr; rms=dbfs(mono)
        peak=20*np.log10(np.abs(mono).max()+1e-12)
        zcr=float(np.mean(np.abs(np.diff(np.sign(mono))))/2)
        self._m["rtf"].configure(text=f"{rtf:.3f}")
        self._m["dur"].configure(text=f"{dur:.2f}")
        self._m["rms"].configure(text=f"{rms:.1f}")
        self._m["peak"].configure(text=f"{peak:.1f}")
        self._m["sr"].configure(text=f"{sr}")
        self._m["zcr"].configure(text=f"{zcr:.3f}")
        n=len(self._history)+1; ts=datetime.now().strftime("%H:%M:%S")
        self._history.append((n,ts,rtf,dur,rms,peak,sr,steps,cfg))
        row=ctk.CTkFrame(self.hist_frame,fg_color=BG_INPUT if n%2==0 else "transparent",corner_radius=6)
        row.pack(fill="x",pady=1)
        for val,w in [(n,28),(ts,80),(f"{rtf:.3f}",65),(f"{dur:.2f}s",80),
                      (f"{rms:.1f}",90),(f"{peak:.1f}",90),(f"{sr}",70),(f"{steps}",55),(f"{cfg:.1f}",50)]:
            ctk.CTkLabel(row,text=str(val),width=w,font=ctk.CTkFont("Consolas",10),
                text_color="white").pack(side="left",padx=4,pady=3)

    def _clear(self):
        self._history.clear()
        for w in self.hist_frame.winfo_children(): w.destroy()
        for m in self._m.values(): m.configure(text="—")


# ── Main Application ───────────────────────────────────────────────
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
        hdr=ctk.CTkFrame(self,fg_color=BG_CARD,height=62,corner_radius=0)
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

    # ── Reference audio ────────────────────────────────────────────
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
        def _worker():
            txt=self.engine.transcribe(self.prompt_wav_path)
            self.after(0,lambda:(
                self.prompt_txt.delete("1.0","end"),
                self.prompt_txt.insert("1.0",txt),
                self.log(f"📝 Transcript ready ({len(txt)} chars)")))
        threading.Thread(target=_worker,daemon=True).start()

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
                sr=self.engine.sample_rate
                elapsed=time.time()-self._gen_start
                dur=len(wav)/sr; rtf=elapsed/dur
                tmp=tempfile.NamedTemporaryFile(suffix=".wav",delete=False)
                sf.write(tmp.name,wav,sr)
                self.output_wav_path=tmp.name; self.output_data=wav; self.output_sr=sr
                self.log(f"✅ Done {fmt_dur(dur)} | RTF={rtf:.3f}")
                self.after(0,lambda w=wav,s=sr,r=rtf:(
                    self.out_wave.load(w,s),
                    self.dur_lbl.configure(text=f"{fmt_dur(len(w)/s)} | {s} Hz | RTF {r:.3f}"),
                    self.gen_btn.configure(state="normal",text="✨  Generate Speech"),
                    self.progress.set(1.0),
                    self.stats_panel.update(w,s,r,steps,cfg),
                    self.ab_panel.load_output(tmp.name,w,s)))
            else:
                self.log("⚠️ Empty output")
                self.after(0,lambda:self.gen_btn.configure(state="normal",text="✨  Generate Speech"))
        except Exception as e:
            self.log(f"❌ {e}\n{traceback.format_exc()}")
            self.after(0,lambda:self.gen_btn.configure(state="normal",text="✨  Generate Speech"))

    # ── Playback ───────────────────────────────────────────────────
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
        self.lib_panel.add_voice(self.prompt_wav_path, transcript)

    def _load_from_lib(self, wav_path, transcript):
        self.prompt_wav_path=wav_path
        self.drop_lbl.configure(text=f"✅  {Path(wav_path).name} (library)",text_color=SUCCESS)
        self.prompt_txt.delete("1.0","end"); self.prompt_txt.insert("1.0",transcript)
        self.log(f"📚 Loaded from library: {Path(wav_path).name}")
        self.tabs.set("🎙️  Main")


if __name__ == "__main__":
    app = VoxCPMStudio()
    app.mainloop()
