import sqlite3
import os
import requests
from datetime import date

def get_db_path():
    """Returns path to data/messages.db using __file__"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(base, "data")
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    return os.path.join(db_dir, "messages.db")

def get_proxycurl_key():
    """Uses exact pattern from PROJECT CONTEXT to get ProxyCurl API key"""
    try:
        import streamlit as st
        return st.secrets.get("PROXYCURL_API_KEY", "")
    except Exception:
        from dotenv import load_dotenv
        import os
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
        )
        load_dotenv(env_path)
        return os.getenv("PROXYCURL_API_KEY", "")

def create_tables():
    """Creates profiles and messages tables if they do not exist"""
    conn = sqlite3.connect(get_db_path())
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                linkedin_url TEXT UNIQUE,
                name TEXT,
                headline TEXT,
                current_role TEXT,
                company TEXT,
                recent_post TEXT,
                scraped_on DATE DEFAULT (DATE('now'))
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER,
                user_bio TEXT,
                tone TEXT,
                output TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id)
            )
        ''')
        conn.commit()
    finally:
        conn.close()

def extract_name_from_url(url):
    """Parses name from LinkedIn URL slug if scraping fails"""
    try:
        # Splits on "/in/", strips trailing slash and query params
        slug = url.split("/in/")[1].split("/")[0].split("?")[0]
        name = slug.replace("-", " ").title()
        return name, slug
    except Exception:
        return "LinkedIn User", "unknown"

def scrape_with_proxycurl(linkedin_url):
    """Calls ProxyCurl API to fetch public LinkedIn profile data"""
    key = get_proxycurl_key()
    if not key or key == "your_proxycurl_api_key_here":
        return None
    
    api_endpoint = "https://nubela.co/proxycurl/api/v2/linkedin"
    params = {"url": linkedin_url, "use_cache": "if-present"}
    headers = {"Authorization": f"Bearer {key}"}
    
    try:
        response = requests.get(api_endpoint, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            headline = data.get('headline', '')
            
            experiences = data.get('experiences', [])
            current_role = experiences[0].get('title', '') if experiences else ''
            company = experiences[0].get('company', '') if experiences else ''
            
            activities = data.get('activities', [])
            recent_post = activities[0].get('title', '')[:200] if activities else ''
            
            return {
                "name": name,
                "headline": headline,
                "current_role": current_role,
                "company": company,
                "recent_post": recent_post
            }
        return None
    except Exception:
        return None

def get_or_create_profile(linkedin_url):
    """Main profile function to get data from cache or scraper"""
    create_tables()
    today = date.today().isoformat()
    
    conn = sqlite3.connect(get_db_path())
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, headline, current_role, company, recent_post FROM profiles WHERE linkedin_url=? AND scraped_on=?",
            (linkedin_url, today)
        )
        row = cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "headline": row[2],
                "current_role": row[3],
                "company": row[4],
                "recent_post": row[5]
            }
        
        # If not found or stale, scrape
        scraped_data = scrape_with_proxycurl(linkedin_url)
        
        if not scraped_data:
            name, _ = extract_name_from_url(linkedin_url)
            scraped_data = {
                "name": name,
                "headline": "Profile data unavailable",
                "current_role": "Unknown",
                "company": "Unknown",
                "recent_post": "No recent posts found"
            }
            
        cursor.execute('''
            INSERT OR REPLACE INTO profiles 
            (linkedin_url, name, headline, current_role, company, recent_post, scraped_on)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (linkedin_url, scraped_data['name'], scraped_data['headline'], 
              scraped_data['current_role'], scraped_data['company'], 
              scraped_data['recent_post'], today))
        
        conn.commit()
        scraped_data["id"] = cursor.lastrowid
        return scraped_data
    finally:
        conn.close()

def save_message(profile_id, user_bio, tone, output):
    """Saves generated message to the messages table"""
    conn = sqlite3.connect(get_db_path())
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (profile_id, user_bio, tone, output)
            VALUES (?, ?, ?, ?)
        ''', (profile_id, user_bio, tone, output))
        conn.commit()
    finally:
        conn.close()

def get_message_history(limit=50):
    """Returns list of formatted message history tuples"""
    conn = sqlite3.connect(get_db_path())
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.name, p.current_role, m.tone, m.output, m.created_at
            FROM messages m JOIN profiles p ON m.profile_id = p.id
            ORDER BY m.created_at DESC LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        conn.close()
