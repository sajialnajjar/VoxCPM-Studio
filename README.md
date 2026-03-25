# 🎙️ VoxCPM Voice Cloning Studio

A beautiful, full-featured **Python GUI application** for zero-shot voice cloning and
text-to-speech synthesis using [OpenBMB VoxCPM](https://github.com/OpenBMB/VoxCPM).

---

## ✨ Features

| Feature | Description |
|---|---|
| 📂 **Audio Upload** | Upload any `.wav / .mp3 / .flac` reference audio |
| 🤖 **Auto-Transcription** | Automatically convert reference audio → text (SenseVoice or Whisper) |
| 🎤 **Voice Cloning** | Clone any voice with a short reference clip |
| ✍️ **TTS Synthesis** | Type new text and generate it in the cloned voice |
| 📊 **Waveform Viewer** | Live waveform visualisation of output audio |
| ⚙️ **Parameter Tuning** | CFG value, inference steps, normalize, denoise, streaming mode |
| 💾 **Export Audio** | Save synthesised audio as `.wav` |
| 🔊 **Playback** | Play reference and output audio inside the app |
| 📋 **Activity Log** | Real-time status and log panel |

---

## 🗂️ Files in This Project

```
VoxCPM-Studio/
├── voxcpm_studio.py    ← Main GUI application  ⬅ run this
├── requirements.txt    ← All dependencies
├── setup_venv.bat      ← Creates venv + installs packages (run ONCE)
└── run_studio.bat      ← Launches the app (run each time)
```

---

## 🚀 Quick Start

### Step 1 — Run the setup script (only once)

Double-click **`setup_venv.bat`**  
This script will:
1. Find your Python 3.10 installation
2. Create a virtual environment at `venv\`
3. Install all required packages

> ⚠️ **This may take 10–30 minutes** on first run because PyTorch and model weights are large.

### Step 2 — Launch the app

Double-click **`run_studio.bat`**

---

## 📦 Package List & Why Each Is Needed

| Package | Why |
|---|---|
| `voxcpm` | The core TTS + voice cloning engine |
| `customtkinter` | Modern dark-mode GUI framework |
| `Pillow` | Image loading (required by customtkinter) |
| `soundfile` | Read/write WAV audio files |
| `numpy` | Array operations for audio data |
| `pygame` | In-app audio playback |
| `sounddevice` | Alternative audio playback |
| `funasr` | SenseVoice ASR for auto-transcription |
| `modelscope` | Download SenseVoice model automatically |
| `faster-whisper` | Fallback ASR if SenseVoice unavailable |
| `huggingface-hub` | Download VoxCPM model weights |

---

## 🖥️ Manual Installation (PowerShell)

If you prefer to run commands yourself:

```powershell
# 1. Create venv with Python 3.10
python -m venv venv

# 2. Activate it
.\venv\Scripts\Activate.ps1

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install packages
pip install -r requirements.txt

# 5. Launch
python voxcpm_studio.py
```

---

## 🧭 How to Use

1. **Click "⚡ Load Model"** — downloads/loads VoxCPM1.5 (first time: ~2 GB download)
2. **Upload reference audio** — any short voice clip (5–30 seconds works best)
3. **Click "🤖 Auto-Transcribe"** — fills the transcript field automatically
4. **Type your text** — what you want the cloned voice to say
5. **Click "✨ Generate Speech"** — sit back and wait
6. **Play or save** the output

---

## 💡 Suggested Future Features

Here are ideas you can add later:

1. **🌐 Multi-language support** — detect language automatically and switch TTS mode
2. **📖 Script / SRT dubbing** — feed a subtitle file, dub each line in the cloned voice
3. **🎚️ Emotion & speed sliders** — control speaking pace, pitch, emotion via SSML
4. **📊 Quality dashboard** — display RTF, DNSMOS score, speaker similarity score
5. **☁️ Voice library** — save/reload named voice profiles
6. **🔁 A/B comparison** — compare original vs cloned audio side-by-side
7. **🎧 Binaural / 3D audio** — add spatial audio post-processing
8. **📋 Batch mode** — read lines from a `.txt` file and generate all at once
9. **🎛️ EQ / reverb panel** — post-process output with audio effects
10. **🔌 REST API server** — expose generation as an HTTP endpoint for integrations

---

## ⚠️ Notes

- VoxCPM is optimised for **Chinese and English**. Quality in other languages may vary.
- Voice cloning can generate realistic audio — use responsibly and ethically.
- GPU (NVIDIA CUDA) is strongly recommended; CPU inference is possible but slow.
- First launch downloads ~2–5 GB of model weights from Hugging Face.
