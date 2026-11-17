import { useRef, useState } from "react";
import { Car, Coffee, ExternalLink, Luggage, Plane, Search, ShieldCheck } from "lucide-react";

import AirportHeader from "../components/AirportHeader";
import AirportToday from "../components/AirportToday";
import ChatAssistant from "../components/ChatAssistant";
import DeparturesBoard from "../components/DeparturesBoard";
import GlassCard from "../components/GlassCard";
import AirportServices from "../components/AirportServices";
import WeatherWidget from "../components/WeatherWidget";
import DocumentAdmin from "../components/DocumentAdmin";

import { useChat } from "../hooks/useChat";
import { useBackendStatus } from "../hooks/useBackendStatus";
import { useWeather } from "../hooks/useWeather";
import { useAuth } from "../auth/useAuth";
import airportImage from "../assets/agadir-airport-real.jpg";

const quickActions = [
  {
    icon: Plane,
    title: "Flight status",
    description: "Check your flight",
    prompt: "I want to check my flight status",
  },
  {
    icon: Luggage,
    title: "Baggage",
    description: "Baggage information",
    prompt: "Where can I find baggage information?",
  },
  {
    icon: Car,
    title: "Transport",
    description: "Taxi and transport",
    prompt: "How can I travel from Agadir airport?",
  },
  {
    icon: ShieldCheck,
    title: "Security",
    description: "Security procedures",
    prompt: "What are the airport security procedures?",
  },
  {
    icon: Coffee,
    title: "Services",
    description: "Airport facilities",
    prompt: "What services are available at the airport?",
  },
];

