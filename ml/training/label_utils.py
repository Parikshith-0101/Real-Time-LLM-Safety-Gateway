# ml/training/label_utils.py

import pandas as pd
from typing import Dict, Tuple

NORMALIZED_MAPPING: Dict[str, str] = {
    "s": "S",
    "": "S",
    "nan": "S",

    "prompt injection": "Prompt Injection",
    "prompt injection and jailbreak": "Prompt Injection",
    "prompt injection, jailbreak": "Prompt Injection",
    "prompt injection or jailbreak": "Prompt Injection",
    "prompt injection/jailbreak": "Prompt Injection",
    "jailbreak/prompt injection": "Prompt Injection",
    "prompt injection/social engineering": "Prompt Injection",
    "prompt injection/phishing/identity theft": "Prompt Injection",
    "prompt injection, jailbreak, social engineering": "Prompt Injection",
    "malicious prompt injection": "Prompt Injection",
    "malicious prompt": "Prompt Injection",
    "threatening prompt": "Prompt Injection",

    "jailbreak": "Jailbreaking",
    "jailbreak mode": "Jailbreaking",
    "jailbreak and prompt injection": "Jailbreaking",
    "jailbreak/hacking": "Jailbreaking",

    "malware": "Malware Generation",
    "malware injection": "Malware Generation",
    "malware/exploit": "Malware Generation",
    "malicious ai training": "Malware Generation",
    "malicious chatbot creation": "Malware Generation",

    "command injection": "OS Command Execution (RCE)",
    "malicious code execution": "OS Command Execution (RCE)",
    "voice recognition attack": "OS Command Execution (RCE)",
    "code_execution": "OS Command Execution (RCE)",

    "sql injection": "SQL Injection",
    "json injection": "SQL Injection",
    "code injection": "SQL Injection",
    "malicious code injection": "Malicious Code Injection",
    "sql_injection": "SQL Injection",

    "phishing": "Phishing",
    "email phishing attack": "Phishing",
    "password phishing": "Phishing",
    "password harvesting": "Phishing",
    "password cracking": "Phishing",
    "password bypass": "Phishing",
    "phishing/manipulation": "Phishing",
    "phishing/hate speech": "Phishing",
    "social engineering/phishing": "Phishing",

    "hate speech and discrimination": "Hate Speech / Toxicity",
    "hate speech and incitement to violence": "Hate Speech / Toxicity",
    "hate speech and manipulation": "Hate Speech / Toxicity",
    "hate speech and propaganda": "Hate Speech / Toxicity",
    "hate speech and privacy invasion": "Hate Speech / Toxicity",
    "toxic language and behavior": "Hate Speech / Toxicity",
    "verbal attack": "Hate Speech / Toxicity",
    "harmful language": "Hate Speech / Toxicity",

    "social engineering": "Social Engineering",
    "identity theft": "Social Engineering",
    "psychological manipulation": "Social Engineering",
    "psychological manipulation and propaganda": "Social Engineering",
    "emotional manipulation": "Social Engineering",
    "political manipulation": "Social Engineering",
    "false information/disinformation": "Social Engineering",
    "information gathering": "Social Engineering",
    "propaganda": "Social Engineering",

    "role-playing game exploit": "Roleplay / Persona Injection",
    "impersonation": "Roleplay / Persona Injection",
    "persona_switch": "Roleplay / Persona Injection",
    "developer mode simulation": "Developer Mode / Ignore Instructions",
    "developer mode / ignore instructions": "Developer Mode / Ignore Instructions",

    "memory manipulation": "Data Exfiltration / PII Leakage",
    "piracy": "Data Exfiltration / PII Leakage",
    "info_leak": "Data Exfiltration / PII Leakage",
}

LABEL_MAPPING: Dict[str, Tuple[int,int,int,int]] = {
    "S": (0, 0, 0, 0),
    "Prompt Injection": (1, 0, 0, 0),
    "Jailbreaking": (1, 0, 0, 0),
    "Malware Generation": (1, 0, 0, 0),
    "Illegal Activity": (1, 0, 0, 0),
    "Hate Speech / Toxicity": (1, 0, 0, 0),
    "Phishing": (1, 0, 0, 0),
    "Social Engineering": (1, 0, 1, 0),
    "Roleplay / Persona Injection": (1, 1, 0, 0),
    "Developer Mode / Ignore Instructions": (1, 1, 0, 0),
    "Prompt Leakage / System Prompt Extraction": (0, 0, 1, 0),
    "Data Exfiltration / PII Leakage": (0, 0, 1, 0),
    "SQL Injection": (0, 0, 0, 1),
    "Malicious Code Injection": (0, 0, 0, 1),
    "OS Command Execution (RCE)": (0, 0, 0, 1),
}

def normalize_attack_type(raw: str) -> str:
    if pd.isna(raw):
        return "S"
    raw = str(raw).strip().lower()
    return NORMALIZED_MAPPING.get(raw, "S")
