# lexus_dialog_agent.py
# Efficient, name-aware Lexus recommender:
#  - Body type first
#  - Show only relevant models immediately
#  - Ask only the minimum extra questions needed (#people, exec/family, luxury/fun)
#  - EV short-circuit for RZ
#  - Clean name extraction from free-form text

import random, re, sys

# ------------ Name handling ------------
EXIT_WORDS = {"quit","exit","q"}
HELP_WORDS = {"help","h","?"}

def ask_raw(prompt):
    ans = input(prompt).strip()
    low = ans.lower()
    if low in EXIT_WORDS:
        print("Exiting. Thanks for stopping by!")
        sys.exit(0)
    if low in HELP_WORDS:
        print("Tips: short answers work best. Type 'quit' to exit.")
        return ask_raw(prompt)
    return ans

NAME_PATTERNS = [
    r"\bmy\s+name\s+is\s+([a-zA-Z][a-zA-Z\-' ]+)$",
    r"\bi\s*am\s+([a-zA-Z][a-zA-Z\-' ]+)$",
    r"\bi'm\s+([a-zA-Z][a-zA-Z\-' ]+)$",
    r"\bthis\s+is\s+([a-zA-Z][a-zA-Z\-' ]+)$",
    r"\bit'?s\s+([a-zA-Z][a-zA-Z\-' ]+)$",
]
def clean_word(w): return re.sub(r"[^A-Za-z\-' ]","",w).strip()
def extract_name(raw: str) -> str:
    s = re.sub(r"[\.!\?]+\s*$","",raw.strip())
    low = s.lower()
    for pat in NAME_PATTERNS:
        m = re.search(pat, low)
        if m:
            cand = clean_word(m.group(1))
            parts = [p for p in cand.split() if p]
            if parts: return parts[0].capitalize()
    toks = [clean_word(t) for t in s.split()]
    toks = [t for t in toks if t]
    return toks[-1].capitalize() if toks else "Friend"

# ------------ Knowledge base ------------
# Each profile is a simple set of attributes; we filter down as users answer.
# Note: NX has two variants per your spec (exec-lux & fun). GX per your spec (<4, fun).

MODELS = [
    # --- Electric (BEV) ---
    {"name": "RZ", "body": "crossover", "powertrain": "electric",
     "persona": "executive", "feel": "luxury", "family": ">=4"},

    # --- Sedans ---
    {"name": "LS", "body": "sedan", "powertrain": "gas/hybrid",
     "persona": "executive", "feel": "luxury", "family": "<4"},
    {"name": "ES", "body": "sedan", "powertrain": "gas/hybrid",
     "persona": "family", "feel": "luxury", "family": "<4"},
    {"name": "IS", "body": "sedan", "powertrain": "gas",
     "persona": "executive", "feel": "fun", "family": "<4"},

    # --- Coupes / Grand Tourers ---
    {"name": "LC", "body": "coupe", "powertrain": "gas/hybrid",
     "persona": "executive", "feel": "luxury", "family": "<4"},
    {"name": "RC", "body": "coupe", "powertrain": "gas",
     "persona": "executive", "feel": "fun", "family": "<4"},

    # --- Crossovers / SUVs ---
    # Compact route (Executive → UX, Family → NX)
    {"name": "UX", "body": "crossover", "powertrain": "hybrid",
     "persona": "executive", "feel": "luxury", "family": "<4"},
    {"name": "NX", "body": "crossover", "powertrain": "gas/hybrid/phev",
     "persona": "family", "feel": "luxury", "family": "<4"},
    # (Optional second NX profile if you still want a “fun” flavor in compact)
    {"name": "NX", "body": "crossover", "powertrain": "gas/hybrid/phev",
     "persona": "executive", "feel": "fun", "family": "<4"},

    # Mid-size route (Executive → RZ, Family → RX, Fun → GX)
    {"name": "RX", "body": "crossover", "powertrain": "gas/hybrid/phev",
     "persona": "family", "feel": "luxury", "family": ">=4"},
    {"name": "GX", "body": "suv", "powertrain": "gas",
     "persona": "family", "feel": "fun", "family": ">=4"},

    # Full-size route (Executive → LX, Family → TX)
    {"name": "LX", "body": "suv", "powertrain": "gas",
     "persona": "executive", "feel": "luxury", "family": ">=4"},
    {"name": "TX", "body": "crossover", "powertrain": "gas/hybrid/phev",
     "persona": "family", "feel": "luxury", "family": ">=4"},
]

