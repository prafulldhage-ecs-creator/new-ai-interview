/**
 * Voice Module - InterviewIQ
 * Implements real Audio-to-Audio conversational loop using Web Speech API + Web Audio API.
 * Features:
 * - Natural Text-to-Speech playback for AI interviewer
 * - Real-time Speech-to-Text transcription
 * - Dynamic Microphone Level Meter (Web Audio API)
 * - Hands-free auto-silence detection
 * - Echo cancellation & clean pause management
 */

class VoiceManager {
  constructor(options = {}) {
    this.targetTextarea = options.targetTextarea || document.getElementById('answer-text');
    this.statusPill = options.statusPill || document.getElementById('candidate-status-pill');
    this.captionsOverlay = options.captionsOverlay || document.getElementById('candidate-captions');
    this.silencePill = options.silencePill || document.getElementById('silence-countdown-pill');
    this.micMeterBars = options.micMeterBars || document.querySelectorAll('.candidate-meter-bar');

    this.onAnswerReady = options.onAnswerReady || null; // Callback when candidate finishes speaking
    this.onAiSpeakingStateChange = options.onAiSpeakingStateChange || null;

    this.isRecording = false;
    this.recognition = null;
    this.interimTranscript = '';
    this.fullTranscript = '';
    this.language = options.language || 'en-US';

    // Hands-free silence timer
    this.silenceTimer = null;
    this.silenceTimeoutMs = 3500; // 3.5 seconds of silence triggers completion
    this.countdownInterval = null;
    this.autoHandsFree = true;

    // Web Audio API for Live Microphone Level
    this.audioContext = null;
    this.analyser = null;
    this.microphoneSource = null;
    this.meterInterval = null;

    this.initRecognition();
  }

  initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('SpeechRecognition API not available in this browser.');
      return;
    }

    try {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = this.language;

      this.recognition.onstart = () => {
        this.isRecording = true;
        this.updateUI(true);
        if (this.statusPill) this.statusPill.innerHTML = '<span class="status-dot" style="background:#10b981;"></span> Listening...';
      };

      this.recognition.onresult = (event) => {
        let interimChunk = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            const finalPiece = event.results[i][0].transcript.trim();
            if (finalPiece) {
              this.fullTranscript = this.fullTranscript ? this.fullTranscript + ' ' + finalPiece : finalPiece;
            }
          } else {
            interimChunk += event.results[i][0].transcript;
          }
        }

        const displayText = (this.fullTranscript + ' ' + interimChunk).trim();

        // Update captions & textarea
        if (this.captionsOverlay) {
          this.captionsOverlay.style.display = displayText ? 'block' : 'none';
          this.captionsOverlay.textContent = `"${displayText}"`;
        }
        if (this.targetTextarea) {
          this.targetTextarea.value = displayText;
        }

        // Reset and trigger silence detection if student spoke at least 3 words
        const words = displayText.split(/\s+/).length;
        if (words >= 3 && this.autoHandsFree) {
          this.resetSilenceTimer();
        }
      };

      this.recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        if (event.error === 'not-allowed') {
          showToast('Microphone access was denied in browser permissions.', 'warning');
        }
        this.clearSilenceTimer();
      };

      this.recognition.onend = () => {
        // If still supposed to be recording, restart (keeps mic open continuous)
        if (this.isRecording) {
          try {
            this.recognition.start();
          } catch (e) {
            this.isRecording = false;
            this.updateUI(false);
          }
        } else {
          this.updateUI(false);
        }
      };
    } catch (e) {
      console.error('Failed to initialize speech recognition:', e);
    }
  }

  // Connect candidate audio stream to Web Audio API analyser
  attachAudioStream(stream) {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx || !stream) return;

      this.audioContext = new AudioCtx();
      this.microphoneSource = this.audioContext.createMediaStreamSource(stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 32;
      this.microphoneSource.connect(this.analyser);

      const bufferLength = this.analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      if (this.meterInterval) clearInterval(this.meterInterval);
      this.meterInterval = setInterval(() => {
        if (!this.analyser || !this.isRecording) {
          this.resetMeterBars();
          return;
        }

        this.analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += dataArray[i];
        }
        const avg = sum / bufferLength;

        // Animate 5 meter bars based on volume
        const bars = document.querySelectorAll('.candidate-meter-bar');
        bars.forEach((bar, idx) => {
          const threshold = (idx + 1) * 12;
          if (avg > threshold) {
            bar.classList.add('active');
            bar.style.height = `${Math.min(14, 4 + (avg - threshold) * 0.5)}px`;
          } else {
            bar.classList.remove('active');
            bar.style.height = '4px';
          }
        });
      }, 100);
    } catch (e) {
      console.warn('Could not attach Web Audio analyser:', e);
    }
  }

  resetMeterBars() {
    const bars = document.querySelectorAll('.candidate-meter-bar');
    bars.forEach(bar => {
      bar.classList.remove('active');
      bar.style.height = '4px';
    });
  }

  startListening() {
    this.stopSpeaking();
    this.fullTranscript = '';
    this.interimTranscript = '';

    if (this.captionsOverlay) {
      this.captionsOverlay.textContent = 'Listening... Speak your answer';
      this.captionsOverlay.style.display = 'block';
    }

    if (this.recognition) {
      try {
        this.isRecording = true;
        this.recognition.start();
      } catch (e) {
        // Recognition already active
      }
    }
  }

  stopListening() {
    this.isRecording = false;
    this.clearSilenceTimer();
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {}
    }
    this.updateUI(false);
  }

  resetSilenceTimer() {
    this.clearSilenceTimer();

    let countdown = 3;
    if (this.silencePill) {
      this.silencePill.style.display = 'inline-flex';
      this.silencePill.textContent = `Auto-submitting in ${countdown}s...`;
    }

    this.countdownInterval = setInterval(() => {
      countdown--;
      if (this.silencePill) {
        if (countdown > 0) {
          this.silencePill.textContent = `Auto-submitting in ${countdown}s...`;
        } else {
          this.silencePill.style.display = 'none';
        }
      }
    }, 1000);

    this.silenceTimer = setTimeout(() => {
      this.clearSilenceTimer();
      // Auto-trigger completion of current answer
      if (typeof this.onAnswerReady === 'function') {
        const text = (this.fullTranscript || (this.targetTextarea ? this.targetTextarea.value : '')).trim();
        if (text) {
          this.onAnswerReady(text);
        }
      }
    }, this.silenceTimeoutMs);
  }

  clearSilenceTimer() {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }
    if (this.silencePill) {
      this.silencePill.style.display = 'none';
    }
  }

  updateUI(recording) {
    const micBtn = document.getElementById('btn-mic-toggle');
    if (micBtn) {
      if (recording) {
        micBtn.classList.add('active-recording');
        micBtn.innerHTML = '<span>🎙️</span><span>Mic Active</span>';
      } else {
        micBtn.classList.remove('active-recording');
        micBtn.innerHTML = '<span>🎙️</span><span>Mic Muted</span>';
      }
    }
  }

  // Text-To-Speech with AI Waveform Animation & Auto-Listen Trigger
  speak(text, onComplete) {
    if (!('speechSynthesis' in window)) {
      if (typeof onComplete === 'function') onComplete();
      return;
    }

    this.stopSpeaking();
    this.stopListening(); // Echo cancellation: pause mic while AI speaks

    if (!text || text.trim() === '') {
      if (typeof onComplete === 'function') onComplete();
      return;
    }

    // Clean text (remove brackets or markdown)
    const cleanText = text.replace(/\[.*?\]/g, '').replace(/[\*_`#]/g, '').trim();
    if (!cleanText) {
      if (typeof onComplete === 'function') onComplete();
      return;
    }

    // Split text into natural sentence chunks so Chrome/Edge NEVER cuts off speech!
    const sentenceRegex = /[^.?!;]+[.?!;]+(\s+|$)|[^.?!;]+$/g;
    const rawChunks = cleanText.match(sentenceRegex) || [cleanText];
    const chunks = rawChunks.map(c => c.trim()).filter(c => c.length > 0);

    if (chunks.length === 0) {
      if (typeof onComplete === 'function') onComplete();
      return;
    }

    this.setAiSpeakingUI(true, cleanText);

    let currentChunkIndex = 0;

    // Chrome keep-alive timer preventing internal SpeechSynthesis pause
    if (this.ttsKeepAlive) clearInterval(this.ttsKeepAlive);
    this.ttsKeepAlive = setInterval(() => {
      if (window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.pause();
        window.speechSynthesis.resume();
      } else {
        clearInterval(this.ttsKeepAlive);
      }
    }, 5000);

    const speakNextChunk = () => {
      if (currentChunkIndex >= chunks.length) {
        if (this.ttsKeepAlive) clearInterval(this.ttsKeepAlive);
        this.setAiSpeakingUI(false, '');
        if (typeof onComplete === 'function') {
          onComplete();
        } else {
          this.startListening();
        }
        return;
      }

      const chunkText = chunks[currentChunkIndex];
      currentChunkIndex++;

      const utterance = new SpeechSynthesisUtterance(chunkText);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.lang = this.language;

      const voices = window.speechSynthesis.getVoices();
      const naturalVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Microsoft') || v.name.includes('David') || v.name.includes('Zira') || v.name.includes('Samantha')));
      if (naturalVoice) utterance.voice = naturalVoice;

      utterance.onend = () => {
        speakNextChunk();
      };

      utterance.onerror = (e) => {
        console.warn('Speech chunk error:', e);
        speakNextChunk();
      };

      window.speechSynthesis.speak(utterance);
    };

    speakNextChunk();
  }

  setAiSpeakingUI(isSpeaking, spokenText) {
    const avatar = document.getElementById('ai-avatar');
    const waveBars = document.querySelectorAll('.ai-wave-bar');
    const aiStatus = document.getElementById('ai-status-pill');
    const aiCaptions = document.getElementById('ai-captions-overlay');

    if (avatar) {
      if (isSpeaking) avatar.classList.add('speaking');
      else avatar.classList.remove('speaking');
    }

    waveBars.forEach(b => {
      if (isSpeaking) b.classList.add('active');
      else b.classList.remove('active');
    });

    if (aiStatus) {
      aiStatus.innerHTML = isSpeaking
        ? '<span class="status-dot" style="background:#38bdf8;"></span> AI Speaking...'
        : '<span class="status-dot" style="background:#10b981;"></span> Listening to you...';
    }

    if (aiCaptions) {
      aiCaptions.textContent = spokenText;
      aiCaptions.style.display = isSpeaking ? 'block' : 'none';
    }

    if (typeof this.onAiSpeakingStateChange === 'function') {
      this.onAiSpeakingStateChange(isSpeaking);
    }
  }

  stopSpeaking() {
    if (this.ttsKeepAlive) {
      clearInterval(this.ttsKeepAlive);
      this.ttsKeepAlive = null;
    }
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    this.setAiSpeakingUI(false, '');
  }

  destroy() {
    this.stopSpeaking();
    this.stopListening();
    if (this.meterInterval) clearInterval(this.meterInterval);
    if (this.audioContext) this.audioContext.close();
  }
}

window.VoiceManager = VoiceManager;
