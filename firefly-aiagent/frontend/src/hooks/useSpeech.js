import { useEffect, useRef, useState } from 'react';

const SPEECH_LANGUAGE = 'id-ID';

export function useSpeech(onTranscript) {
  const [isListening, setIsListening] = useState(false);
  const [speechSupported] = useState(
    () => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)
  );
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      return undefined;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = SPEECH_LANGUAGE;
    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join('');
      onTranscript(transcript);
    };
    recognition.onerror = (event) => {
      console.warn('Speech recognition notice:', event.error);
      setIsListening(false);
    };
    recognition.onend = () => setIsListening(false);
    recognitionRef.current = recognition;

    return () => {
      recognition.onstart = null;
      recognition.onresult = null;
      recognition.onerror = null;
      recognition.onend = null;
      recognition.stop();
    };
  }, [onTranscript]);

  const toggleListening = () => {
    if (!speechSupported) {
      alert('Browser Anda belum mendukung Web Speech Recognition. Gunakan Chrome, Edge, atau Safari.');
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      return;
    }

    try {
      recognitionRef.current?.start();
    } catch (error) {
      console.warn('Speech recognition restart error:', error);
    }
  };

  return {
    isListening,
    speechSupported,
    recognitionRef,
    toggleListening,
    stopListening: () => {
      if (isListening) {
        recognitionRef.current?.stop();
      }
    },
  };
}
