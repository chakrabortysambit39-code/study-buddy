# Study Buddy V10 Tutor Engine

Free/open-source prototype for a conversational photorealistic AI teacher.

## Goal

Student speaks naturally -> speech recognition -> Study Buddy/Groq decides a short response -> TTS creates audio -> real-time avatar lip-syncs -> browser receives the stream. The tutor should listen continuously and stop speaking when the student interrupts.

## Hardware plan

The student's Ryzen 3 5300U + integrated Radeon is not suitable for real-time avatar inference. The GPU inference stage will run on a temporary cloud GPU for the prototype. The laptop remains the browser/control device.

## Open-source stack

- LiveTalking: real-time digital-human/WebRTC engine
- Wav2Lip first: lower GPU requirement and easiest first milestone
- MuseTalk 1.5 later: higher-quality lip-sync
- Browser microphone / speech input
- Groq for Study Buddy's existing AI brain
- Free/local TTS where practical

LiveTalking documents support for Wav2Lip, MuseTalk, WebRTC, interruption, custom avatars, and education/training. Its current README reports Wav2Lip around 60 FPS on an RTX 3060 and recommends an RTX 3080 Ti+ for MuseTalk real-time use.

## Milestones

1. Get a cloud NVIDIA GPU and prove Wav2Lip can speak.
2. Add microphone input and interruption.
3. Connect Groq and Grade/Subject/Topic context.
4. Upgrade the avatar engine to MuseTalk 1.5.
5. Expose a small WebRTC/API bridge.
6. Connect `/ai-face` in Study Buddy to the tutor engine.

## Important

Do not put model weights or API keys into GitHub. Store secrets in the runtime environment.

## Prototype

Open `tutor-engine/colab_tutor.ipynb` in Google Colab. Colab provides free GPU access, but free sessions are temporary; this notebook is for testing, not permanent hosting.

References:
- https://github.com/lipku/LiveTalking
- https://github.com/TMElyralab/MuseTalk
