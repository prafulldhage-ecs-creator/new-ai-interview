/**
 * InterviewIQ - Video Meeting & Audio-to-Audio Room Controller
 * Orchestrates real video call meeting interface, Web Speech audio dialogue loop,
 * hands-free silence detection, and dynamic question progression.
 */

document.addEventListener('DOMContentLoaded', () => {
  const roomConfig = window.INTERVIEW_CONFIG || {};
  if (!roomConfig.sessionId) return;

  const sessionId = roomConfig.sessionId;
  let currentQuestionId = roomConfig.questionId;
  let currentQuestionIndex = roomConfig.questionIndex;
  const totalQuestions = roomConfig.totalQuestions;

  // DOM Elements
  const precallOverlay = document.getElementById('precall-overlay');
  const btnJoinCall = document.getElementById('btn-join-call');
  const timerEl = document.getElementById('call-timer');
  const questionNumberTag = document.getElementById('ai-question-tag');
  const aiCaptionsOverlay = document.getElementById('ai-captions-overlay');
  const candidateCaptions = document.getElementById('candidate-captions');
  const btnDoneSpeaking = document.getElementById('btn-done-speaking');
  const btnMicToggle = document.getElementById('btn-mic-toggle');
  const btnCamToggle = document.getElementById('btn-cam-toggle');
  const btnSubtitlesToggle = document.getElementById('btn-subtitles-toggle');
  const btnToggleTextDrawer = document.getElementById('btn-toggle-text-drawer');
  const textDrawer = document.getElementById('text-fallback-drawer');
  const manualTextarea = document.getElementById('manual-answer-text');
  const btnManualSubmit = document.getElementById('btn-manual-submit');

  let callStarted = false;
  let questionStartTime = Date.now();
  let timerInterval = null;
  let isEvaluating = false;

  // 1. Initialize Voice Manager
  let voiceManager = null;
  if (window.VoiceManager) {
    voiceManager = new window.VoiceManager({
      targetTextarea: manualTextarea,
      statusPill: document.getElementById('candidate-status-pill'),
      captionsOverlay: candidateCaptions,
      silencePill: document.getElementById('silence-countdown-pill'),
      onAnswerReady: (spokenText) => {
        handleSpokenAnswerSubmission(spokenText);
      }
    });
  }

  // 2. Initialize Webcam Observer
  let webcamObserver = null;
  if (window.WebcamPresenceObserver) {
    webcamObserver = new window.WebcamPresenceObserver({
      videoEl: document.getElementById('candidate-video'),
      canvasEl: document.getElementById('candidate-canvas'),
      statusBanner: document.getElementById('presence-status'),
      toggleBtn: btnCamToggle,
      placeholderEl: document.getElementById('candidate-cam-placeholder'),
      onStreamReady: (stream) => {
        if (voiceManager) {
          voiceManager.attachAudioStream(stream);
        }
      }
    });
  }

  // 3. Joining the Video Call
  if (btnJoinCall) {
    btnJoinCall.addEventListener('click', async () => {
      callStarted = true;
      if (precallOverlay) {
        precallOverlay.style.display = 'none';
      }

      // Start webcam & microphone
      if (webcamObserver) {
        await webcamObserver.start();
      }

      // Start Call Timer
      questionStartTime = Date.now();
      startCallTimer();

      // Interviewer speaks opening introduction aloud!
      const openingQuestion = window.INTERVIEW_CONFIG.initialQuestionText ||
        "Hello and welcome to your placement interview! I will be conducting your interview today. To get started, please introduce yourself, share your academic background, and tell me about the projects or technologies you enjoy working on.";

      showAiSpeakingQuestion(openingQuestion);
    });
  }

  function startCallTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      if (!timerEl) return;
      const elapsedSeconds = Math.floor((Date.now() - questionStartTime) / 1000);
      const mins = String(Math.floor(elapsedSeconds / 60)).padStart(2, '0');
      const secs = String(elapsedSeconds % 60).padStart(2, '0');
      timerEl.textContent = `${mins}:${secs}`;
    }, 1000);
  }

  // 4. AI Speaks Question & Automatically Switches to Listening
  function showAiSpeakingQuestion(questionText) {
    if (aiCaptionsOverlay) {
      aiCaptionsOverlay.textContent = questionText;
      aiCaptionsOverlay.style.display = 'block';
    }

    if (voiceManager) {
      // Speak through TTS; on speech end, auto-activates microphone!
      voiceManager.speak(questionText, () => {
        // AI finished speaking -> Candidate's microphone opens!
        voiceManager.startListening();
        showToast("🎙️ Listening... Speak your answer.", "info");
      });
    }
  }

  // 5. Answer Submission Flow
  async function handleSpokenAnswerSubmission(answerText) {
    if (isEvaluating) return;
    const cleanedText = (answerText || '').trim();

    if (!cleanedText) {
      showToast("No spoken response detected. Please speak your answer into the microphone.", "warning");
      if (voiceManager) voiceManager.startListening();
      return;
    }

    isEvaluating = true;
    if (voiceManager) {
      voiceManager.stopListening();
      voiceManager.clearSilenceTimer();
    }

    // UI: Interviewer is Evaluating
    setAiEvaluatingUI(true);

    const durationSeconds = Math.max(1, Math.floor((Date.now() - questionStartTime) / 1000));
    const payload = {
      question_id: currentQuestionId,
      text: cleanedText,
      input_method: 'voice',
      duration_seconds: durationSeconds
    };

    try {
      const response = await fetch(`/api/interview/${sessionId}/submit-answer/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': CSRF_TOKEN
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Server error evaluating response.');
      }

      handleEvaluationResult(data);

    } catch (err) {
      console.error('Answer submission error:', err);
      showToast(err.message || 'Error processing response. Please retry.', 'danger');
      setAiEvaluatingUI(false);
      isEvaluating = false;
      if (voiceManager) voiceManager.startListening();
    }
  }

  function handleEvaluationResult(data) {
    isEvaluating = false;
    setAiEvaluatingUI(false);

    const evaluation = data.evaluation;
    const nextStep = data.next_step;

    // Build the interviewer's spoken response
    let spokenDialogue = evaluation.interviewer_response;

    if (nextStep.action === 'completed') {
      spokenDialogue += " That completes our placement interview for today. Excellent effort! Preparing your final assessment report now.";
      if (voiceManager) {
        voiceManager.speak(spokenDialogue, () => {
          setTimeout(() => {
            window.location.href = `/interview/${sessionId}/report/`;
          }, 1500);
        });
      } else {
        setTimeout(() => {
          window.location.href = `/interview/${sessionId}/report/`;
        }, 3000);
      }
      return;
    }

    // Prepare next question or follow-up
    currentQuestionId = nextStep.question_id;
    currentQuestionIndex = nextStep.question_index;
    questionStartTime = Date.now();

    if (nextStep.is_follow_up) {
      if (questionNumberTag) questionNumberTag.textContent = `Follow-up on Q${currentQuestionIndex}`;
      spokenDialogue += ` ${nextStep.question_text}`;
    } else {
      if (questionNumberTag) {
        if (nextStep.category === 'Candidate Introduction') {
          questionNumberTag.textContent = 'Candidate Introduction';
        } else {
          questionNumberTag.textContent = `Q${currentQuestionIndex} of ${totalQuestions}`;
        }
      }
      spokenDialogue += ` ${nextStep.question_text}`;
    }

    // Reset Candidate Captions & Textbox
    if (candidateCaptions) candidateCaptions.textContent = '';
    if (manualTextarea) manualTextarea.value = '';

    // AI Speaks response + next question, then automatically listens for answer!
    showAiSpeakingQuestion(spokenDialogue);
  }

  function setAiEvaluatingUI(evaluating) {
    const aiStatus = document.getElementById('ai-status-pill');
    const btnDone = document.getElementById('btn-done-speaking');

    if (evaluating) {
      if (aiStatus) aiStatus.innerHTML = '<span class="status-dot" style="background:#f59e0b;"></span> Interviewer Thinking...';
      if (btnDone) {
        btnDone.disabled = true;
        btnDone.innerHTML = '<span>⏳</span><span>Evaluating Answer...</span>';
      }
    } else {
      if (btnDone) {
        btnDone.disabled = false;
        btnDone.innerHTML = '<span>🗣️</span><span>Done Speaking</span>';
      }
    }
  }

  // 6. Dock Buttons Event Listeners
  if (btnDoneSpeaking) {
    btnDoneSpeaking.addEventListener('click', () => {
      const text = (voiceManager ? voiceManager.fullTranscript : '') || (manualTextarea ? manualTextarea.value : '');
      handleSpokenAnswerSubmission(text);
    });
  }

  if (btnMicToggle) {
    btnMicToggle.addEventListener('click', () => {
      if (voiceManager) {
        if (voiceManager.isRecording) {
          voiceManager.stopListening();
          showToast('Microphone muted', 'info');
        } else {
          voiceManager.startListening();
          showToast('Microphone unmuted', 'info');
        }
      }
    });
  }

  if (btnCamToggle) {
    btnCamToggle.addEventListener('click', () => {
      if (webcamObserver) {
        webcamObserver.toggle();
      }
    });
  }

  if (btnSubtitlesToggle) {
    let subsVisible = true;
    btnSubtitlesToggle.addEventListener('click', () => {
      subsVisible = !subsVisible;
      if (aiCaptionsOverlay) aiCaptionsOverlay.style.visibility = subsVisible ? 'visible' : 'hidden';
      if (candidateCaptions) candidateCaptions.style.visibility = subsVisible ? 'visible' : 'hidden';
      btnSubtitlesToggle.classList.toggle('active-recording', !subsVisible);
      showToast(subsVisible ? 'Captions Enabled' : 'Captions Hidden', 'info');
    });
  }

  if (btnToggleTextDrawer && textDrawer) {
    btnToggleTextDrawer.addEventListener('click', () => {
      const isHidden = textDrawer.style.display === 'none';
      textDrawer.style.display = isHidden ? 'block' : 'none';
    });
  }

  if (btnManualSubmit) {
    btnManualSubmit.addEventListener('click', () => {
      const manualText = (manualTextarea.value || '').trim();
      if (!manualText) {
        showToast('Please enter text before submitting.', 'warning');
        return;
      }
      handleSpokenAnswerSubmission(manualText);
    });
  }

  // Keyboard shortcut: Spacebar to toggle done speaking
  document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && e.target.tagName !== 'TEXTAREA' && e.target.tagName !== 'INPUT') {
      e.preventDefault();
      const text = (voiceManager ? voiceManager.fullTranscript : '') || (manualTextarea ? manualTextarea.value : '');
      if (text) {
        handleSpokenAnswerSubmission(text);
      }
    }
  });
});
