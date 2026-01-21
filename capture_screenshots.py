from playwright.sync_api import sync_playwright
import time
import os

def capture():
    # Ensure directory exists
    os.makedirs('static/screenshots', exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        base_url = "http://127.0.0.1:5000"

        # --- 1. Student Dashboard ---
        print("Capturing Student Dashboard...")
        page.goto(f"{base_url}/login")
        page.fill('input[name="email"]', 'rahul@test.com')
        page.fill('input[name="password"]', 'pass123')
        page.click('button[type="submit"]')
        page.wait_for_selector('h1', timeout=10000) 
        time.sleep(1) # Visual settle
        page.screenshot(path="static/screenshots/student_dashboard.png")
        page.goto(f"{base_url}/logout")

        # --- 2. Provider Dashboard ---
        print("Capturing Provider Dashboard...")
        page.goto(f"{base_url}/login")
        page.fill('input[name="email"]', 'tesla@test.com')
        page.fill('input[name="password"]', 'pass123')
        page.click('button[type="submit"]')
        page.wait_for_selector('h1', timeout=10000)
        time.sleep(1)
        page.screenshot(path="static/screenshots/provider_dashboard.png")
        page.goto(f"{base_url}/logout")

        # --- 3. College Dashboard ---
        print("Capturing College Dashboard...")
        page.goto(f"{base_url}/login")
        page.fill('input[name="email"]', 'anna@test.com')
        page.fill('input[name="password"]', 'pass123')
        page.click('button[type="submit"]')
        page.wait_for_selector('h1', timeout=10000)
        time.sleep(1)
        page.screenshot(path="static/screenshots/college_dashboard.png")
        page.goto(f"{base_url}/logout")

        # --- 4. Home Page ---
        print("Capturing Home Page...")
        page.goto(f"{base_url}/")
        page.wait_for_selector('.hero')
        time.sleep(1)
        page.screenshot(path="static/screenshots/home_page.png")

        browser.close()
        print("All screenshots captured in static/screenshots/")

if __name__ == "__main__":
    try:
        capture()
    except Exception as e:
        print(f"Error capturing screenshots: {e}")
        print("Ensure the server is running on port 5000!")
