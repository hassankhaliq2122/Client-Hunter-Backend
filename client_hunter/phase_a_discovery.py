import os
import json
import requests
import csv
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_api_key():
    # Try environment variable first
    key = os.getenv("SERPER_API_KEY")
    if not key:
        print("\n" + "="*50)
        print("SERPER API KEY REQUIRED")
        print("="*50)
        print("To search for leads, you need a free Google Search API key.")
        print("1. Go to https://serper.dev/")
        print("2. Sign up for a free account (gives you 2,500 free searches)")
        print("3. Paste your API key below:")
        key = input("> ").strip()
    return key

def search_organic(query, location, api_key):
    """Fallback: Search for businesses via organic Google Search."""
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": f"{query} {location} website",
        "num": 20
    })
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    print(f"[*] Falling back to Organic Search for '{query}'...")
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code != 200:
            return []
            
        data = response.json()
        organic = data.get("organic", [])
        
        leads = []
        for result in organic:
            link = result.get("link")
            title = result.get("title")
            snippet = result.get("snippet", "")
            
            # Simple heuristic: ignore major platforms that aren't the business itself
            ignore_list = ["booking.com", "tripadvisor", "expedia", "yelp", "facebook", "instagram"]
            if any(domain in link.lower() for domain in ignore_list):
                continue
                
            leads.append({
                "Business Name": title.split("-")[0].split("|")[0].strip(),
                "Website": link,
                "Phone": "N/A (Check Website)",
                "Address": location,
                "Email": ""
            })
        return leads
    except Exception:
        return []

def search_businesses(query, location, api_key):
    """Search for businesses using Google Search via Serper API."""
    url = "https://google.serper.dev/places"
    
    # Attempt to detect country for better results (default to US)
    gl = "us"
    if "london" in location.lower() or "uk" in location.lower() or "united kingdom" in location.lower():
        gl = "gb"
    
    payload = json.dumps({
      "q": f"{query} in {location}",
      "gl": gl,
    })
    headers = {
      'X-API-KEY': api_key,
      'Content-Type': 'application/json'
    }
    
    print(f"\n[*] Searching Google Maps for '{query}' in '{location}' (gl: {gl})...")
    leads = []
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code == 200:
            data = response.json()
            places = data.get("places", [])
            
            for place in places:
                name = place.get("title")
                website = place.get("website")
                phone = place.get("phoneNumber")
                address = place.get("address")
                
                if website: 
                    leads.append({
                        "Business Name": name,
                        "Website": website,
                        "Phone": phone,
                        "Address": address,
                        "Email": ""
                    })
                    print(f"  [+] Found: {name} ({website})")
    except Exception as e:
        print(f"[!] Maps error: {e}")
        
    # FALLBACK: If no leads found via Maps, try Organic Search
    if not leads:
        leads = search_organic(query, location, api_key)
            
    return leads

def save_to_csv(leads, filename="discovered_leads.csv"):
    if not leads:
        print("\n[-] No leads found with websites. Try a broader search.")
        return
        
    keys = leads[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(leads)
    print(f"\n[*] SUCCESS: Saved {len(leads)} high-quality leads to '{filename}'")
    print("[*] These leads are ready for Phase B: The AI Website Analyzer!")

if __name__ == "__main__":
    import sys
    print("=== AI Client Hunter | Phase A: Lead Discovery ===")
    api_key = get_api_key()
    
    if api_key:
        print("\nLet's find some clients.")
        
        # Use command line args if provided, else prompt
        if len(sys.argv) > 2:
            target_niche = sys.argv[1]
            target_location = sys.argv[2]
            print(f"Niche: {target_niche}")
            print(f"Location: {target_location}")
        else:
            target_niche = input("Enter target niche (e.g., 'plumbers', 'med spas', 'boutique hotels'): ").strip()
            target_location = input("Enter target location (e.g., 'London, UK', 'Toronto'): ").strip()
        
        if target_niche and target_location:
            found_leads = search_businesses(target_niche, target_location, api_key)
            save_to_csv(found_leads)
        else:
            print("[!] Niche and location are required.")
    else:
        print("[!] Exiting. A Serper API key is required to query Google.")
