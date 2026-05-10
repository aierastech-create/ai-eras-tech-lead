import json
import streamlit as st
import pandas as pd
import requests
import re
import urllib.parse
from bs4 import BeautifulSoup
import logging
from typing import List, Optional
from playwright.sync_api import sync_playwright, Page
from dataclasses import dataclass, asdict
import platform
import time
import os
import random
from dotenv import load_dotenv
import database as db
import email_utils as email

# --- Load Environment Variables ---
load_dotenv()

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Data Structures ---
@dataclass
class Place:
    name: str = ""
    address: str = ""
    website: str = ""
    phone_number: str = ""
    reviews_count: Optional[int] = None
    reviews_average: Optional[float] = None
    store_shopping: str = "No"
    in_store_pickup: str = "No"
    store_delivery: str = "No"
    place_type: str = ""
    opens_at: str = ""
    introduction: str = ""

# --- Google Maps Scraper Functions ---
def extract_text(page: Page, xpath: str) -> str:
    try:
        if page.locator(xpath).count() > 0:
            return page.locator(xpath).inner_text()
    except Exception as e:
        logging.warning(f"Failed to extract text for xpath {xpath}: {e}")
    return ""

def extract_place(page: Page) -> Place:
    # XPaths
    name_xpath = '//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]'
    address_xpath = '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]'
    website_xpath = '//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]'
    phone_number_xpath = '//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]'
    reviews_count_xpath = '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span//span//span[@aria-label]'
    reviews_average_xpath = '//div[@class="TIHn2 "]//div[@class="fontBodyMedium dmRWX"]//div//span[@aria-hidden]'
    info1 = '//div[@class="LTs0Rc"][1]'
    info2 = '//div[@class="LTs0Rc"][2]'
    info3 = '//div[@class="LTs0Rc"][3]'
    opens_at_xpath = '//button[contains(@data-item-id, "oh")]//div[contains(@class, "fontBodyMedium")]'
    opens_at_xpath2 = '//div[@class="MkV9"]//span[@class="ZDu9vd"]//span[2]'
    place_type_xpath = '//div[@class="LBgpqf"]//button[@class="DkEaL "]'
    intro_xpath = '//div[@class="WeS02d fontBodyMedium"]//div[@class="PYvSYb "]'

    place = Place()
    place.name = extract_text(page, name_xpath)
    place.address = extract_text(page, address_xpath)
    place.website = extract_text(page, website_xpath)
    place.phone_number = extract_text(page, phone_number_xpath)
    place.place_type = extract_text(page, place_type_xpath)
    place.introduction = extract_text(page, intro_xpath) or "None Found"

    # Reviews Count
    reviews_count_raw = extract_text(page, reviews_count_xpath)
    if reviews_count_raw:
        try:
            temp = reviews_count_raw.replace('\xa0', '').replace('(','').replace(')','').replace(',','')
            place.reviews_count = int(temp)
        except Exception as e:
            logging.warning(f"Failed to parse reviews count: {e}")
    # Reviews Average
    reviews_avg_raw = extract_text(page, reviews_average_xpath)
    if reviews_avg_raw:
        try:
            temp = reviews_avg_raw.replace(' ','').replace(',','.')
            place.reviews_average = float(temp)
        except Exception as e:
            logging.warning(f"Failed to parse reviews average: {e}")
    # Store Info
    for idx, info_xpath in enumerate([info1, info2, info3]):
        info_raw = extract_text(page, info_xpath)
        if info_raw:
            temp = info_raw.split('·')
            if len(temp) > 1:
                check = temp[1].replace("\n", "").lower()
                if 'shop' in check:
                    place.store_shopping = "Yes"
                if 'pickup' in check:
                    place.in_store_pickup = "Yes"
                if 'delivery' in check:
                    place.store_delivery = "Yes"
    # Opens At
    opens_at_raw = extract_text(page, opens_at_xpath)
    if opens_at_raw:
        opens = opens_at_raw.split('⋅')
        if len(opens) > 1:
            place.opens_at = opens[1].replace("\u202f","")
        else:
            place.opens_at = opens_at_raw.replace("\u202f","")
    else:
        opens_at2_raw = extract_text(page, opens_at_xpath2)
        if opens_at2_raw:
            opens = opens_at2_raw.split('⋅')
            if len(opens) > 1:
                place.opens_at = opens[1].replace("\u202f","")
            else:
                place.opens_at = opens_at2_raw.replace("\u202f","")
    return place

