# Study Buddy V11 — simpler avatar path

V11 replaces the LiveTalking/WebRTC experiment for the first visual milestone with the official **KlingAIResearch/LivePortrait** project.

## Why

The previous LiveTalking prototype successfully loaded Wav2Lip on a T4, but exposing its WebRTC media from Colab introduced unnecessary TCP/UDP networking work. V11 uses LivePortrait's Gradio interface with `--share`, so the first goal is simply to see the animated teacher in a browser.

## Run

Open `tutor-engine/liveportrait_v11.ipynb` in Google Colab, select a GPU runtime, and run the cells in order.

The notebook:

1. checks the NVIDIA GPU;
2. clones the official LivePortrait repository;
3. installs its dependencies;
4. downloads the official `KlingTeam/LivePortrait` pretrained weights;
5. launches the human Gradio interface with a temporary public share URL.

## Next

Once the visual avatar works, V12 will add the conversational layer:

`microphone → speech recognition → Groq → TTS → talking portrait → interruption`

Then we connect that service to Study Buddy `/ai-face`.

## Important

- Do not commit model weights or API keys.
- Colab GPU sessions are temporary.
- LivePortrait is the portrait-animation component; it is not itself a full speech/LLM conversation system.

Official project: https://github.com/KlingAIResearch/LivePortrait
