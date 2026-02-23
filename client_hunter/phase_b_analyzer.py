import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_groq_key():
    return os.getenv("GROQ_API_KEY")

def extract_emails(text):
    """Simple regex to found emails in unstructured text."""
    if not text:
        return ""
    # Standard email regex pattern
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    # Return unique emails joined by comma, or empty string
    return ",".join(list(set(emails))) if emails else ""

def scrape_website_text(url, max_chars=3000):
    """Fetch website and extract clean, readable text (preserving headings)."""
    if not url.startswith("http"):
        url = "https://" + url
    print(f"  > Scraping {url} ...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"  [!] Failed to load {url} (Status: {response.status_code})")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove scripts/styles
        for tag in soup(["script", "style"]):
            tag.decompose()
        
        # Preserve headings + paragraphs
        elements = soup.find_all(['h1','h2','h3','h4','p','li'])
        text_chunks = [el.get_text(separator=' ', strip=True) for el in elements]
        text = "\n".join(text_chunks)
        text = " ".join(text.split())  # normalize whitespace
        
        return text[:max_chars]
    except Exception as e:
        print(f"  [!] Error scraping {url}: {e}")
        return None

def analyze_website_with_groq(website_text, business_name):
    """Call Groq REST API to identify one major pain point + solution."""
    api_key = get_groq_key()
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    prompt = f"""
You are an expert web development consultant. 
The business is named: {business_name}.

Analyze the following website text and identify EXACTLY ONE major area of improvement for the website. 
Focus on things like:
- Missing or unclear CTAs
- Confusing messaging
- Outdated design
- Lack of modern features

Return exactly two sentences: 
1) Identify the problem politely but clearly.
2) Suggest a solution (modern, high-converting website).

Website Text:
{website_text}
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
                analysis = result['choices'][0]['message']['content']
                return analysis.strip()
            elif response.status_code == 429:
                print(f"  [!] Rate limited. Waiting {wait}s before retry (Attempt {attempt+1})...")
                time.sleep(wait)
            else:
                print(f"  [!] Groq API Error {response.status_code}: {response.text}")
                # Log a bit of the prompt to see if it's too long or has issues
                print(f"  [DEBUG] Prompt length: {len(prompt)}")
                return f"Could not generate analysis (Error {response.status_code})."
        except Exception as e:
            print(f"  [!] Exception during Groq call: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    
    return "Could not generate analysis due to repeated errors."

def process_leads(input_csv="discovered_leads.csv", output_csv="analyzed_leads.csv"):
    if not os.path.exists(input_csv):
        print(f"[!] Input file '{input_csv}' not found. Run phase_a_discovery.py first.")
        return
    
    api_key = get_groq_key()
    if not api_key:
        print("[!] Groq API key required. Exiting.")
        return
    
    analyzed_leads = []
    
    print("[*] Reading leads...")
    with open(input_csv, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            business_name = row.get("Business Name", "Unknown").strip()
            website = row.get("Website", "").strip()
            
            if website:
                print(f"\n[*] Analyzing {business_name} ({website}) ...")
                website_text = scrape_website_text(website)
                
                if website_text:
                    print("  > Generating analysis with Groq...")
                    analysis = analyze_website_with_groq(website_text, business_name)
                    print(f"  > Analysis: {analysis}")
                    row["Website Analysis"] = analysis
                    
                    # Email Extraction
                    print("  > Extracting emails...")
                    found_emails = extract_emails(website_text)
                    if found_emails:
                        print(f"  > Found emails: {found_emails}")
                        row["Email"] = found_emails
                    else:
                        print("  > No emails found on page.")
                else:
                    print("  [!] Could not scrape website text.")
                    row["Website Analysis"] = "Website unreachable or outdated; candidate for full redesign."
                
                analyzed_leads.append(row)
                
                # Random sleep to reduce rate-limit likelihood
                time.sleep(random.uniform(3,6))
    
    if analyzed_leads:
        keys = analyzed_leads[0].keys()
        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=keys)
            writer.writeheader()
            writer.writerows(analyzed_leads)
        print(f"\n[*] SUCCESS: Saved {len(analyzed_leads)} analyzed leads to '{output_csv}'")
        print("[*] Ready for Phase C: The Cold Email Generator!")
    else:
        print("[!] No leads were successfully analyzed.")

if __name__ == "__main__":
    print("=== AI Client Hunter | Phase B: Website Analyzer ===")
    process_leads()