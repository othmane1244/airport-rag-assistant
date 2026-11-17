import { useRef, useState } from "react";
import { sendMessage } from "../services/chatService";

const createMessageId = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;

function getErrorMessage(status, language) {
  const messages = {
    en: {
      401: "Your secure session could not be verified. Please sign in again.",
      429: "There are too many requests right now. Please wait a moment and try again.",
      503: "The airport assistant is temporarily unavailable. Please try again shortly.",
      default: "Unable to reach the airport assistant. Check your connection and try again.",
    },
    fr: {
      401: "Votre session sécurisée n’a pas pu être vérifiée. Reconnectez-vous puis réessayez.",
      429: "Il y a trop de demandes pour le moment. Attendez un instant puis réessayez.",
      503: "L’assistant de l’aéroport est momentanément indisponible. Réessayez dans quelques instants.",
      default: "Impossible de joindre l’assistant. Vérifiez votre connexion puis réessayez.",
    },
    ar: {
      401: "تعذر التحقق من جلستك الآمنة. سجّل الدخول مرة أخرى ثم حاول من جديد.",
      429: "عدد الطلبات كبير حالياً. انتظر قليلاً ثم حاول مرة أخرى.",
      503: "مساعد المطار غير متاح مؤقتاً. حاول مرة أخرى بعد قليل.",
      default: "تعذر الاتصال بالمساعد. تحقق من اتصالك بالإنترنت ثم حاول مرة أخرى.",
    },
  };
  const languageMessages = messages[language] || messages.en;
  return languageMessages[status] || languageMessages.default;
}

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const inFlight = useRef(false);

  const send = async (text, lang = "fr") => {
    const question = text?.trim();
    if (!question || inFlight.current) return null;
    inFlight.current = true;

    const timestamp = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMessage = {
      id: createMessageId(), role: "user", type: "text", content: question, lang,
      timestamp: timestamp(),
    };
    setMessages((previous) => [...previous, userMessage]);
    setLoading(true);

    try {
      const response = await sendMessage(question, lang);
      const assistantMessage = {
        id: createMessageId(),
        role: "assistant",
        type: response.type || "text",
        content: response.reply || response.answer || response.message || "Sorry, I couldn’t find an answer.",
        sources: Array.isArray(response.sources) ? response.sources : [],
        lang: response.lang || lang,
        data: response,
        timestamp: timestamp(),
      };
      setMessages((previous) => [...previous, assistantMessage]);
      return response;
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage = {
        id: createMessageId(),
        role: "assistant",
        type: "error",
        content: getErrorMessage(error.response?.status, lang),
        retryText: question,
        lang,
        timestamp: timestamp(),
      };
      setMessages((previous) => [...previous, errorMessage]);
      return null;
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  };

  return { messages, loading, send };
}
