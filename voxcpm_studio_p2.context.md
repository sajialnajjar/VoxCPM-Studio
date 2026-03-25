# VoxCPM Studio Part 2 Overview
A supplementary or alternate version of the VoxCPM Voice Cloning Studio. It contains iterations or additional features for the voice cloning process.

## UI Description
- Similar to the main `voxcpm_studio.py` application, built with `customtkinter`.
- Includes panels for Reference Audio, Text to Speech, Model Status, and Output.

## Logic
- Handles voice cloning and text-to-speech generation.
- Audio loading, transcription, and TTS inference logic.

## Data Flow
- Reference audio -> UI waveform -> Transcription -> Generation -> Output audio.

## Dependencies
- `customtkinter`, `soundfile`, `numpy`, `pygame`
- `voxcpm`, `funasr`, `faster-whisper`

## State Management
- Instance variables manage the current loaded audio, metadata, and generated outputs.

## Known Issues / Notes
- Differs from the main application potentially in layout or experimental features. Should be merged or maintained separately based on usage.

### Changelog
- [2026-03-25] - Created context file as part of project preparation for GitHub.