def scrape_places(search_for: str, total: int, status_placeholder, progress_bar) -> List[Place]:
    places: List[Place] = []
    
    # --- Playwright Browser Management ---
    # Ensure chromium is installed (required for Cloud hosting)
    try:
        import subprocess
        # Check if chromium is already installed to avoid redundant installs
        result = subprocess.run(["playwright", "install", "chromium"], capture_output=True, text=True)
        if result.returncode != 0:
            logging.info(f"Playwright installation output: {result.stdout}")
    except Exception as e:
        logging.warning(f"Note: Playwright browser check skipped or failed: {e}")

    with sync_playwright() as p:
        # Check if we are in a server environment (typically Linux) or local
        is_server = platform.system() != "Windows"
        
        # Use headless=True for server environments
        # You can toggle this to True even locally if you don't want the browser window to pop up
        browser = p.chromium.launch(headless=True if is_server else False)
            
        page = browser.new_page()
        try:
            status_placeholder.text(f"Opening Google Maps and searching for '{search_for}'...")
            page.goto("https://www.google.com/maps/@32.9817464,70.1930781,3.67z?", timeout=60000)
            page.wait_for_timeout(1000)
            page.locator('//input[@name="q"]').fill(search_for)
            page.keyboard.press("Enter")
            page.wait_for_selector('//a[contains(@href, "https://www.google.com/maps/place")]')
            page.hover('//a[contains(@href, "https://www.google.com/maps/place")]')
            previously_counted = 0
            retries = 0
            
            while True:
                # Hover over the last element to ensure scroll targets the sidebar
                elements = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()
                if elements:
                    try:
                        elements[-1].hover()
                    except Exception:
                        pass
                
                page.mouse.wheel(0, 10000)
                page.wait_for_timeout(1500)  # Wait for new elements to load
                
                found = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').count()
                status_placeholder.text(f"Scrolling... Found {found}/{total} listings.")
                
                if found >= total:
                    break
                
                if found == previously_counted:
                    retries += 1
                    if retries >= 3:
                        status_placeholder.text(f"Arrived at all available listings ({found}).")
                        break
                else:
                    retries = 0
                    
                previously_counted = found
                
            listings = page.locator('//a[contains(@href, "https://www.google.com/maps/place")]').all()[:total]
            listings = [listing.locator("xpath=..") for listing in listings]
            
            for idx, listing in enumerate(listings):
                try:
                    status_placeholder.text(f"Extracting details for listing {idx+1}/{len(listings)}...")
                    progress_bar.progress((idx + 1) / len(listings))
                    listing.click()
                    page.wait_for_selector('//div[@class="TIHn2 "]//h1[@class="DUwDvf lfPIob"]', timeout=10000)
                    time.sleep(1.5)  # Give time for details to load
                    place = extract_place(page)
                    if place.name:
                        places.append(place)
                except Exception as e:
                    logging.warning(f"Failed to extract listing {idx+1}: {e}")
        finally:
            browser.close()
    return places

