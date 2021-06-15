from io import BytesIO
from pathlib import Path

import librosa
import numpy as np
from pydub import AudioSegment
import sys
import os
from scipy.io import wavfile



from encoder import inference as encoder
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import StreamingResponse
from synthesizer.inference import Synthesizer
from vocoder import inference as vocoder

print("Preparing the encoder, the synthesizer and the vocoder...")
encoder.load_model(Path("encoder/saved_models/pretrained.pt"))
synthesizer = Synthesizer(Path("synthesizer/saved_models/logs-pretrained/taco_pretrained"), low_mem=False, seed=None)
vocoder.load_model(Path("vocoder/saved_models/pretrained/pretrained.pt"))


def load_embedding(file):
    original_wav, sampling_rate = librosa.load(file)
    preprocessed_wav = encoder.preprocess_wav(original_wav, sampling_rate)
    print("Loaded file succesfully")
    emb = encoder.embed_utterance(preprocessed_wav)
    return emb


embed = load_embedding('bot1.wav')

def louder_audio(file, output):
    song = AudioSegment.from_wav(file)

    song += 20

    song.export(output, format='wav')
    return output

sys.path.append('/path/to/ffmpeg')
app = FastAPI()


@app.post("/sample")
async def create_upload_file(file: UploadFile = File(...)):
    global embed
    embed = load_embedding(file.file)
    return 200


@app.post("/tts")
async def create_upload_file(text: str, k=1.1, step=0, louder=10, pitch=2):
    texts = [text]
    print("emebeddings: ", embed.shape)
    embeds = [embed]
    # If you know what the attention layer alignments are, you can retrieve them here by
    # passing return_alignments=True
    specs = synthesizer.synthesize_spectrograms(texts, embeds)
    print("specs size: ", np.array(specs).shape)
    spec = specs[0] * float(k) + float(step)
    print("Created the mel spectrogram")

    ## Generating the waveform
    print("Synthesizing the waveform:")

    # Synthesizing the waveform is fairly straightforward. Remember that the longer the
    # spectrogram, the more time-efficient the vocoder.
    generated_wav = vocoder.infer_waveform(spec)

    print("vocoder: ", np.array(generated_wav).shape)

    ## Post-generation
    # There's a bug with sounddevice that makes the audio cut one second earlier, so we
    # pad it.
    generated_wav = np.pad(generated_wav, (0, synthesizer.sample_rate), mode="constant")

    # Trim excess silences to compensate for gaps in spectrograms (issue #53)
    generated_wav = encoder.preprocess_wav(generated_wav)

    print("cut vocoder: ", np.array(generated_wav).shape)

    # Save it on the disk
    output = BytesIO()
    y_shifted = librosa.effects.pitch_shift(generated_wav.astype(np.float32), synthesizer.sample_rate, n_steps=pitch)
    wavfile.write("tmp.wav", synthesizer.sample_rate, y_shifted)
    song = AudioSegment.from_wav("tmp.wav")

    song += louder
    song.export(output, format='wav')
    os.remove("tmp.wav")

    #wavfile.write(output, synthesizer.sample_rate, generated_wav.astype(np.float32))
    return StreamingResponse(output, media_type='audio/x-wav')