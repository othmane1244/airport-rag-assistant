import { useState } from "react";
import { Bot, ChevronDown, Globe, LogOut, Menu, X } from "lucide-react";

export default function AirportHeader({ onAssistantClick, currentLang = "EN", onSelectLang, username, onLogout, isDocumentAdmin = false }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [langDropdown, setLangDropdown] = useState(false);

  const languages = ["EN", "FR", "AR"];

  return (
    <header className="mockup-header">
      <div className="header-inner">
        {/* LOGO */}
        <div className="brand-group">
          <div className="logo-icon-svg">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M16 4C17.2 9 21 12.8 26 14C21 15.2 17.2 19 16 24C14.8 19 11 15.2 6 14C11 12.8 14.8 9 16 4Z" fill="#38bdf8" />
              <path d="M16 10C16.8 13 19 15.2 22 16C19 16.8 16.8 19 16 22C15.2 19 13 16.8 10 16C13 15.2 15.2 13 16 10Z" fill="#ffffff" />
            </svg>
          </div>
          <div className="brand-titles">
            <div className="brand-main">
              <span className="brand-code">AGA</span>
              <span className="brand-sub">AIRPORT ASSISTANT</span>
            </div>
            <span className="brand-location">Agadir Al Massira Airport</span>
          </div>
        </div>

        {/* DESKTOP NAV */}
        <nav className="header-nav" aria-label="Main navigation">
          <a href="#home" className="nav-link">Home</a>
          <a href="#flights" className="nav-link">Flights</a>
          <a href="#services" className="nav-link">Services</a>
          <a href="#assistant" className="nav-link">Assistant</a>
          {isDocumentAdmin && <a href="#document-admin" className="nav-link">Documents</a>}
        </nav>

        {/* RIGHT CONTROLS */}
        <div className="header-controls">
          {/* LANG DROPDOWN */}
          <div className="lang-selector-wrapper">
            <button
              type="button"
              className="lang-btn"
              aria-label="Choose assistant response language"
              aria-expanded={langDropdown}
              onClick={() => setLangDropdown(!langDropdown)}
            >
              <Globe size={16} />
              <span>{currentLang}</span>
              <ChevronDown size={14} />
            </button>
            {langDropdown && (
              <div className="lang-dropdown-menu" role="menu" aria-label="Response language">
                {languages.map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    role="menuitemradio"
                    aria-checked={currentLang === lang}
                    className={`lang-option ${currentLang === lang ? "active" : ""}`}
                    onClick={() => {
                      onSelectLang?.(lang);
                      setLangDropdown(false);
                    }}
                  >
                    {lang === "EN" ? "English (EN)" : lang === "FR" ? "French (FR)" : "Arabic (AR)"}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* AI ASSISTANT BUTTON */}
          <button
            type="button"
            className="ai-assistant-pill-btn"
            onClick={onAssistantClick}
          >
            <Bot size={17} />
            <span>AI Assistant</span>
          </button>
                    <button type="button" className="account-pill-btn" onClick={onLogout} aria-label="Sign out">
            <span className="account-avatar" aria-hidden="true">{(username || "U").slice(0, 1).toUpperCase()}</span>
            <span className="account-name">{username || "Account"}</span>
            <LogOut size={15} aria-hidden="true" />
          </button>

          {/* MOBILE MENU TOGGLE */}
          <button
            type="button"
            className="mobile-toggle"
            aria-expanded={menuOpen}
            aria-label={menuOpen ? "Close navigation" : "Open navigation"}
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* MOBILE NAV DRAWER */}
      {menuOpen && (
        <nav className="mobile-nav-drawer" aria-label="Mobile navigation">
          <a href="#home" onClick={() => setMenuOpen(false)}>Home</a>
          <a href="#flights" onClick={() => setMenuOpen(false)}>Flights</a>
          <a href="#services" onClick={() => setMenuOpen(false)}>Services</a>
          <a href="#assistant" onClick={() => setMenuOpen(false)}>Assistant</a>
          {isDocumentAdmin && <a href="#document-admin" onClick={() => setMenuOpen(false)}>Document administration</a>}
          <button
            type="button"
            className="mobile-ai-btn"
            onClick={() => {
              setMenuOpen(false);
              onAssistantClick?.();
            }}
          >
            <Bot size={18} />
            <span>AI Assistant</span>
          </button>
          <div className="mobile-account-row">
            <span className="account-avatar" aria-hidden="true">{(username || "U").slice(0, 1).toUpperCase()}</span>
            <span className="account-name">{username || "Account"}</span>
            <button type="button" className="mobile-logout" onClick={onLogout}>
              <LogOut size={16} /> Sign out
            </button>
          </div>
        </nav>
      )}
    </header>
  );
}