# --- Email Scraper Functions ---
def extract_emails_from_text(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    valid_emails = set()
    for email in emails:
        if not any(email.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg']):
            valid_emails.add(email)
    return list(valid_emails)

def get_emails_from_url(url, timeout=10):
    if not str(url).startswith('http'):
        url = 'https://' + str(url)
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        emails = set()
        for a in soup.find_all('a', href=True):
            if a.get('href') and a['href'].startswith('mailto:'):
                email = a['href'].replace('mailto:', '').split('?')[0].strip()
                if email:
                    emails.add(email)
                    
        text = soup.get_text(separator=' ')
        emails.update(extract_emails_from_text(text))
        return list(emails)
    except Exception as e:
        return []

def scrape_emails_for_dataframe(df, status_placeholder, progress_bar):
    if 'website' not in df.columns:
        return df
        
    df['emails'] = ""
    total = len(df)
    
    for index, row in df.iterrows():
        website = row.get('website')
        status_placeholder.text(f"Scraping emails from ({index+1}/{total}): {website}")
        progress_bar.progress((index + 1) / total)
        
        if pd.isna(website) or not str(website).strip() or str(website).lower() == 'nan':
            continue
            
        emails = get_emails_from_url(website)
        
        if not emails:
            base_url = 'https://' + str(website) if not str(website).startswith('http') else str(website)
            contact_url = urllib.parse.urljoin(base_url, '/contact')
            emails = get_emails_from_url(contact_url)
            
            if not emails:
                contact_us_url = urllib.parse.urljoin(base_url, '/contact-us')
                emails = get_emails_from_url(contact_us_url)
                
        if emails:
            df.at[index, 'emails'] = ", ".join(emails)
            
    return df

# --- Authentication Helpers ---
def send_new_otp(email_addr):
    otp = str(random.randint(100000, 999999))
    db.set_user_otp(email_addr, otp)
    if email.send_otp(email_addr, otp):
        return True
    return False

# --- Streamlit UI ---
def main():
    st.set_page_config(page_title="Scraper Auth System", page_icon="🔐", layout="wide")
    db.init_db()
    admin_email = os.getenv("ADMIN_EMAIL")

    # Session State Initialization
    if 'user' not in st.session_state:
        st.session_state['user'] = None
    if 'auth_mode' not in st.session_state:
        st.session_state['auth_mode'] = 'login'
    if 'verify_email' not in st.session_state:
        st.session_state['verify_email'] = None

    # --- Logout Logic ---
    def logout():
        st.session_state['user'] = None
        st.session_state['verify_email'] = None
        st.rerun()

    # --- Authentication UI ---
    if st.session_state['user'] is None:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.session_state['verify_email']:
                st.title("📧 Verify Email")
                st.info(f"An OTP has been sent to {st.session_state['verify_email']}")
                otp_input = st.text_input("Enter 6-digit OTP", max_chars=6)
                if st.button("Verify OTP", type="primary", use_container_width=True):
                    if db.verify_user_otp(st.session_state['verify_email'], otp_input):
                        st.success("Email verified! You can now login once the admin approves your account.")
                        st.session_state['verify_email'] = None
                        st.session_state['auth_mode'] = 'login'
                        st.rerun()
                    else:
                        st.error("Invalid OTP. Please try again.")
                if st.button("Back to Login"):
                    st.session_state['verify_email'] = None
                    st.rerun()

            elif st.session_state['auth_mode'] == 'login':
                st.title("🔐 Login")
                identifier = st.text_input("Username or Email")
                password = st.text_input("Password", type="password")
                
                if st.button("Login", type="primary", use_container_width=True):
                    user = db.authenticate_user(identifier, password)
                    if user:
                        if not user['is_verified']:
                            st.warning("Please verify your email first.")
                            st.session_state['verify_email'] = user['email']
                            send_new_otp(user['email'])
                            st.rerun()
                        elif not user['is_active']:
                            st.error("🚫 Access Denied. Your account is pending admin approval.")
                        else:
                            st.session_state['user'] = user
                            st.rerun()
                    else:
                        st.error("Invalid credentials.")
                
                st.markdown("---")
                if st.button("Don't have an account? Sign Up"):
                    st.session_state['auth_mode'] = 'signup'
                    st.rerun()

            else:
                st.title("📝 Sign Up")
                new_user = st.text_input("Username")
                new_email = st.text_input("Email")
                new_phone = st.text_input("Phone Number")
                new_pass = st.text_input("Password", type="password")
                
                if st.button("Create Account", type="primary", use_container_width=True):
                    if not new_user or not new_email or not new_pass:
                        st.error("Please fill all required fields.")
                    else:
                        # Auto-admin if it matches ADMIN_EMAIL or if first user
                        is_admin = 1 if new_email == admin_email else 0
                        # If first user, make admin and active
                        users = db.get_all_users()
                        if not users:
                            is_admin = 1
                        
                        if db.register_user(new_user, new_email, new_phone, new_pass, is_admin=is_admin):
                            if is_admin:
                                # Auto active for admin
                                user_in_db = db.get_user_by_email(new_email)
                                db.update_user_status(user_in_db['id'], is_active=True)
                            
                            st.session_state['verify_email'] = new_email
                            send_new_otp(new_email)
                            st.rerun()
                        else:
                            st.error("Username or Email already exists.")
                
                st.markdown("---")
                if st.button("Already have an account? Login"):
                    st.session_state['auth_mode'] = 'login'
                    st.rerun()
        return

    # --- Main Application (Authenticated) ---
    user = st.session_state['user']
    
    # --- Sidebar Navigation ---
    with st.sidebar:
        st.markdown(f"### Welcome, {user['username']}")
        st.caption(f"📧 {user['email']}")
        st.caption(f"📞 {user['phone']}")
        st.divider()
        
        # Navigation Menu
        menu_options = ["🏠 Home & Scraper"]
        if user['is_admin']:
            menu_options.append("🛡️ Admin Panel")
        
        choice = st.radio("Navigation", menu_options)
        st.divider()
        
        if st.button("Logout", use_container_width=True):
            logout()

    # --- Page Content ---
    if choice == "🛡️ Admin Panel" and user['is_admin']:
        st.title("🛡️ Admin Control Center")
        st.markdown("Manage users, monitor sign-ups, and control application access.")
        
        users = db.get_all_users()
        if not users:
            st.info("No users found.")
        else:
            # Filter out the current admin from the management list
            other_users = [u for u in users if u['email'] != user['email']]
            
            st.divider()
            st.subheader("👥 User Management Directory")
            
            if not other_users:
                st.info("No other users have signed up yet.")
            else:
                # Header Row
                h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 2, 2])
                h1.markdown("**Username**")
                h2.markdown("**Email**")
                h3.markdown("**Phone**")
                h4.markdown("**Verified**")
                h5.markdown("**Access Control**")
                st.divider()

                for u in other_users:
                    c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 2])
                    c1.write(u['username'])
                    c2.write(u['email'])
                    c3.write(u['phone'])
                    c4.write("✅ Verified" if u['is_verified'] else "❌ Unverified")
                    
                    with c5:
                        is_active = st.toggle("Allow Access", value=bool(u['is_active']), key=f"act_{u['id']}")
                        if is_active != bool(u['is_active']):
                            db.update_user_status(u['id'], is_active=is_active)
                            st.rerun()
                    
                    with st.expander(f"More options for {u['username']}"):
                        col_del, col_role = st.columns(2)
                        with col_del:
                            if st.button("🗑️ Delete Account", key=f"del_{u['id']}", type="secondary"):
                                db.delete_user(u['id'])
                                st.rerun()
                        with col_role:
                            is_adm = st.checkbox("Make Admin", value=bool(u['is_admin']), key=f"adm_{u['id']}")
                            if is_adm != bool(u['is_admin']):
                                db.update_user_status(u['id'], is_admin=is_adm)
                                st.rerun()
                    st.divider()
        return

    # --- Scraper Content (Default) ---

    # --- Scraper Content ---
    st.title("🗺️ Google Maps Numbers & Email Scraper")
    st.markdown("Easily extract places from Google Maps and find their associated email addresses in one click.")
    
    with st.sidebar:
        st.header("Scraping Settings")
        search_query = st.text_input("Search Query", "turkish stores in toronto Canada")
        total_results = st.number_input("Total Results to Scrape", min_value=1, max_value=500, value=5)
        extract_emails = st.checkbox("Also Extract Emails from Websites", value=True)
        start_button = st.button("Start Scraping", type="primary", use_container_width=True)

    if start_button:
        if not search_query:
            st.error("Please enter a search query.")
            return

        st.subheader("Scraping Progress")
        st.markdown("**Step 1: Scraping Google Maps...**")
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        places = scrape_places(search_query, total_results, status_text, progress_bar)
        if not places:
            st.error("No places found.")
            return
            
        df = pd.DataFrame([asdict(place) for place in places])
        for column in df.columns:
            if df[column].isna().all() or (df[column] == "").all() or (df[column] == "None").all():
                df.drop(column, axis=1, inplace=True)
        status_text.success(f"Successfully scraped {len(df)} places from Google Maps.")
        
        if extract_emails and 'website' in df.columns:
            st.markdown("**Step 2: Extracting Emails...**")
            email_status_text = st.empty()
            email_progress_bar = st.progress(0)
            df = scrape_emails_for_dataframe(df, email_status_text, email_progress_bar)
            email_status_text.success("Email extraction completed!")
            
        st.subheader("Results")
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="Download Data as CSV", data=csv, file_name="scraped_results.csv", mime="text/csv")

if __name__ == "__main__":
    main()
