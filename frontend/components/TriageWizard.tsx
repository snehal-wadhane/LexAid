"use client";

import { useState } from "react";

interface SubCategory {
  id: string;
  label: string;
  prompt: string;
}

interface Category {
  id: string;
  label: string;
  icon: string;
  apiCategory: string;
  subcategories: SubCategory[];
}

const CATEGORIES: Category[] = [
  {
    id: "labour",
    label: "Labour Rights",
    icon: "⚒️",
    apiCategory: "labour",
    subcategories: [
      { id: "wages",       label: "Unpaid / Below-minimum wages", prompt: "My employer has not paid my salary for the last 2 months. What are my legal rights and what steps can I take under Indian law?" },
      { id: "termination", label: "Wrongful termination",         prompt: "I was terminated from my job without notice or reason. What are my rights under the Industrial Disputes Act?" },
      { id: "pf",          label: "PF / ESI issues",              prompt: "My employer is deducting PF from my salary but not depositing it. What action can I take?" },
      { id: "harassment",  label: "Workplace harassment",         prompt: "I am facing harassment at my workplace. What does Indian law say about my rights and the employer's obligations?" },
    ],
  },
  {
    id: "consumer",
    label: "Consumer Rights",
    icon: "🛒",
    apiCategory: "consumer",
    subcategories: [
      { id: "defective", label: "Defective product / service",  prompt: "I bought a product that is defective and the seller is refusing to replace or refund it. What are my rights under the Consumer Protection Act, 2019?" },
      { id: "refund",    label: "Refund denied",                prompt: "A company is refusing to refund my money for a service that was not delivered. How can I file a consumer complaint?" },
      { id: "fraud",     label: "Online fraud / scam",          prompt: "I was cheated in an online transaction. What legal remedies are available to me under Indian consumer law?" },
      { id: "insurance", label: "Insurance claim rejected",     prompt: "My insurance claim was rejected without valid reasons. What are my options under Indian law?" },
    ],
  },
  {
    id: "criminal",
    label: "Criminal Law",
    icon: "⚖️",
    apiCategory: "criminal",
    subcategories: [
      { id: "fir",        label: "Filing / challenging an FIR", prompt: "I want to file an FIR but the police are refusing to register it. What can I do under Indian criminal law?" },
      { id: "bail",       label: "Bail process",                prompt: "My family member has been arrested. What is the bail process and what are the grounds for getting bail?" },
      { id: "victim",     label: "Victim rights",               prompt: "I am a victim of a crime. What rights do I have under Indian law during investigation and trial?" },
      { id: "cybercrime", label: "Cybercrime",                  prompt: "I am a victim of cybercrime including online harassment. What laws protect me and how do I report it?" },
    ],
  },
  {
    id: "property",
    label: "Property & Rent",
    icon: "🏠",
    apiCategory: "property",
    subcategories: [
      { id: "eviction", label: "Illegal eviction",    prompt: "My landlord is threatening to evict me without proper legal process. What are my rights as a tenant?" },
      { id: "rent",     label: "Rent disputes",       prompt: "My landlord is demanding more rent than agreed and threatening to cut off utilities. What does the law say?" },
      { id: "deposit",  label: "Security deposit",    prompt: "My landlord is refusing to return my security deposit without reason. What legal action can I take?" },
    ],
  },
  {
    id: "administrative",
    label: "RTI & Gov. Services",
    icon: "📋",
    apiCategory: "administrative",
    subcategories: [
      { id: "rti_file",   label: "How to file RTI",           prompt: "How do I file an RTI application? What information can I request and what is the process?" },
      { id: "rti_denied", label: "RTI denied / no response",  prompt: "My RTI application got no response within 30 days. What are my rights and how do I appeal?" },
      { id: "benefits",   label: "Government benefits denied", prompt: "I was denied a government scheme benefit I am entitled to. What legal recourse do I have?" },
    ],
  },
  {
    id: "civil_rights",
    label: "Civil Rights",
    icon: "🤝",
    apiCategory: "civil_rights",
    subcategories: [
      { id: "discrimination", label: "Caste discrimination",     prompt: "I faced caste-based discrimination and abuse. What does the SC/ST Prevention of Atrocities Act say about my rights?" },
      { id: "disability",     label: "Disability rights",        prompt: "I was denied employment because of my disability. What are my rights under the Rights of Persons with Disabilities Act, 2016?" },
      { id: "domestic",       label: "Domestic violence",        prompt: "I am facing domestic violence at home. What protections and remedies does Indian law provide?" },
    ],
  },
];

interface Props {
  onQuery: (question: string, category: string) => void;
}

export function TriageWizard({ onQuery }: Props) {
  const [selectedCat, setSelectedCat] = useState<Category | null>(null);

  const handleSub = (sub: SubCategory, cat: Category) => {
    onQuery(sub.prompt, cat.apiCategory);
    setSelectedCat(null);
  };

  if (selectedCat) {
    return (
      <div className="p-4">
        <button
          onClick={() => setSelectedCat(null)}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-200 mb-3 transition-colors"
        >
          ← back
        </button>
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          {selectedCat.icon} {selectedCat.label}
        </p>
        <div className="flex flex-col gap-2">
          {selectedCat.subcategories.map((sub) => (
            <button
              key={sub.id}
              onClick={() => handleSub(sub, selectedCat)}
              className="text-left text-sm text-gray-200 bg-white/5 hover:bg-orange-500/20 border border-white/10 hover:border-orange-500/40 rounded-lg px-3 py-2.5 transition-all"
            >
              {sub.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        What is your issue?
      </p>
      <div className="flex flex-col gap-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCat(cat)}
            className="text-left text-sm text-gray-200 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg px-3 py-2.5 transition-all flex items-center gap-2"
          >
            <span>{cat.icon}</span>
            <span>{cat.label}</span>
            <span className="ml-auto text-gray-500">›</span>
          </button>
        ))}
      </div>
    </div>
  );
}
