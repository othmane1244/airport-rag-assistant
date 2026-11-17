import {
  Armchair,
  ArrowUpRight,
  Briefcase,
  Car,
  Coins,
  Cross,
  ShoppingBag,
  Utensils,
  Wifi,
} from "lucide-react";

const services = [
  {
    id: "parking",
    label: "Parking",
    description: "Rates, access and parking options",
    icon: Car,
    prompt: "What are the parking rates and options at Agadir Airport?",
  },
  {
    id: "restaurants",
    label: "Food & drink",
    description: "Restaurants, cafés and places to eat",
    icon: Utensils,
    prompt: "What restaurants, cafés and dining options are available at AGA airport?",
  },
  {
    id: "dutyfree",
    label: "Duty Free",
    description: "Shops, products and locations",
    icon: ShoppingBag,
    prompt: "Where are the Duty Free shops located and what items do they sell?",
  },
  {
    id: "lounges",
    label: "Lounges",
    description: "Lounge access and facilities",
    icon: Armchair,
    prompt: "Where are the VIP lounges at Agadir airport and how can I access them?",
  },
  {
    id: "wifi",
    label: "Wi-Fi",
    description: "How to get connected at the airport",
    icon: Wifi,
    prompt: "How do I connect to the free ONDA WiFi at Agadir airport?",
  },
  {
    id: "currency",
    label: "Currency & ATMs",
    description: "Exchange services and cash machines",
    icon: Coins,
    prompt: "Where can I exchange currency or find ATMs at the airport?",
  },
  {
    id: "lostfound",
    label: "Lost property",
    description: "Lost luggage and found items",
    icon: Briefcase,
    prompt: "Where is the lost luggage and lost & found office at Agadir Airport?",
  },
  {
    id: "medical",
    label: "Medical assistance",
    description: "First aid and medical facilities",
    icon: Cross,
    prompt: "Where is the medical center and first aid station at the airport?",
  },
];

export default function AirportServices({ onSelectService, disabled = false }) {
  return (
    <div className="airport-services-card">
      <div className="services-heading">
        <div>
          <span className="services-eyebrow">MAKE YOUR WAY EASIER</span>
          <h2>Airport services</h2>
          <p>Useful information for a smoother time at Agadir Al Massira.</p>
        </div>
        <span className="services-count">{services.length} services</span>
      </div>

      <div className="services-mockup-grid">
        {services.map(({ id, label, description, icon: Icon, prompt }) => (
          <button
            key={id}
            type="button"
            className="service-square-btn"
            disabled={disabled}
            onClick={() => onSelectService?.(prompt)}
          >
            <span className="service-icon-box" aria-hidden="true">
              <Icon size={19} strokeWidth={1.8} />
            </span>
            <span className="service-copy">
              <span className="service-square-label">{label}</span>
              <span className="service-description">{description}</span>
              <span className="service-ask">Ask assistant <ArrowUpRight size={14} /></span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
