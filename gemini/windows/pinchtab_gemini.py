import requests
import time
import json
import os
import re
import subprocess

def get_pinchtab_token():
    """Tries to retrieve the token from the environment variable, CLI, or config file."""
    # 1. Try environment variable
    token = os.environ.get("PINCHTAB_TOKEN", "").strip()
    if token:
        return token
    
    # 2. Try to fetch from pinchtab CLI (Optimized for Windows)
    try:
        # On Windows, we ALWAYS need shell=True for npm-installed commands
        result = subprocess.run(
            ["pinchtab", "config", "show"], 
            capture_output=True, 
            text=True, 
            check=False, 
            shell=True
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "Token:" in line:
                    t = line.split("Token:", 1)[1].strip()
                    if t: return t
    except Exception:
        pass

    # 3. Fallback: Try reading the config file directly from Windows User Profile
    try:
        home = os.environ.get("USERPROFILE")
        config_path = os.path.join(home, ".pinchtab", "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                t = config.get("server", {}).get("token")
                if t: return t
    except Exception:
        pass
        
    return ""

class PinchtabGeminiClient:
    def __init__(self, base_url="http://localhost:9868", token=None):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def wait_for_ready(self, timeout=60):
        print(f"⏳ [Windows] Waiting for Pinchtab Bridge at {self.base_url}...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                resp = requests.get(f"{self.base_url}/health", timeout=2)
                if resp.status_code in [200, 401]:
                    print("✅ Bridge is reachable!")
                    return True
            except requests.exceptions.ConnectionError:
                pass
            except Exception as e:
                print(f"  (Status check: {e})")
            
            time.sleep(2)
        
        print(f"❌ Timed out waiting for bridge at {self.base_url} after {timeout}s.")
        return False

    def navigate(self, url, tab_id=None, new_tab=False):
        print(f"Navigating to {url}...")
        payload = {"url": url}
        if tab_id:
            payload["tabId"] = tab_id
        if new_tab:
            payload["newTab"] = True
        
        resp = requests.post(f"{self.base_url}/navigate", headers=self.headers, json=payload)
        
        if resp.status_code == 401:
            raise Exception("401 Unauthorized: Pinchtab token is invalid. Run 'pinchtab security down' in CMD.")
            
        resp.raise_for_status()
        return resp.json()

    def get_snapshot(self, filter="interactive", tab_id=None):
        url = f"{self.base_url}/snapshot?filter={filter}"
        if tab_id:
            url += f"&tabId={tab_id}"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    def focus_tab(self, tab_id):
        resp = requests.post(f"{self.base_url}/tab", headers=self.headers, json={
            "action": "focus",
            "tabId": tab_id
        })
        resp.raise_for_status()
        return resp.json()

    def close_tab(self, tab_id):
        resp = requests.post(f"{self.base_url}/close", headers=self.headers, json={
            "tabId": tab_id
        })
        resp.raise_for_status()
        return resp.json()

    def perform_action(self, kind, ref=None, text=None, press_enter=False):
        payload = {"kind": kind}
        if ref: payload["ref"] = ref
        if text: payload["text"] = text
        if press_enter: payload["pressEnter"] = True
        
        resp = requests.post(f"{self.base_url}/action", headers=self.headers, json=payload)
        resp.raise_for_status()
        return resp.json()

    def evaluate_js(self, tab_id, expression):
        resp = requests.post(
            f"{self.base_url}/tabs/{tab_id}/evaluate",
            headers=self.headers,
            json={"expression": expression}
        )
        resp.raise_for_status()
        return resp.json()

    def find_node(self, snapshot, role=None, name=None, testid=None, text_contains=None):
        for node in snapshot.get("nodes", []):
            if role and node.get("role") != role: continue
            if name and node.get("name") != name: continue
            if testid and node.get("testid") != testid: continue
            if text_contains:
                text_val = node.get("text") or ""
                name_val = node.get("name") or ""
                if text_contains not in text_val and text_contains not in name_val:
                    continue
            return node
        return None

    def generate_image(self, prompt):
        print(f"Generating image for prompt: {prompt}")
        nav_res = self.navigate("https://gemini.google.com/app")
        tab_id = nav_res.get("tabId")
        if not tab_id:
            raise Exception("Could not retrieve tab ID")
        time.sleep(5)
        
        self.focus_tab(tab_id)
        snap = self.get_snapshot(tab_id=tab_id)
        prompt_box = self.find_node(snap, role="textbox")
        if not prompt_box:
            raise Exception("Could not find Gemini prompt box")
        
        escaped_prompt = json.dumps(prompt)
        js_expr = f"""
        (() => {{
          const el = document.querySelector('div[contenteditable="true"][aria-label*="Gemini"], div[contenteditable="true"]');
          if (!el) return "Element not found";
          el.focus();
          el.textContent = {escaped_prompt};
          el.dispatchEvent(new Event('input', {{ bubbles: true }}));
          el.dispatchEvent(new Event('change', {{ bubbles: true }}));
          return "Success";
        }})()
        """
        self.evaluate_js(tab_id, js_expr)
        time.sleep(1)
        
        self.focus_tab(tab_id)
        snap = self.get_snapshot(tab_id=tab_id)
        send_btn = self.find_node(snap, name="Send message")
        if not send_btn:
            send_btn = self.find_node(snap, role="button", text_contains="Send")
        if not send_btn or send_btn.get("disabled"):
            raise Exception("Send button not found or disabled")
            
        self.perform_action("click", ref=send_btn["ref"])
        
        for _ in range(15): # Wait up to 75s
            time.sleep(5)
            snap = self.get_snapshot(filter="all", tab_id=tab_id)
            download_btn = self.find_node(snap, role="button", text_contains="Download")
            if download_btn:
                print("Found download button!")
                return True
        
        return False
