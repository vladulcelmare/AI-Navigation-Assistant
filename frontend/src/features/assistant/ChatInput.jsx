import {useEffect, useRef, useState} from "react";

export function ChatInput({ onSend, disabled = false, onAudioRecorded }){
    const [message, setMessage] = useState("");
    const [isSending, setIsSending] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const inputRef = useRef();
    const streamRef = useRef(null);
    const recordingTimeoutRef = useRef(null);
    const audioContextRef = useRef(null);
    const sourceNodeRef = useRef(null);
    const processorNodeRef = useRef(null);
    const silentGainNodeRef = useRef(null);
    const pcmChunksRef = useRef([]);
    const sampleRateRef = useRef(44100);
    const isStoppingRef = useRef(false);
    const hasAudioHandler = typeof onAudioRecorded === "function";

    async function blobToBase64(blob) {
        const buffer = await blob.arrayBuffer();
        const bytes = new Uint8Array(buffer);
        const chunkSize = 0x8000;
        let binary = "";

        for (let i = 0; i < bytes.length; i += chunkSize) {
            binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
        }

        return btoa(binary);
    }

    function mergeAudioChunks(chunks) {
        const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
        const merged = new Float32Array(totalLength);
        let offset = 0;

        chunks.forEach((chunk) => {
            merged.set(chunk, offset);
            offset += chunk.length;
        });

        return merged;
    }

    function audioSamplesToWavBlob(samples, sampleRate) {
        const bitsPerSample = 16;
        const bytesPerSample = bitsPerSample / 8;
        const numberOfChannels = 1;
        const frameCount = samples.length;
        const blockAlign = numberOfChannels * bytesPerSample;
        const byteRate = sampleRate * blockAlign;
        const dataSize = frameCount * blockAlign;
        const buffer = new ArrayBuffer(44 + dataSize);
        const view = new DataView(buffer);
        let offset = 0;

        function writeString(value) {
            for (let i = 0; i < value.length; i += 1) {
                view.setUint8(offset, value.charCodeAt(i));
                offset += 1;
            }
        }

        writeString("RIFF");
        view.setUint32(offset, 36 + dataSize, true);
        offset += 4;
        writeString("WAVE");
        writeString("fmt ");
        view.setUint32(offset, 16, true);
        offset += 4;
        view.setUint16(offset, 1, true);
        offset += 2;
        view.setUint16(offset, numberOfChannels, true);
        offset += 2;
        view.setUint32(offset, sampleRate, true);
        offset += 4;
        view.setUint32(offset, byteRate, true);
        offset += 4;
        view.setUint16(offset, blockAlign, true);
        offset += 2;
        view.setUint16(offset, bitsPerSample, true);
        offset += 2;
        writeString("data");
        view.setUint32(offset, dataSize, true);
        offset += 4;

        for (let frame = 0; frame < frameCount; frame += 1) {
            const sample = Math.max(-1, Math.min(1, samples[frame]));
            const pcmSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
            view.setInt16(offset, pcmSample, true);
            offset += bytesPerSample;
        }

        return new Blob([buffer], { type: "audio/wav" });
    }

    async function cleanupRecordingResources() {
        if (recordingTimeoutRef.current) {
            clearTimeout(recordingTimeoutRef.current);
            recordingTimeoutRef.current = null;
        }

        if (processorNodeRef.current) {
            processorNodeRef.current.onaudioprocess = null;
            processorNodeRef.current.disconnect();
            processorNodeRef.current = null;
        }

        if (sourceNodeRef.current) {
            sourceNodeRef.current.disconnect();
            sourceNodeRef.current = null;
        }

        if (silentGainNodeRef.current) {
            silentGainNodeRef.current.disconnect();
            silentGainNodeRef.current = null;
        }

        if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
        }

        if (audioContextRef.current) {
            const currentAudioContext = audioContextRef.current;
            audioContextRef.current = null;

            if (currentAudioContext.state !== "closed") {
                await currentAudioContext.close();
            }
        }
    }

    async function finalizeRecording() {
        const recordedChunks = pcmChunksRef.current;
        pcmChunksRef.current = [];
        setIsRecording(false);

        const audioSamples = mergeAudioChunks(recordedChunks);

        if (audioSamples.length === 0) {
            return;
        }

        const wavBlob = audioSamplesToWavBlob(audioSamples, sampleRateRef.current);
        const base64Audio = await blobToBase64(wavBlob);
        console.log("Recorded audio WAV base64:", base64Audio);

        if (onAudioRecorded) {
            try {
                const result = await onAudioRecorded(base64Audio);

                if (typeof result === "string") {
                    setMessage(result);
                }
            } catch (error) {
                console.error("Audio transcription callback failed:", error);
            }
        }
    }

    async function stopRecording() {
        if (isStoppingRef.current) {
            return;
        }

        isStoppingRef.current = true;

        try {
            await cleanupRecordingResources();
            await finalizeRecording();
        } catch (error) {
            console.error("Failed to finalize WAV base64 audio:", error);
            pcmChunksRef.current = [];
            setIsRecording(false);
        } finally {
            isStoppingRef.current = false;
        }
    }

    async function sendMessage() {
        const trimmedMessage = message.trim();

        if (!trimmedMessage || disabled || isSending || !onSend) {
            return;
        }

        setIsSending(true);

        try {
            setMessage("");
            await onSend(trimmedMessage);
        } catch (error) {
            console.error(error);
        } finally {
            setIsSending(false);

            setTimeout(() => {
                if (inputRef.current && !disabled) {
                    inputRef.current.focus();
                }
            }, 0);
        }
    }

    async function toggleAudioRecording() {
        if (disabled || isSending || !hasAudioHandler) {
            return;
        }

        if (isRecording) {
            await stopRecording();
            return;
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            console.error("Audio recording is not supported in this browser.");
            return;
        }

        const AudioContextClass = window.AudioContext || window.webkitAudioContext;

        if (!AudioContextClass) {
            console.error("Audio capture is not supported in this browser.");
            return;
        }

        try {
            streamRef.current = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });
            pcmChunksRef.current = [];
            audioContextRef.current = new AudioContextClass();

            if (audioContextRef.current.state === "suspended") {
                await audioContextRef.current.resume();
            }

            sampleRateRef.current = audioContextRef.current.sampleRate;
            sourceNodeRef.current = audioContextRef.current.createMediaStreamSource(streamRef.current);
            processorNodeRef.current = audioContextRef.current.createScriptProcessor(4096, 1, 1);
            silentGainNodeRef.current = audioContextRef.current.createGain();
            silentGainNodeRef.current.gain.value = 0;

            processorNodeRef.current.onaudioprocess = (event) => {
                const channelData = event.inputBuffer.getChannelData(0);
                pcmChunksRef.current.push(new Float32Array(channelData));
            };

            sourceNodeRef.current.connect(processorNodeRef.current);
            processorNodeRef.current.connect(silentGainNodeRef.current);
            silentGainNodeRef.current.connect(audioContextRef.current.destination);

            setIsRecording(true);
            recordingTimeoutRef.current = setTimeout(() => {
                stopRecording().catch((error) => {
                    console.error("Failed to auto-stop recording:", error);
                });
            }, 4000);
        } catch (error) {
            console.error("Failed to start audio recording:", error);
            pcmChunksRef.current = [];
            setIsRecording(false);
            await cleanupRecordingResources();
        }
    }

    useEffect(() => {
        return () => {
            cleanupRecordingResources().catch((error) => {
                console.error("Failed to clean up audio resources:", error);
            });
        };
    }, []);

    return(
      <div className="w-full rounded-lg shadow-sm bg-black text-white flex flex-row justify-evenly align-baseline p-3"
           onKeyDown={(event)=>{
          if(event.key === "Enter"){
              sendMessage();
          }
      }}>
          <input
              ref={inputRef}
              type="text"
              value={message}
              onChange={(e)=>{setMessage(e.target.value)}}
              placeholder="Ask the assistant..."
              aria-label="Message the assistant"
              className="w-[80%] h-full"
              disabled={disabled || isSending || isRecording}
          />
          {hasAudioHandler && (
              <button
                  type="button"
                  className={"material-symbols-outlined cursor-pointer disabled:opacity-50"}
                  onClick={toggleAudioRecording}
                  disabled={disabled || isSending}
                  title={isRecording ? "Stop recording" : "Start recording"}
              >
                  {isRecording ? "stop_circle" : "mic"}
              </button>
          )}
          <button
              type="button"
              className={"material-symbols-outlined cursor-pointer disabled:opacity-50"}
              onClick={sendMessage}
              disabled={disabled || isSending || isRecording}
          >
              send
          </button>
      </div>
    );
}