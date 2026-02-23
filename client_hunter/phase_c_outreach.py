import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_groq_key():
    return os.getenv("GROQ_API_KEY")

def generate_cold_email(business_name, website, analysis):
    """Uses Groq REST API to draft a hyper-personalized cold email."""
    api_key = get_groq_key()
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    prompt = f"""
You are an expert sales copywriter specializing in cold emails for web development services. 
I want you to write a highly personalized, short, and punchy cold email to the owner of {business_name}.

Here is what we know about their current website ({website}):
{analysis}

Instructions:
1. Subject Line: Make it catchy, relevant to their business name, and subtly hint at a website improvement.
2. Body: Keep it under 100 words. Start by complimenting their business. Then gently bring up the specific pain point mentioned in the analysis. Output a call to action asking for a quick 5-min chat.
3. Tone: Professional but conversational. Not spammy. 

Format:
Subject: [Subject Line here]

Hi [Owner Name or Team],
[Body of email here]

Best,
[Your Name]
Web Solutions Expert
"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    wait_times = [5, 10, 20]
    for attempt, wait in enumerate(wait_times):
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                result = response.json()
                email_draft = result['choices'][0]['message']['content']
                return email_draft.strip()
            elif response.status_code == 429:
                print(f"  [!] Rate limited. Waiting {wait}s before retry (Attempt {attempt+1})...")
                time.sleep(wait)
            else:
                print(f"  [!] Groq API Error {response.status_code}: {response.text}")
                return f"Could not generate email (Error {response.status_code})."
        except Exception as e:
            print(f"  [!] Exception during Groq call: {e}. Retrying in {wait}s...")
            time.sleep(wait)
            
    return "Could not generate email due to repeated errors."


def process_final_leads(input_csv="analyzed_leads.csv", output_csv="final_outreach_list.csv"):
    if not os.path.exists(input_csv):
        print(f"[!] Input file '{input_csv}' not found. Run phase_b_analyzer.py first.")
        return
        
    final_leads = []
    
    print("[*] Reading analyzed leads...")
    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            business_name = row.get("Business Name", "Unknown").strip()
            website = row.get("Website", "").strip()
            analysis = row.get("Website Analysis", "").strip()
            
            if website and analysis and "Could not generate analysis" not in analysis:
                print(f"\n[*] Drafting email for {business_name}...")
                email_draft = generate_cold_email(business_name, website, analysis)
                print(f"  > Email drafted.")
                row["Email Draft"] = email_draft
                final_leads.append(row)
            else:
                print(f"\n[!] Skipping {business_name} (No valid analysis).")
                row["Email Draft"] = "N/A"
                final_leads.append(row)
                
            # Random sleep to be safe
            time.sleep(random.uniform(2, 4))
                
    if final_leads:
        keys = final_leads[0].keys()
        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=keys)
            writer.writeheader()
            writer.writerows(final_leads)
        print(f"\n[*] SUCCESS: Saved {len(final_leads)} final outreaches to '{output_csv}'")
    else:
        print("[!] No leads could be processed.")

if __name__ == "__main__":
    print("=== AI Client Hunter | Phase C: Cold Email Generator (Groq Edition) ===")
    process_final_leads()