export default function Home() {
  const assistantRef = useRef(null);
  const flightsRef = useRef(null);

  const [currentLang, setCurrentLang] = useState("EN");

  const { messages, loading: chatLoading, send } = useChat();
  const backendStatus = useBackendStatus();
  const { username, logout, isDocumentAdmin } = useAuth();

  const { weather, loading: weatherLoading, error: weatherError } = useWeather();

  const scrollToAssistant = () => {
    assistantRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const scrollToFlights = () => {
    flightsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleSend = async (text) => {
    return send(text, currentLang.toLowerCase());
  };

  const handleQuickAction = (action) => {
    scrollToAssistant();
    handleSend(action.prompt);
  };

  return (
    <main className="airport-app">
      <AirportHeader
        onAssistantClick={scrollToAssistant}
        onFlightsClick={scrollToFlights}
        username={username}
        onLogout={logout}
        isDocumentAdmin={isDocumentAdmin}
        currentLang={currentLang}
        onSelectLang={setCurrentLang}
      />

      {/* ======================================================
          HERO
      ====================================================== */}
      <section id="home" className="hero-section">
        <div className="hero-container">
          <div className="hero-content">
            <div className="hero-badge">
              <span className="hero-status-dot" />
              AGADIR AL MASSIRA &middot; AGA
            </div>

            <h1>
              Travel with
              <span> peace of mind.</span>
            </h1>

            <p>
              Everything you need for a smoother journey through Agadir Al Massira Airport, all in one place.
            </p>

            <div className="hero-search">
              <Search size={21} />
              <button type="button" onClick={scrollToAssistant}>
                Ask anything about your journey
              </button>
              <button
                type="button"
                className="hero-search-button"
                onClick={scrollToAssistant}
                aria-label="Open assistant"
              >
                <Plane size={18} />
              </button>
            </div>

            <div className="hero-trust">
              <span>AI powered</span>
              <span>Airport information</span>
              <span>Flight assistance</span>
            </div>
          </div>

          <figure className="hero-visual">
            <img
              src={airportImage}
              alt="The main entrance of Agadir Al Massira Airport"
              width="1280"
              height="732"
              fetchPriority="high"
              decoding="async"
            />
            <figcaption className="hero-visual-caption">
              <span>YOUR GATEWAY TO THE SOUTH</span>
              <strong>Agadir, Morocco</strong>
              <small className="hero-photo-credit">
                Photo: <a href="https://commons.wikimedia.org/wiki/File:Agadir_Airport_-_Main_Entrance.jpg" target="_blank" rel="noreferrer">Hamza Izourane / Wikimedia Commons</a>
                {" / "}<a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noreferrer">CC BY-SA 4.0</a>
              </small>
            </figcaption>
            <div className="hero-weather-float">
              <WeatherWidget weather={weather} loading={weatherLoading} />
            </div>
          </figure>
        </div>
      </section>

      <section className="today-section" aria-label="Airport today">
        <div className="section-container today-content">
          <div className="today-intro">
            <span className="section-eyebrow">AT A GLANCE</span>
            <h2>Your airport, today.</h2>
          </div>
          <AirportToday weather={weather} loading={weatherLoading} error={weatherError} />
        </div>
      </section>

      {/* ======================================================
          QUICK ACTIONS
      ====================================================== */}
      <section className="quick-actions-section">
        <div className="section-container">
          <div className="section-heading">
            <span className="section-eyebrow">QUICK ACCESS</span>
            <h2>How can we help you?</h2>
            <p>Choose a topic or ask the assistant anything about your journey.</p>
          </div>

          <div className="quick-actions-grid">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.title}
                  type="button"
                  className="quick-action-card"
                  disabled={chatLoading}
                  onClick={() => handleQuickAction(action)}
                >
                  <div className="quick-action-icon">
                    <Icon size={22} />
                  </div>
                  <div>
                    <strong>{action.title}</strong>
                    <span>{action.description}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      {/* ======================================================
          AI ASSISTANT
      ====================================================== */}
      <section ref={assistantRef} id="assistant" className="assistant-section">
        <div className="section-container">
          <div className="content-section-heading">
            <span className="section-eyebrow">AI ASSISTANT</span>
            <h2>Ask AGA anything</h2>
            <p>Get intelligent answers about the airport and your journey.</p>
          </div>

          <div className="assistant-layout">
            <ChatAssistant
              messages={messages}
              loading={chatLoading}
              connectionStatus={backendStatus}
              lang={currentLang}
              onSend={handleSend}
            />
          </div>
        </div>
      </section>

      {/* ======================================================
          FLIGHT INFORMATION
      ====================================================== */}
      <section ref={flightsRef} id="flights" className="flights-section">
        <div className="section-container">
          <div className="content-section-heading">
            <span className="section-eyebrow">FLIGHT INFORMATION</span>
            <h2>Stay informed</h2>
            <p>Check available flight information and live departures.</p>
          </div>

          <div className="flight-information-layout">
            <GlassCard className="flight-empty-card">
              <Plane size={42} strokeWidth={1.5} />
              <h3>Flight Information</h3>
              <p>Check current flight information through the official airport search.</p>
              <a href="https://www.onda.ma/mobile/Site-Mobile/Recherche" target="_blank" rel="noreferrer">
                Search flights on ONDA <ExternalLink size={14} />
              </a>
            </GlassCard>
            <DeparturesBoard />
          </div>
        </div>
      </section>

      {/* ======================================================
          SERVICES
      ====================================================== */}
      <section id="services" className="services-section">
        <div className="section-container">
          <AirportServices disabled={chatLoading} onSelectService={(prompt) => { scrollToAssistant(); handleSend(prompt); }} />
        </div>
      </section>

      {isDocumentAdmin && <DocumentAdmin />}

      {/* ======================================================
          FOOTER
      ====================================================== */}
      <footer id="contact" className="airport-footer">
        <div className="section-container footer-content">
          <div>
            <strong>AGA Airport Assistant</strong>
            <p>Your digital airport companion.</p>
          </div>
          <div className="footer-note">
            &copy; {new Date().getFullYear()} AGA Airport Assistant
          </div>
        </div>
      </footer>
    </main>
  );
}
