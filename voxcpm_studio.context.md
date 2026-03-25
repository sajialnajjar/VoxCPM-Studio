# VoxCPM Studio Overview
The main GUI application for zero-shot voice cloning and text-to-speech synthesis using OpenBMB VoxCPM. This application provides a full-featured interface for uploading reference audio, automatic transcription, voice cloning, and audio waveform visualization.

## UI Description
- **Main Layout**: Uses `customtkinter` for a modern dark-mode GUI.
- **Header**: Title and sub-title.
- **Reference Audio Panel**: Upload audio, auto-transcribe button, play button, waveform display.
- **Text to Speech Panel**: Text area for input text, generate button.
- **Model Status Panel**: Loading model button, VRAM usage, status indicator.
- **Activity Log**: Real-time status updates and execution times.
- **Output Panel**: Waveform visualization, play, and export buttons.

## Logic
- **Audio Processing**: Handles `.wav`, `.mp3`, `.flac` loading. Normalizes and pads audio for the model.
- **Transcription**: Uses SenseVoice (via `funasr`) with a fallback to `faster-whisper`.
- **Inference**: Uses the VoxCPM `TTSModel` for audio synthesis. Supports parameter tuning like CFG, steps, and denoising.

## Data Flow
1. User uploads reference audio -> Audio is loaded into a NumPy array -> Displayed in UI.
2. User clicks Auto-Transcribe -> Audio sent to ASR model -> Transcript appears in UI.
3. User enters target text.
4. User clicks Generate -> Reference audio, transcript, and target text are sent to the VoxCPM `TTSModel.inference()` -> Output audio generated.
5. Output audio -> Displayed in waveform -> Made available for playback saving.

## Dependencies
- `customtkinter`, `soundfile`, `numpy`, `pygame`
- `voxcpm` (TTS model)
- `funasr`, `faster-whisper` (ASR models)

## State Management
- GUI state is stored in class attributes (e.g., `self.ref_audio`, `self.ref_sr`, `self.out_audio`).
- Pygame mixer is used for managing audio playback states.

## Known Issues / Notes
- First-time execution requires downloading substantial model weights.
- GPU with CUDA is highly recommended for reasonable generation speeds.

### Changelog
- [2026-03-25] - Created context file as part of project preparation for GitHub.
