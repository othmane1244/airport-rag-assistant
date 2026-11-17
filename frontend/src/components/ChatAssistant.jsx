import { useEffect, useRef, useState } from "react";
import { Bot, Send, User } from "lucide-react";
import ReactMarkdown from "react-markdown";

const copyByLanguage = {
  en: {
    welcome: "Hello! I’m your AI airport assistant. How can I help you today?",
    suggestions: ["What are the check-in times?", "Where is the duty-free shop?", "How do I get to the city center?", "What services are available?"],
    placeholder: "Ask me anything about the airport…",
    send: "Send message", source: "Sources", dataSources: "Data sources:",
    official: "AGA information", flights: "Flight information", weather: "Weather",
    retry: "Try again", form: "Airport assistant message form",
    status: { checking: "Checking connection", ready: "Assistant ready", unavailable: "Connection issue" },
  },
  fr: {
    welcome: "Bonjour ! Je suis votre assistant de l’aéroport. Comment puis-je vous aider ?",
    suggestions: ["Quels sont les horaires d’enregistrement ?", "Où se trouve le duty free ?", "Comment rejoindre le centre-ville ?", "Quels services sont disponibles ?"],
    placeholder: "Posez une question sur l’aéroport…",
    send: "Envoyer le message", source: "Sources", dataSources: "Sources des données :",
    official: "Informations AGA", flights: "Informations vols", weather: "Météo",
    retry: "Réessayer", form: "Formulaire de discussion avec l’assistant",
    status: { checking: "Connexion…", ready: "Assistant prêt", unavailable: "Problème de connexion" },
  },
  ar: {
    welcome: "مرحباً! أنا مساعد المطار الذكي. كيف يمكنني مساعدتك اليوم؟",
    suggestions: ["ما مواعيد تسجيل الوصول؟", "أين يوجد السوق الحرة؟", "كيف أصل إلى وسط المدينة؟", "ما الخدمات المتاحة؟"],
    placeholder: "اسأل عن المطار…",
    send: "إرسال الرسالة", source: "المصادر", dataSources: "مصادر البيانات:",
    official: "معلومات المطار", flights: "معلومات الرحلات", weather: "الطقس",
    retry: "حاول مرة أخرى", form: "نموذج مراسلة مساعد المطار",
    status: { checking: "جارٍ فحص الاتصال", ready: "المساعد جاهز", unavailable: "مشكلة في الاتصال" },
  },
};

export default function ChatAssistant({ messages = [], loading = false, connectionStatus = "checking", lang = "EN", onSend }) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);
  const language = String(lang).toLowerCase();
  const copy = copyByLanguage[language] || copyByLanguage.en;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, loading]);

  const submitMessage = (text) => {
    const value = text.trim();
    if (!value || loading || !onSend) return;
    setInput("");
    onSend(value);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    submitMessage(input);
  };

  return (
    <div className="chat-assistant-mockup-card mockup-card" dir={language === "ar" ? "rtl" : "ltr"}>
      <div className="chat-header">
        <div className="chat-title-group">
          <div className="bot-header-icon"><Bot size={20} /></div>
          <h3>AI Airport Assistant</h3>
        </div>
        <div className={`online-badge connection-${connectionStatus}`} role="status" aria-live="polite">
          <span className="online-dot" />
          <span>{copy.status[connectionStatus] || copy.status.checking}</span>
        </div>
      </div>

      <div className="chat-body-scrollable" role="log" aria-live="polite" aria-relevant="additions text" aria-busy={loading}>
        {messages.length === 0 && (
          <>
            <div className="msg-row bot-row">
              <div className="msg-bubble-mockup bot-bubble"><p className="welcome-text">{copy.welcome}</p></div>
            </div>
            <div className="suggestion-pills-grid">
              {copy.suggestions.map((suggestion) => (
                <button key={suggestion} type="button" className="mockup-suggestion-pill" onClick={() => submitMessage(suggestion)} disabled={loading}>
                  {suggestion}
                </button>
              ))}
            </div>
          </>
        )}

        {messages.map((message) => {
          const isUser = message.role === "user";
          const messageLanguage = String(message.lang || language).toLowerCase();
          return (
            <div key={message.id} className={`msg-row chat-message-enter ${isUser ? "user-row" : "bot-row"}`} dir={messageLanguage === "ar" ? "rtl" : "auto"}>
              {!isUser && <div className="msg-avatar bot-av" aria-hidden="true"><Bot size={14} /></div>}
              <div className={`msg-bubble-mockup ${isUser ? "user-bubble" : "bot-bubble"}`}>
                <div className="msg-markdown-content"><ReactMarkdown>{message.content}</ReactMarkdown></div>
                {message.sources?.length > 0 && (
                  <div className="msg-sources-tag"><span>{copy.source}: {message.sources.join(", ")}</span></div>
                )}
                {message.type === "error" && message.retryText && (
                  <button type="button" className="chat-retry-button" onClick={() => submitMessage(message.retryText)} disabled={loading}>{copy.retry}</button>
                )}
                <span className="msg-time-stamp">{message.timestamp || "Now"}</span>
              </div>
              {isUser && <div className="msg-avatar user-av" aria-hidden="true"><User size={14} /></div>}
            </div>
          );
        })}

        {loading && (
          <div className="msg-row bot-row" role="status" aria-label={language === "fr" ? "Réponse en cours" : language === "ar" ? "جارٍ إعداد الرد" : "Preparing a reply"}>
            <div className="msg-bubble-mockup bot-bubble typing-bubble"><span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" /></div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-wrapper" onSubmit={handleSubmit} aria-label={copy.form}>
        <input
          type="text"
          className="chat-text-input"
          placeholder={copy.placeholder}
          aria-label={copy.placeholder}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          disabled={loading}
        />
        <button type="submit" className="chat-send-circle-btn" disabled={loading || !input.trim()} aria-label={copy.send}>
          <Send size={16} />
        </button>
      </form>

      <div className="chat-card-footer">
        <span className="data-sources-label">{copy.dataSources}</span>
        <div className="data-sources-tags">
          <span className="source-pill">{copy.official}</span>
          <span className="source-pill">{copy.flights}</span>
          <span className="source-pill">{copy.weather}</span>
        </div>
      </div>
    </div>
  );
}
