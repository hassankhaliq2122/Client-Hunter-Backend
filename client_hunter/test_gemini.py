import google.generativeai as genai
import os

genai.configure(api_key=api_key)

try:
    print("Testing Gemini API...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Say hello")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