EXPLAINS = {
    "RZ":"All-electric luxury crossover (quiet, punchy, tech-forward).",
    "NX":"Compact luxury crossover; agile size, premium cabin.",
    "RX":"Midsize luxury crossover; comfy and family-friendly.",
    "LS":"Flagship luxury sedan; serene, executive vibe.",
    "ES":"Comfort-focused sedan; smooth, quiet daily driver.",
    "IS":"Sporty compact sedan; engaging drive.",
    "RC":"Sporty coupe; 2-door style + fun.",
    "LC":"Grand-tourer luxury coupe; flagship 2-door with refined power.",
    "LX":"Full-size luxury SUV; space and presence (≥4).",
    "GX":"Body-on-frame SUV; adventurous, fun-leaning.",
    "UX":"Subcompact luxury crossover; tidy size and great efficiency.",
    "TX":"Three-row full-size luxury crossover; roomy and family-first.",
}

# Price ranges per model (uppercase keys, en-dash)
PRICE_RANGES = {
    "LS": "$80K–$115K",
    "ES": "$45K–$55K",
    "IS": "$40K–$65K",
    "LC": "$100K–$105K",
    "RC": "$45K–$95K",
    "UX": "$40K–$45K",
    "NX": "$40K–$65K",
    "RZ": "$45K–$60K",
    "RX": "$50K–$75K",
    "GX": "$65K–$85K",
    "LX": "$105K–$140K",
    "TX": "$60K-100K"
}

# Helper for consistent recommendation output
def print_recommendation(name, model):
    print(f"\n{name}, my recommendation is: **{model}**")
    explain = EXPLAINS.get(model)
    if explain:
        print(explain)
    price = PRICE_RANGES.get(model)
    if price:
        print(f"Approx. price range: {price}")

# Synonym maps
YES = {"y","yes","yeah","yep","sure","ok","okay","absolutely","of course","for sure","ye","yeh", "let's do it","fs","bet","let's run it","type shit","yea"}
NO  = {"n","no","nope","nah","hell no","na","I'm good", "I'm alright","Im okay","fuck no","hell no","hell nah"}
BODIES = {
    "sedan": {"sedan", "saloon"},
    "coupe": {"coupe", "2-door", "two door"},
    "crossover_suv": {
        "crossover", "cuv", "cross-over", "cross over", "suv", "sport utility", "sport-utility",
        "crossover/suv", "crossover suv"
    },
    "electric": {
        "ev", "electric", "electric vehicle", "bev", "let's do ev", "i'd prefer ev"
    },
}
PEOPLE = {"<4":{"<4","1","2","3","one","two","three","small"},
          ">=4":{">=4","4","5","6","7","8","four","five","six","seven","eight","big"}}
PERSONA = {"executive":{"executive","exec","premium"},
           "family":{"family","roomy","spacious"}}
FEEL = {"luxury":{"luxury","comfort","quiet","plush","relaxed"},
        "fun":{"fun","sport","sporty","engaging","lively","fast"}}

SIZE = {
    "compact": {"compact", "small"},
    "mid-size": {"mid-size", "midsize", "mid size"},
    "full-size": {"full-size", "full size", "large"},
}


# --- Normalization helpers that match keywords inside sentences ---
import re
def _contains_term(ans: str, term: str) -> bool:
    a = ans.strip().lower()
    t = term.strip().lower()
    if not t:
        return False
    # Use regex boundaries for alphanumerics; allow separators like "/" and "-" within terms
    if any(ch.isalnum() for ch in t):
        pattern = r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])"
        return re.search(pattern, a) is not None
    # Fallback simple substring for non-alphanumeric terms
    return t in a

def norm(ans, mapping):
    a = ans.strip().lower()
    # direct key match or contained key word
    for k, syn in mapping.items():
        if a == k or _contains_term(a, k):
            return k
        for s in syn:
            if a == s or _contains_term(a, s):
                return k
    return None


