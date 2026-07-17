/* PRODUCTION VERSION 1 — 2026-05-16 — chapter_player.js */
/* Rollback: replace with chapter_player.js.v1.bak */
/* chapter_player.js — loaded by exported chapter HTML files */
(function () {
  const data = window.CHAPTER_DATA;
  if (!data) { document.body.innerHTML = '<p style="color:red;padding:2rem">Error: no chapter data found.</p>'; return; }

  const fmt = s => { if (!isFinite(s)) return '0:00'; const m = Math.floor(s / 60), ss = Math.floor(s % 60).toString().padStart(2, '0'); return `${m}:${ss}`; };
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  document.title = `${data.book} — ${data.chapter}`;

  // Ensure viewport-fit=cover so safe-area-inset env vars are populated on iOS/Android
  let vp = document.querySelector('meta[name=viewport]');
  if(vp && !vp.content.includes('viewport-fit')) {
    vp.content += ', viewport-fit=cover';
  }

  document.body.innerHTML = `
    <div class="player-wrap">
      <header class="cp-header">
        <a href="../index.html" class="back-link">← Library</a>
        <div class="cp-meta">
          <span class="cp-book">${esc(data.book)}</span>
          <span class="cp-chapter">${esc(data.chapter)}</span>
        </div>
      </header>

      <div id="audio-status" style="display:none;font-size:13px;padding:10px 20px;line-height:1.6;"></div>

      <div class="transcript-wrap">
        <div id="transcript-box" role="region" aria-label="Scripture text" aria-live="polite"></div>
      </div>

      <footer class="cp-controls">
        <div class="ctrl-top">
          <span id="time-display">Loading…</span>
          <input type="range" id="seek-bar" min="0" max="100" value="0" step="0.1" aria-label="Seek">
        </div>
        <div class="ctrl-bottom">
          <button id="restart-btn" aria-label="Restart">⏮</button>
          <button id="skip-back-btn" aria-label="Skip back 10s">−10s</button>
          <button id="play-btn" class="play-main" aria-label="Play">▶</button>
          <button id="skip-fwd-btn" aria-label="Skip forward 10s">+10s</button>
          <div class="vol-wrap">
            <span>🔉</span>
            <input type="range" id="vol-bar" min="0" max="1" value="1" step="0.01" aria-label="Volume">
          </div>
        </div>
      </footer>
    </div>
  `;

  // Use an <audio> element with crossOrigin set — required for Archive.org streaming
  const audio = document.createElement('audio');
  audio.crossOrigin = 'anonymous';
  audio.preload = 'metadata';
  audio.src = data.audioSrc;

  const lyrics = data.lyrics;
  let currentIdx = -1, isSeeking = false;

  const transcriptBox = document.getElementById('transcript-box');
  const seekBar = document.getElementById('seek-bar');
  const timeDisplay = document.getElementById('time-display');
  const volBar = document.getElementById('vol-bar');
  const playBtn = document.getElementById('play-btn');
  const audioStatus = document.getElementById('audio-status');

  function showStatus(msg, isError) {
    audioStatus.style.display = 'block';
    audioStatus.style.color = isError ? '#b03a3a' : '#8a6a34';
    audioStatus.textContent = msg;
  }
  function hideStatus() { audioStatus.style.display = 'none'; }

  // Render lines
  lyrics.forEach((l, i) => {
    const div = document.createElement('div');
    div.className = 'lyric-line';
    div.dataset.idx = i;
    div.innerHTML = `<span class="ts">${fmt(l.time)}</span><span class="body">${esc(l.text)}</span>`;
    div.addEventListener('click', () => { audio.currentTime = l.time; audio.play().catch(e => showStatus('Could not play: ' + e.message, true)); });
    transcriptBox.appendChild(div);
  });

  function updatePlayBtn() { playBtn.textContent = audio.paused ? '▶' : '⏸'; }

  function updateActive() {
    const ct = audio.currentTime;
    let idx = -1;
    for (let i = 0; i < lyrics.length; i++) { if (ct >= lyrics[i].time) idx = i; else break; }
    if (idx === currentIdx) return;
    currentIdx = idx;
    document.querySelectorAll('.lyric-line').forEach(el => el.classList.remove('active'));
    if (idx >= 0) {
      const el = document.querySelector(`.lyric-line[data-idx="${idx}"]`);
      if (el) {
        el.classList.add('active');
        transcriptBox.scrollTo({ top: el.offsetTop - transcriptBox.offsetTop - transcriptBox.clientHeight / 3, behavior: 'smooth' });
      }
    }
  }

  audio.addEventListener('loadedmetadata', () => {
    timeDisplay.textContent = `0:00 / ${fmt(audio.duration)}`;
    hideStatus();
  });
  audio.addEventListener('timeupdate', () => {
    if (!isSeeking) {
      seekBar.value = audio.duration ? audio.currentTime / audio.duration * 100 : 0;
      timeDisplay.textContent = `${fmt(audio.currentTime)} / ${fmt(audio.duration || 0)}`;
    }
    updateActive();
  });
  audio.addEventListener('ended', () => {
    updatePlayBtn(); currentIdx = -1;
    document.querySelectorAll('.lyric-line').forEach(el => el.classList.remove('active'));
  });
  audio.addEventListener('play', updatePlayBtn);
  audio.addEventListener('pause', updatePlayBtn);
  audio.addEventListener('waiting', () => showStatus('Buffering…', false));
  audio.addEventListener('playing', hideStatus);
  audio.addEventListener('error', () => {
    const codes = { 1:'Aborted', 2:'Network error', 3:'Decode error', 4:'Source not supported' };
    const code = audio.error ? audio.error.code : 0;
    showStatus(
      `Audio failed to load (${codes[code] || 'Unknown error'}). ` +
      `Check that the Archive.org URL is correct and the file is publicly accessible.\n` +
      `URL: ${data.audioSrc}`,
      true
    );
    timeDisplay.textContent = '0:00 / 0:00';
  });

  playBtn.addEventListener('click', () => {
    if (audio.paused) {
      audio.play().catch(e => {
        showStatus(`Playback blocked: ${e.message}. Try tapping again or check the audio URL.`, true);
      });
    } else {
      audio.pause();
    }
  });

  document.getElementById('restart-btn').addEventListener('click', () => { audio.currentTime = 0; });
  document.getElementById('skip-back-btn').addEventListener('click', () => { audio.currentTime = Math.max(0, audio.currentTime - 10); });
  document.getElementById('skip-fwd-btn').addEventListener('click', () => { audio.currentTime = Math.min(audio.duration || 0, audio.currentTime + 10); });
  seekBar.addEventListener('mousedown', () => isSeeking = true);
  seekBar.addEventListener('touchstart', () => isSeeking = true, { passive: true });
  seekBar.addEventListener('input', () => {
    if (audio.duration) {
      audio.currentTime = seekBar.value / 100 * audio.duration;
      timeDisplay.textContent = `${fmt(audio.currentTime)} / ${fmt(audio.duration)}`;
    }
  });
  seekBar.addEventListener('mouseup', () => isSeeking = false);
  seekBar.addEventListener('touchend', () => isSeeking = false);
  volBar.addEventListener('input', () => audio.volume = volBar.value);
})();
