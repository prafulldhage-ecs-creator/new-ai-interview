/**
 * Webcam & Video Feed Observer - InterviewIQ
 * Displays live webcam feed in meeting tile, handles browser permissions gracefully,
 * and provides stream to VoiceManager for real-time visualizer.
 */

class WebcamPresenceObserver {
  constructor(options = {}) {
    this.videoEl = options.videoEl || document.getElementById('candidate-video');
    this.canvasEl = options.canvasEl || document.getElementById('candidate-canvas');
    this.statusBanner = options.statusBanner || document.getElementById('presence-status');
    this.toggleBtn = options.toggleBtn || document.getElementById('btn-cam-toggle');
    this.placeholderEl = options.placeholderEl || document.getElementById('candidate-cam-placeholder');
    this.onStreamReady = options.onStreamReady || null;

    this.stream = null;
    this.isActive = false;
    this.analysisInterval = null;
    this.faceDetector = null;

    this.lastAlertTime = 0;
    this.alertCooldownMs = 12000;
    this.missingFaceCounter = 0;

    this.initDetector();
  }

  async initDetector() {
    if ('FaceDetector' in window) {
      try {
        // @ts-ignore
        this.faceDetector = new window.FaceDetector({ fastMode: true, maxDetectedFaces: 5 });
      } catch (e) {
        this.faceDetector = null;
      }
    }
  }

  async start() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.setStatus('Camera API not supported in browser.', 'warning');
      this.showPermissionHelp('Your browser does not support webcam access or requires HTTPS / localhost.');
      return;
    }

    // Try video-only first to prevent audio device lockouts
    let mediaStream = null;
    try {
      // Preferred standard constraints
      mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } }
      });
    } catch (e1) {
      console.warn('Standard video constraint failed, trying basic video:true...', e1);
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
      } catch (e2) {
        console.warn('Basic video:true also failed:', e2);
        this.showPermissionHelp(e2.name === 'NotAllowedError' 
          ? 'Camera permission was blocked. Please click the camera/lock icon in your browser address bar to allow camera access.'
          : 'Could not access webcam. Ensure another application (like Zoom or Teams) is not using your camera.'
        );
        return;
      }
    }

    if (!mediaStream) return;
    this.stream = mediaStream;

    // Also request separate audio stream for visualizer if possible
    try {
      const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (typeof this.onStreamReady === 'function') {
        this.onStreamReady(audioStream);
      }
    } catch (audioErr) {
      console.log('Audio visualizer stream optional note:', audioErr);
    }

    if (this.videoEl) {
      this.videoEl.srcObject = this.stream;
      this.videoEl.muted = true;
      this.videoEl.playsInline = true;
      this.videoEl.style.display = 'block';

      // Robust play handler
      const playPromise = this.videoEl.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          this.videoEl.onloadedmetadata = () => {
            this.videoEl.play().catch(e => console.warn('Metadata play error:', e));
          };
        });
      }
    }

    if (this.placeholderEl) this.placeholderEl.style.display = 'none';
    this.isActive = true;
    this.setStatus('Camera Active', 'success');

    if (this.toggleBtn) {
      this.toggleBtn.innerHTML = '<span>📹</span><span>Cam Active</span>';
      this.toggleBtn.classList.remove('btn-secondary');
    }

    this.startPresenceLoop();
  }

  showPermissionHelp(msg) {
    this.setStatus('Camera Blocked / Unavailable', 'warning');
    if (this.placeholderEl) {
      this.placeholderEl.style.display = 'flex';
      this.placeholderEl.innerHTML = `
        <div style="font-size:2.2rem;margin-bottom:0.4rem;">📷</div>
        <p style="font-size:0.85rem;color:#fca5a5;max-width:320px;line-height:1.4;margin-bottom:0.75rem;">
          ${msg}
        </p>
        <button type="button" class="btn btn-primary btn-sm" id="btn-retry-camera" style="font-size:0.8rem;padding:0.4rem 0.85rem;">
          🔄 Retry Camera Access
        </button>
      `;
      const retryBtn = document.getElementById('btn-retry-camera');
      if (retryBtn) {
        retryBtn.addEventListener('click', () => this.start());
      }
    }
  }

  stop() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    if (this.analysisInterval) {
      clearInterval(this.analysisInterval);
      this.analysisInterval = null;
    }
    this.isActive = false;

    if (this.videoEl) {
      this.videoEl.style.display = 'none';
    }
    if (this.placeholderEl) {
      this.placeholderEl.style.display = 'flex';
      this.placeholderEl.innerHTML = `
        <div style="font-size:2.5rem;margin-bottom:0.5rem;">📷</div>
        <p style="font-size:0.9rem;">Camera Turned Off</p>
        <button type="button" class="btn btn-secondary btn-sm" id="btn-turn-on-cam" style="margin-top:0.5rem;">Turn On Camera</button>
      `;
      const onBtn = document.getElementById('btn-turn-on-cam');
      if (onBtn) onBtn.addEventListener('click', () => this.start());
    }

    this.setStatus('Camera Off', 'default');

    if (this.toggleBtn) {
      this.toggleBtn.innerHTML = '<span>📷</span><span>Cam Off</span>';
    }
  }

  toggle() {
    if (this.isActive) {
      this.stop();
    } else {
      this.start();
    }
  }

  setStatus(text, type = 'default') {
    if (!this.statusBanner) return;
    this.statusBanner.textContent = text;
    this.statusBanner.className = 'tile-status-tag';
    if (type === 'warning') this.statusBanner.style.background = 'rgba(245, 158, 11, 0.85)';
    else if (type === 'success') this.statusBanner.style.background = 'rgba(16, 185, 129, 0.85)';
    else this.statusBanner.style.background = 'rgba(15, 23, 42, 0.85)';
  }

  startPresenceLoop() {
    if (this.analysisInterval) clearInterval(this.analysisInterval);

    this.analysisInterval = setInterval(async () => {
      if (!this.isActive || !this.videoEl || this.videoEl.readyState < 2) return;

      const now = Date.now();

      if (this.faceDetector) {
        try {
          const faces = await this.faceDetector.detect(this.videoEl);
          if (faces.length === 0) {
            this.missingFaceCounter++;
            if (this.missingFaceCounter >= 2 && now - this.lastAlertTime > this.alertCooldownMs) {
              this.setStatus('Face outside frame', 'warning');
              this.lastAlertTime = now;
            }
          } else {
            this.missingFaceCounter = 0;
            this.setStatus('Face In Frame • Good Framing', 'success');
          }
        } catch (e) {
          this.setStatus('Camera Active', 'success');
        }
      } else {
        this.setStatus('Camera Active', 'success');
      }
    }, 3000);
  }

  destroy() {
    this.stop();
  }
}

window.WebcamPresenceObserver = WebcamPresenceObserver;