def norm_from_subset(ans, mapping, allowed_keys):
    a = ans.strip().lower()
    for k in allowed_keys:
        syn = mapping.get(k)
        if syn is None:
            continue
        if a == k or _contains_term(a, k):
            return k
        for s in syn:
            if a == s or _contains_term(a, s):
                return k
    return None

# --- Helper for robustly parsing crew size from free-form text ---
NUM_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "couple": 2, "a couple": 2, "few": 3,
}

def detect_family_bucket(ans: str):
    """Return '<4' or '>=4' if we can infer group size from free-form input like
    'like 6 people', 'usually two', 'i have 5 people in my family',
    'i often drive two other people'. If none detected, return None."""
    s = ans.strip().lower()
    # collect digits
    nums = [int(x) for x in re.findall(r"\d+", s)]
    # collect number words
    for word, val in NUM_WORDS.items():
        # use word boundary matching for standalone words/phrases
        if re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", s):
            nums.append(val)
    if not nums:
        return None
    n = max(nums)
    return ">=4" if n >= 4 else "<4"

def choices_label(keys):
    keys = list(keys)
    if len(keys) == 0:
        return ""
    if len(keys) == 1:
        return keys[0]
    if len(keys) == 2:
        return f"{keys[0]} or {keys[1]}"
    return ", ".join(keys[:-1]) + ", or " + keys[-1]

# ------------ Filtering helpers ------------
def present(models):
    names = sorted({m["name"] for m in models})
    return ", ".join(names)

def filter_attr(cands, key, value):
    return [m for m in cands if m.get(key)==value]

def need_attr(cands, key):
    vals = {m.get(key) for m in cands}
    return len(vals) > 1

def ask_and_filter(name, label, cands, mapping, key, variants):
    if not need_attr(cands, key):
        return cands, list({m[key] for m in cands})[0]
    prompt = random.choice(variants).format(name=name)
    while True:
        raw = ask_raw(prompt+"\n> ")
        ans = norm(raw, mapping)
        if not ans and key == "family":
            bucket = detect_family_bucket(raw)
            if bucket:
                ans = bucket
        if ans:
            cands = filter_attr(cands, key, ans)
            return cands, ans
        allowed = ", ".join(mapping.keys())
        print(f"Sorry {name}, please choose one of: {allowed}.")

# ------------ Question variants ------------
Q_NAME = [
    "Welcome to Lexus. May I have your name so I can provide a more personal experience?",
    "It’s a pleasure to meet you. May I have your name so I can assist you properly?",
    "Welcome to the Lexus showroom. How may I address you today?"
]
Q_BODY = [
    "{name}, which body style are you interested in exploring today? (Sedan / Coupe / Crossover/SUV / Electric)",
    "Let’s begin with the type of vehicle you’re drawn to, {name}: Sedan, Coupe, Crossover/SUV, or Electric?"
]
Q_BODY_LIMITED = [
    "Based on your needs, {name}, which body style would you like to focus on: {choices}?",
    "Given your typical passengers, {name}, which body type makes the most sense: {choices}?"
]
Q_OK_WITH = [
    "These are the matching options: {options}. Good with focusing on these, {name}? (yes/no)",
    "Here’s what fits that type: {options}. Stick with these, {name}? (yes/no)",
]
Q_PEOPLE = [
    "How many people do you usually travel with, {name}? (for example, 2 or 5+)",
    "Roughly how many passengers do you often have, {name}? (1–3 or 4+)"
]
Q_PERSONA = [
    "And in terms of lifestyle, {name}, would you describe yourself as more executive or family-focused? (executive/family)",
    "Would you say your ideal Lexus complements an executive lifestyle or suits a family-oriented one, {name}? (executive/family)"
]
Q_FEEL = [
    "Let’s talk about how you’d like your Lexus Sedan to drive, {name}.\n• Luxury — a serene, quiet ride that exudes refinement\n• Fun — a more dynamic, engaging experience\n(luxury/fun)",
    "When you picture driving your new Sedan, {name}, do you lean toward luxurious comfort or a sportier, fun feel? (luxury/fun)"
]

Q_RZ_CONFIRM = [
    "{name}, Lexus offers a single all-electric model—the **RZ**. It’s a refined, quiet crossover with instant torque. Approx. price range: $45K–$60K. Shall we proceed with RZ? (yes/no)",
    "Quick note, {name}: the all-electric option is the **RZ**, an elegant crossover with seamless power. Estimated price band: $45K–$60K. Would you like to go with RZ? (yes/no)",
]


