// Hold-to-talk with the browser's Web Speech API (en-SG or zh-CN). Free, no key.
// Needs Chrome, and HTTPS or localhost. Where it is missing the app falls back to typing.
import { useCallback, useEffect, useRef, useState } from 'react';
import { speechLang, type Lang } from '../shared/i18n';

interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
}

type Ctor = new () => SpeechRecognitionLike;
const Recognition: Ctor | undefined =
  (window as unknown as { SpeechRecognition?: Ctor; webkitSpeechRecognition?: Ctor }).SpeechRecognition ??
  (window as unknown as { webkitSpeechRecognition?: Ctor }).webkitSpeechRecognition;

export const speechSupported = !!Recognition;

export type TalkState = 'idle' | 'listening' | 'done' | 'denied' | 'error';

/** onFinal fires once, with the whole transcript, after the button is released. */
export function useHoldToTalk(lang: Lang, onFinal: (text: string) => void) {
  const [state, setState] = useState<TalkState>('idle');
  const [interim, setInterim] = useState('');
  const rec = useRef<SpeechRecognitionLike | null>(null);
  const finalText = useRef('');
  const onFinalRef = useRef(onFinal);
  onFinalRef.current = onFinal;

  useEffect(() => () => rec.current?.abort(), []);

  const start = useCallback(() => {
    if (!Recognition || rec.current) return;
    const r = new Recognition();
    r.lang = speechLang(lang);
    r.continuous = true;
    r.interimResults = true;
    finalText.current = '';
    setInterim('');
    r.onresult = (e) => {
      let live = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) finalText.current += res[0].transcript;
        else live += res[0].transcript;
      }
      setInterim(finalText.current + live);
    };
    r.onerror = (e) => setState(e.error === 'not-allowed' || e.error === 'service-not-allowed' ? 'denied' : 'error');
    r.onend = () => {
      rec.current = null;
      const text = finalText.current.trim();
      setState((s) => (s === 'listening' ? 'done' : s));
      if (text) onFinalRef.current(text);
    };
    rec.current = r;
    setState('listening');
    try {
      r.start();
    } catch {
      rec.current = null;
      setState('error');
    }
  }, [lang]);

  const stop = useCallback(() => {
    // Let the recogniser finish the last words; onend delivers the transcript.
    rec.current?.stop();
  }, []);

  return { state, interim, start, stop, supported: speechSupported };
}