Q_BRAND_INTENT = [
    "Wonderful to meet you, {name}. Are you considering joining the Lexus family today? (yes/no)",
    "Quick question, {name}: is Lexus the brand you'd like to explore right now? (yes/no)",
    "Before we begin, {name}, are you exploring Lexus vehicles today? (yes/no)"
]

# --- New prompts for keeping same car type ---
Q_KEEP_SAME = [
    "Would you like to keep the same car type you have now, {name}? (yes/no)",
    "Do you want to stick with your current car type, {name}? (yes/no)",
    "Should we keep the same body style you drive today, {name}? (yes/no)",
]
Q_CURRENT_TYPE = [
    "What type do you drive now, {name}? (sedan / coupe / crossover_suv / electric)",
    "Which body style is your current car, {name}? (sedan / coupe / crossover_suv / electric)",
    "Tell me your current type, {name}: sedan, coupe, crossover_suv, or electric",
]

Q_SIZE = [
    "For your Crossover or SUV, {name}, which size best fits your lifestyle?\n• Compact — easy maneuverability, lower cost\n• Mid-size — balanced comfort and performance\n• Full-size — spacious, three rows, elevated presence\n(compact/mid-size/full-size)",
    "Let’s find the right fit, {name}: Compact for agility, Mid-size for balance, or Full-size for maximum space and comfort? (compact/mid-size/full-size)"
]
Q_SEDAN_FEEL = [
    "Let’s tailor the drive, {name}.\n• Luxury — serene, quiet ride with plush refinement\n• Fun — sportier handling and more responsive character\n(luxury/fun)",
    "Thinking about driving feel, {name}:\nLuxury = smooth, hushed, comfort‑first.\nFun = lively, engaging, sport‑leaning.\n(luxury/fun)",
]
Q_COUPE_FEEL = [
    "For your Coupe, which personality suits you, {name}?\n• Luxury — grand‑touring poise and comfort\n• Fun — playful, sporty dynamics\n(luxury/fun)",
    "Coupe character, {name}:\nLuxury = GT comfort and polish.\nFun = sharper, more spirited feel.\n(luxury/fun)",
]
Q_SEDAN_PERSONA = [
    "And the overall vibe for your Sedan, {name}?\n• Executive — premium ambiance, advanced tech, refined materials\n• Family — space, ease of use, and everyday comfort\n(executive/family)",
    "Last preference for the Sedan, {name}:\nExecutive = upscale, polished feel.\nFamily = practicality and comfort for passengers.\n(executive/family)",
]
Q_COMPACT_PERSONA = [
    "For a Compact Crossover, which focus do you prefer, {name}?\n• Executive — premium ambiance and tech\n• Family — comfort, versatility, and ease of use\n(executive/family)",
]
Q_MIDSIZE_PREF = [
    "Within Mid‑size, what should we emphasize, {name}?\n• Executive — refined, quiet, premium experience\n• Family — comfort, versatility, and serene ride\n• Fun — adventurous look and capability\n(executive/family/fun)",
]
Q_FULLSIZE_PERSONA = [
    "For a Full‑size SUV, which direction suits you best, {name}?\n• Executive — presence, premium materials, quiet cabin\n• Family — maximum space, easy access, road‑trip comfort\n(executive/family)",
]

# ------------ Main flow ------------
def main():
    print("Type 'help' for tips or 'quit' to exit at any time.")

    # 0) Name
    while True:
        raw = ask_raw(random.choice(Q_NAME)+"\n> ")
        name = extract_name(raw)
        if name and name.lower()!="friend": break
        print("Please share your name so I can address you properly.")

    # Brand intent check
    while True:
        intent = norm_from_subset(
            ask_raw(random.choice(Q_BRAND_INTENT).format(name=name) + "\n> "),
            {"yes": YES, "no": NO},
            ["yes", "no"]
        )
        if intent:
            break
        print("Please answer yes or no.")
    if intent == "no":
        print("No worries! If you ever want Lexus recommendations, just say hi. Have a great day!")
        return


    # Keep same car type?
    while True:
        keep_same = norm_from_subset(
            ask_raw(random.choice(Q_KEEP_SAME).format(name=name) + "\n> "),
            {"yes": YES, "no": NO},
            ["yes", "no"]
        )
        if keep_same:
            break
        print("Please answer yes or no.")

    if keep_same == "yes":
        # Ask current type and route immediately
        allowed_now = ["sedan", "coupe", "crossover_suv", "electric"]
        while True:
            body_ans = norm_from_subset(
                ask_raw(random.choice(Q_CURRENT_TYPE).format(name=name) + "\n> "),
                BODIES,
                allowed_now
            )
            if body_ans:
                break
            print(f"Please choose one of: {choices_label(allowed_now)}.")

        # EV short-circuit
        if body_ans == "electric":
            yn = norm(ask_raw(random.choice(Q_RZ_CONFIRM).format(name=name)+"\n> "), {"yes":YES,"no":NO})
            if yn == "yes":
                pick = "RZ"
                print_recommendation(name, pick)
                return
            body_ans = "crossover_suv"

        # Route by body
        if body_ans == "sedan":
            feel_ans = None
            while True:
                feel_ans = norm(ask_raw(random.choice(Q_SEDAN_FEEL).format(name=name)+"\n> "), FEEL)
                if feel_ans:
                  break
                print("Please choose: luxury or fun.")
            persona_ans = None
            while True:
                persona_ans = norm(ask_raw(random.choice(Q_SEDAN_PERSONA).format(name=name)+"\n> "), PERSONA)
                if persona_ans:
                  break
                print("Please choose: executive or family.")
            if feel_ans == "luxury" and persona_ans == "executive":
                model = "LS"
            elif feel_ans == "luxury" and persona_ans == "family":
                model = "ES"
            elif feel_ans == "fun" and persona_ans == "executive":
                model = "IS"
            else:
                model = "IS"
            print_recommendation(name, model)
            return

        if body_ans == "coupe":
            feel_ans = None
            while True:
                feel_ans = norm(ask_raw(random.choice(Q_COUPE_FEEL).format(name=name)+"\n> "), FEEL)
                if feel_ans:
                  break
                print("Please choose: luxury or fun.")
            model = "RC" if feel_ans == "fun" else "LC"
            print_recommendation(name, model)
            return

        if body_ans == "crossover_suv":
            size_ans = None
            while True:
                size_ans = norm(ask_raw(random.choice(Q_SIZE).format(name=name)+"\n> "), SIZE)
                if size_ans:
                  break
                print("Please choose: compact, mid-size, or full-size.")

            if size_ans == "compact":
                persona_ans = None
                while True:
                    persona_ans = norm(ask_raw(random.choice(Q_COMPACT_PERSONA).format(name=name)+"\n> "), PERSONA)
                    if persona_ans:
                      break
                    print("Please choose: executive or family.")
                model = "NX" if persona_ans == "family" else "UX"
                print_recommendation(name, model)
                return
            elif size_ans == "mid-size":
                mid_keys = ["executive","family","fun"]
                pref_ans = None
                while True:
                    pref_ans = norm_from_subset(ask_raw(random.choice(Q_MIDSIZE_PREF).format(name=name)+"\n> "), {**PERSONA, **FEEL}, mid_keys)
                    if pref_ans:
                      break
                    print("Please choose: executive, family, or fun.")
                if pref_ans == "executive":
                    model = "RZ"
                elif pref_ans == "family":
                    model = "RX"
                else:
                    model = "GX"
                print_recommendation(name, model)
                return
            else:  # full-size
                persona_ans = None
                while True:
                    persona_ans = norm(ask_raw(random.choice(Q_FULLSIZE_PERSONA).format(name=name)+"\n> "), PERSONA)
                    if persona_ans:
                      break
                    print("Please choose: executive or family.")
                model = "TX" if persona_ans == "family" else "LX"
                print_recommendation(name, model)
                return

    # 1) People (family size)
    while True:
        raw = ask_raw(random.choice(Q_PEOPLE).format(name=name)+"\n> ")
        family_ans = norm(raw, PEOPLE)
        if not family_ans:
            inferred = detect_family_bucket(raw)
            if inferred:
                family_ans = inferred
        if not family_ans:
            print("Please choose: <4 or >=4.")
            continue
        break

    # 2) Body type limited by family size
    if family_ans == ">=4":
        allowed_bodies = ["crossover_suv", "electric"]
    else:
        allowed_bodies = ["sedan", "coupe", "crossover_suv", "electric"]

    while True:
        prompt = random.choice(Q_BODY_LIMITED).format(name=name, choices=choices_label(allowed_bodies))
        body_ans = norm_from_subset(ask_raw(prompt+"\n> "), BODIES, allowed_bodies)
        if not body_ans:
            print(f"Please choose one of: {choices_label(allowed_bodies)}.")
            continue

        # EV short-circuit
        if body_ans == "electric":
            # Offer RZ directly
            yn = norm(ask_raw(random.choice(Q_RZ_CONFIRM).format(name=name)+"\n> "), {"yes":YES,"no":NO})
            if yn == "yes":
                pick = "RZ"
                print_recommendation(name, pick)
                return
            # If no, fall back to crossover_suv pool
            body_ans = "crossover_suv"

        if body_ans == "sedan":
            # Ask feel
            feel_ans = None
            while True:
                feel_ans = norm(ask_raw(random.choice(Q_SEDAN_FEEL).format(name=name)+"\n> "), FEEL)
                if feel_ans:
                    break
                print(f"Please choose: luxury or fun.")
            # Ask persona
            persona_ans = None
            while True:
                persona_ans = norm(ask_raw(random.choice(Q_SEDAN_PERSONA).format(name=name)+"\n> "), PERSONA)
                if persona_ans:
                    break
                print(f"Please choose: executive or family.")
            # Map to model
            if feel_ans == "luxury" and persona_ans == "executive":
                model = "LS"
            elif feel_ans == "luxury" and persona_ans == "family":
                model = "ES"
            elif feel_ans == "fun" and persona_ans == "executive":
                model = "IS"
            else:  # fun & family default to IS
                model = "IS"
            print_recommendation(name, model)
            return

        if body_ans == "coupe":
            # Ask feel
            feel_ans = None
            while True:
                feel_ans = norm(ask_raw(random.choice(Q_COUPE_FEEL).format(name=name)+"\n> "), FEEL)
                if feel_ans:
                    break
                print(f"Please choose: luxury or fun.")
            # Map to model
            if feel_ans == "fun":
                model = "RC"
            else:  # luxury
                model = "LC"
            print_recommendation(name, model)
            return

        if body_ans == "crossover_suv":
            # Ask size
            size_ans = None
            while True:
                size_ans = norm(ask_raw(random.choice(Q_SIZE).format(name=name)+"\n> "), SIZE)
                if size_ans:
                    break
                print(f"Please choose: compact, mid-size, or full-size.")

            if size_ans == "compact":
                # Ask persona
                persona_ans = None
                while True:
                    persona_ans = norm(ask_raw(random.choice(Q_COMPACT_PERSONA).format(name=name)+"\n> "), PERSONA)
                    if persona_ans:
                        break
                    print(f"Please choose: executive or family.")
                if persona_ans == "family":
                    model = "NX"
                else:  # executive
                    model = "UX"
                print_recommendation(name, model)
                return

            elif size_ans == "mid-size":
                # Ask preference among executive, family, fun
                mid_keys = ["executive","family","fun"]
                pref_ans = None
                while True:
                    pref_ans = norm_from_subset(ask_raw(random.choice(Q_MIDSIZE_PREF).format(name=name)+"\n> "), {**PERSONA, **FEEL}, mid_keys)
                    if pref_ans:
                        break
                    print(f"Please choose: executive, family, or fun.")
                if pref_ans == "executive":
                    model = "RZ"
                elif pref_ans == "family":
                    model = "RX"
                else:  # fun
                    model = "GX"
                print_recommendation(name, model)
                return

            else:  # full-size
                # Ask persona
                persona_ans = None
                while True:
                    persona_ans = norm(ask_raw(random.choice(Q_FULLSIZE_PERSONA).format(name=name)+"\n> "), PERSONA)
                    if persona_ans:
                        break
                    print(f"Please choose: executive or family.")
                if persona_ans == "family":
                    model = "TX"
                else:  # executive
                    model = "LX"
                print_recommendation(name, model)
                return

if __name__ == "__main__":
    main()