import os, io, csv, time, random, requests, threading, subprocess, json
from PIL import Image, ImageStat
import gradio as gr
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pinchtab_gemini import PinchtabGeminiClient, get_pinchtab_token

# ──────────────────────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────────────────────
PINCHTAB_TOKEN = get_pinchtab_token()
if PINCHTAB_TOKEN:
    print(f"🔑 Pinchtab token found: {PINCHTAB_TOKEN[:4]}...{PINCHTAB_TOKEN[-4:]}")
else:
    print("⚠️ No Pinchtab token found. If you get 401 errors, set PINCHTAB_TOKEN env var or check 'pinchtab config'.")

PINCHTAB_URL = os.environ.get("PINCHTAB_URL", "http://localhost:9868")

OUTPUT_DIR     = "generated_rings_browser"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MAX_RETRIES           = 2
INPUT_MAX_PX = 1024
PNG_COMPRESS_LEVEL = 1
MAX_SUMMARY_LOG_LINES = 20
MAX_GALLERY_ITEMS = 24

# ──────────────────────────────────────────────────────────────
#  PINCHTAB CLIENT
# ──────────────────────────────────────────────────────────────
client = PinchtabGeminiClient(base_url=PINCHTAB_URL, token=PINCHTAB_TOKEN)

# ──────────────────────────────────────────────────────────────
#  QUALITY PROMPT
# ──────────────────────────────────────────────────────────────
def build_prompt(custom: str = "") -> str:
    prompt = """You are a professional jewelry product photographer and retoucher.
You will receive exactly two reference images:
  IMAGE 1 = the RING MODEL (source of structure)
  IMAGE 2 = the STONE REFERENCE (source of stone appearance only)

YOUR TASK:
Generate a single photorealistic product image of the ring from IMAGE 1,
with ONLY its gemstone replaced by the stone shown in IMAGE 2.

WHAT TO KEEP EXACTLY AS-IS FROM IMAGE 1:
  1. Ring band shape, width, and profile
  2. Metal color and finish (yellow gold / rose gold / silver / platinum)
  3. Prong count, prong shape, and prong placement
  4. Setting style (solitaire / halo / pavé / channel / bezel — whatever is shown)
  5. Any side stones, milgrain, engraving, or decorative metalwork
  6. Ring size and proportions

WHAT TO TAKE FROM IMAGE 2 (stone only):
  1. Gemstone color and hue (e.g. deep blue, vivid green, blush pink)
  2. Cut shape (round / oval / cushion / emerald / pear — whatever is shown)
  3. Facet pattern and light reflection style
  4. Transparency or opacity of the stone
  5. Surface texture (smooth / included / silky)

WHAT NOT TO DO:
  - Do NOT change the ring band or metal in any way
  - Do NOT add or remove prongs
  - Do NOT change the setting style
  - Do NOT blur, soften, or abstract the output
  - Do NOT add text, watermarks, or borders
  - Do NOT change the ring's viewing angle"""

    if custom.strip():
        prompt += f"\n\nADDITIONAL INSTRUCTIONS:\n{custom.strip()}"

    prompt += """

OUTPUT REQUIREMENTS (non-negotiable):
  • Resolution: 1024 × 1024 pixels, sharp focus throughout
  • Background: pure white (RGB 255, 255, 255), no shadows, no gradients
  • Lighting: soft diffused studio lighting, even highlights on metal
  • The ring must be fully in frame, centered, and in sharp focus
  • No motion blur, no depth-of-field blur, no softness anywhere
  • Render as a real photograph, not an illustration or 3D render"""

    return prompt

# ──────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────
def smart_resize(img: Image.Image, max_px: int = INPUT_MAX_PX) -> Image.Image:
    if max(img.size) > max_px:
        img.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)
    return img

def img_to_b64(img: Image.Image) -> str:
    import base64
    from io import BytesIO
    buffered = BytesIO()
    img_resized = smart_resize(img)
    img_resized.save(buffered, format="PNG", compress_level=PNG_COMPRESS_LEVEL)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def is_valid(img: Image.Image) -> tuple[bool, str]:
    if not img: return False, "Empty image"
    if img.size[0] < 512 or img.size[1] < 512: return False, "Low resolution"
    # Basic check for non-blank image
    stat = ImageStat.Stat(img.convert("L"))
    if stat.stddev[0] < 5: return False, "Possibly blank or flat"
    return True, "OK"

# ──────────────────────────────────────────────────────────────
#  IMAGE CAPTURE LOGIC
# ──────────────────────────────────────────────────────────────
def download_last_gemini_image(client, label, output_path, tab_id=None):
    print(f"  [{label}] Waiting for image generation...")
    # Poll for up to 100 seconds
    for i in range(20):
        time.sleep(5)
        try:
            snap = client.get_snapshot(filter="all", tab_id=tab_id)
            
            # Look for nodes that are likely the generated image
            # We look for role="image" or tag="img" with "AI generated" in their name
            img_nodes = [
                n for n in snap.get("nodes", []) 
                if (n.get("role") == "image" or n.get("tag") == "img") and "AI generated" in (n.get("name") or "")
            ]
            
            # Fallback to any images if no "AI generated" ones are found
            if not img_nodes:
                img_nodes = [
                    n for n in snap.get("nodes", []) 
                    if n.get("role") == "image" or n.get("tag") == "img"
                ]
            
            # Sign of completion: "Download" button appears near the image
            download_btn = client.find_node(snap, text_contains="Download")
            
            if img_nodes and download_btn:
                # Use the last (newest) image node which is usually the result
                target_ref = img_nodes[-1]["ref"]
                print(f"  [{label}] Found image node {target_ref}. Extracting URL and downloading...")
                
                js_get_src = """
                (() => {
                  const el = document.querySelector('img[alt*="AI generated"]');
                  if (el) return el.src;
                  const imgs = Array.from(document.querySelectorAll('img'));
                  for (const img of imgs) {
                    if (img.src && img.src.includes('googleusercontent.com') && !img.src.includes('ogw/') && !img.src.includes('ACg8oc')) {
                      return img.src;
                    }
                  }
                  return null;
                })()
                """
                eval_res = client.evaluate_js(tab_id, js_get_src)
                img_url = eval_res.get("result")
                if not img_url:
                    raise Exception("Failed to get image URL from DOM")
                
                if img_url.startswith("blob:"):
                    print(f"  [{label}] URL is blob: {img_url}. Converting img element to base64 via Canvas...")
                    js_canvas = """
                    (() => {
                      try {
                        let img = document.querySelector('img[alt*="AI generated"]');
                        if (!img) {
                          const imgs = Array.from(document.querySelectorAll('img'));
                          for (let idx = imgs.length - 1; idx >= 0; idx--) {
                            const i = imgs[idx];
                            if (i.naturalWidth > 200 && i.naturalHeight > 200 && !i.src.includes('ogw/')) {
                              img = i;
                              break;
                            }
                          }
                        }
                        if (!img) return "Error: Image element not found";
                        if (!img.complete || img.naturalWidth === 0) {
                          return "Error: Image not fully loaded in browser yet";
                        }
                        
                        const canvas = document.createElement('canvas');
                        canvas.width = img.naturalWidth;
                        canvas.height = img.naturalHeight;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0);
                        return canvas.toDataURL('image/png');
                      } catch (e) {
                        return "Error: Canvas conversion failed - " + e.message;
                      }
                    })()
                    """
                    eval_res = client.evaluate_js(tab_id, js_canvas)
                    val = eval_res.get("result")
                    if val and val.startswith("data:image/"):
                        try:
                            header, encoded = val.split(",", 1)
                            import base64
                            img_data = base64.b64decode(encoded)
                            with open(output_path, "wb") as f:
                                f.write(img_data)
                            print(f"  [{label}] High-quality download (from Blob via Canvas) saved to {output_path}")
                            return True
                        except Exception as parse_err:
                            print(f"  [{label}] Error parsing base64 image data from canvas: {parse_err}")
                    else:
                        print(f"  [{label}] Canvas download failed: {val}")
                else:
                    print(f"  [{label}] Downloading standard network image URL: {img_url}")
                    try:
                        r = requests.get(img_url, timeout=30)
                        r.raise_for_status()
                        with open(output_path, "wb") as f:
                            f.write(r.content)
                        print(f"  [{label}] High-quality download saved directly via requests to {output_path}")
                        return True
                    except Exception as download_err:
                        print(f"  [{label}] Requests download failed: {download_err}")
            
        except Exception as e:
            print(f"  [{label}] Polling error: {e}")
            
    return False

# ──────────────────────────────────────────────────────────────
#  CORE GENERATION TASK
# ──────────────────────────────────────────────────────────────
def generate_single(task: tuple, enable_validation: bool = True):
    model_name, stone_name, model_img, stone_img, variation, custom_prompt = task
    label  = f"{model_name}+{stone_name}_v{variation}"
    prompt = build_prompt(custom_prompt)
    
    for attempt in range(MAX_RETRIES + 1):
        tab_id = None
        try:
            print(f"  [{label}] Attempting generation via browser (Attempt {attempt + 1})...")
            # Navigate to Gemini in a new tab
            resp = client.navigate("https://gemini.google.com/app", new_tab=True)
            tab_id = resp.get("tabId")
            if not tab_id:
                raise Exception("Failed to open a new tab")
                
            print(f"  [{label}] Opened new tab: {tab_id}")
            time.sleep(5)
            
            # Focus tab to ensure actions are targetted correctly
            client.focus_tab(tab_id)
            
            # 1. Paste both images together using chunked base64 loading and simulated Clipboard paste events
            print(f"  [{label}] Preparing base64 images for pasting...")
            model_b64 = img_to_b64(model_img)
            stone_b64 = img_to_b64(stone_img)
            
            print(f"  [{label}] Loading base64 images in chunks to bypass payload size limits...")
            def set_chunked_var(var_name, data):
                client.evaluate_js(tab_id, f"window.{var_name} = '';")
                chunk_size = 200000
                for idx in range(0, len(data), chunk_size):
                    chunk = data[idx : idx + chunk_size]
                    client.evaluate_js(tab_id, f"window.{var_name} += {json.dumps(chunk)};")
            
            set_chunked_var("model_b64_data", model_b64)
            set_chunked_var("stone_b64_data", stone_b64)
            
            print(f"  [{label}] Dispatching paste events for Ring Model and Stone Reference...")
            js_paste = """
            (async () => {
              try {
                const el = document.querySelector('div[contenteditable="true"]');
                if (!el) return "Error: Contenteditable not found";
                el.focus();
                
                const b64s = [window.model_b64_data, window.stone_b64_data];
                
                for (let i = 0; i < b64s.length; i++) {
                  if (!b64s[i]) return "Error: Base64 data for image " + i + " is empty";
                  const res = await fetch("data:image/png;base64," + b64s[i]);
                  const blob = await res.blob();
                  const file = new File([blob], `file_${i}.png`, { type: "image/png" });
                  
                  const dataTransfer = new DataTransfer();
                  dataTransfer.items.add(file);
                  
                  const pasteEvent = new ClipboardEvent('paste', {
                    bubbles: true,
                    cancelable: true,
                    clipboardData: dataTransfer
                  });
                  
                  el.dispatchEvent(pasteEvent);
                  // Wait a short delay between pastes to let Gemini register each attachment
                  await new Promise(r => setTimeout(r, 1500));
                }
                
                // Clean up window variables
                delete window.model_b64_data;
                delete window.stone_b64_data;
                
                return "Success";
              } catch (e) {
                return "Error: " + e.message;
              }
            })()
            """
            paste_res = client.evaluate_js(tab_id, js_paste)
            print(f"  [{label}] Paste response: {paste_res}")
            
            # Poll for the thumbnails in the input container to verify they were uploaded successfully
            uploaded_ok = False
            for poll_sec in range(10):
                check_thumbnails = """
                (() => {
                  const imgs = document.querySelectorAll('div[class*="attachment"] img, div[class*="thumbnail"] img, mat-chip img, .chip img');
                  return imgs.length;
                })()
                """
                count_res = client.evaluate_js(tab_id, check_thumbnails)
                count = count_res.get("result", 0)
                if isinstance(count, int) and count >= 2:
                    print(f"  [{label}] Confirmed: {count} attached thumbnails found in input container.")
                    uploaded_ok = True
                    break
                time.sleep(1)
            
            if not uploaded_ok:
                print(f"  [{label}] Warning: Could not confirm 2 attached thumbnails in the input container, proceeding anyway.")
            
            print(f"  [{label}] Setting prompt via JS...")
            escaped_prompt = json.dumps(prompt)
            js_expr = f"""
            (() => {{
              const el = document.querySelector('div[contenteditable="true"]');
              if (!el) return "Element not found";
              el.focus();
              el.innerText = {escaped_prompt};
              el.dispatchEvent(new Event('input', {{ bubbles: true }}));
              el.dispatchEvent(new Event('change', {{ bubbles: true }}));
              return "Success";
            }})()
            """
            client.evaluate_js(tab_id, js_expr)
            time.sleep(2)
            
            # Focus tab before action to be safe
            client.focus_tab(tab_id)
            
            # 4. Wait for Send Button to be enabled using live JS evaluations
            is_disabled = True
            for wait_sec in range(10): # Wait up to 10 seconds
                eval_btn = client.evaluate_js(tab_id, "(() => { const btn = document.querySelector('button[aria-label=\"Send message\"]'); return btn ? btn.disabled : true; })()")
                if eval_btn.get("result") is False:
                    is_disabled = False
                    break
                time.sleep(1)
            
            if not is_disabled:
                # Try clicking via JS first because it is 100% reliable and bypasses bridge-side snapshot element state/cache issues
                print(f"  [{label}] Clicking Send button via JS...")
                js_click_res = client.evaluate_js(tab_id, "(() => { const btn = document.querySelector('button[aria-label=\"Send message\"]'); if (btn) { btn.click(); return 'clicked'; } return 'not_found'; })()")
                if js_click_res.get("result") == "clicked":
                    print(f"  [{label}] Clicked Send button successfully via JS")
                else:
                    # Fallback to snapshot + perform_action if JS click says not found
                    print(f"  [{label}] Send button not found via JS. Trying snapshot...")
                    snap = client.get_snapshot(tab_id=tab_id)
                    send_btn = client.find_node(snap, name="Send message") or client.find_node(snap, role="button", text_contains="Send")
                    if send_btn:
                        print(f"  [{label}] Clicking Send button {send_btn['ref']} via perform_action...")
                        client.perform_action("click", ref=send_btn["ref"])
                    else:
                        raise Exception("Send button not found via JS or snapshot")
            else:
                raise Exception("Send button remained disabled after setting text")
            
            # Path for the real screenshot/download
            fn = f"{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            output_path = os.path.abspath(os.path.join(OUTPUT_DIR, fn))
            
            # Capture
            success = download_last_gemini_image(client, label, output_path, tab_id=tab_id)
            
            if success:
                print(f"  ✅ [{label}] Result captured: {output_path}")
                try:
                    client.close_tab(tab_id)
                    tab_id = None
                except Exception as close_err:
                    print(f"  [{label}] Error closing tab: {close_err}")
                return output_path, label, True, True, "OK"
            
            print(f"  [{label}] Generation failed or timed out")
            
        except Exception as e:
            print(f"  [{label}] Error: {e}")
            time.sleep(5)
        finally:
            if tab_id:
                try:
                    print(f"  [{label}] Cleaning up tab: {tab_id}")
                    client.close_tab(tab_id)
                except Exception as close_err:
                    print(f"  [{label}] Error cleaning up tab: {close_err}")
                    
    return None, label, False, False, "All attempts failed"


# ──────────────────────────────────────────────────────────────
#  UI HELPERS & IMAGE UTILITIES
# ──────────────────────────────────────────────────────────────
def load_image_from_url(url: str) -> Image.Image:
    url = url.strip()
    if not url.startswith("http"):
        raise ValueError("Invalid URL")
    r = requests.get(url,
                     headers={"User-Agent": "Mozilla/5.0", "Accept": "image/*"},
                     timeout=30)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")

def load_images_from_files(files) -> tuple[list, list]:
    images, names = [], []
    if not files:
        return images, names
    for f in files:
        path = f if isinstance(f, str) else f.name
        if os.path.splitext(path)[1].lower() not in (".jpg",".jpeg",".png",".webp",".bmp"):
            continue
        try:
            images.append(Image.open(path).convert("RGB"))
            names.append(os.path.splitext(os.path.basename(path))[0])
        except Exception as e:
            print(f"Skipping {path}: {e}")
    return images, names

def parse_urls(text: str) -> list[str]:
    if not text:
        return []
    return [u.strip() for u in text.split("\n") if u.strip()]

def toggle_model(src):
    return (gr.update(visible=src == "Upload Folder"),
            gr.update(visible=src == "Image URL(s)"))

def toggle_stone(src):
    return (gr.update(visible=src == "Upload Folder"),
            gr.update(visible=src == "Image URL(s)"))

# ──────────────────────────────────────────────────────────────
#  BATCH ORCHESTRATOR
# ──────────────────────────────────────────────────────────────
def generate_rings_batch_pinchtab(
    model_source, model_folder, model_urls_text,
    stone_source, stone_folder, stone_urls_text,
    custom_prompt, num_variations,
    enable_validation, max_workers,
    progress=gr.Progress()
):
    progress(0, desc="Preparing Pinchtab session…")
    
    # Load ring models
    ring_imgs, ring_names = [], []
    if model_source == "Upload Folder":
        if not model_folder:
            return "❌ Upload ring model images", [], None, None
        ring_imgs, ring_names = load_images_from_files(model_folder)
    else:
        for i, url in enumerate(parse_urls(model_urls_text)):
            try:
                ring_imgs.append(load_image_from_url(url))
                ring_names.append(f"model_{i+1}")
            except Exception as e:
                print(f"Model URL {i+1} failed: {e}")

    if not ring_imgs:
        return "❌ No ring models loaded", [], None, None

    # Load stones
    stone_imgs, stone_names = [], []
    if stone_source == "Upload Folder":
        if not stone_folder:
            return "❌ Upload stone images", [], ring_imgs[0], None
        stone_imgs, stone_names = load_images_from_files(stone_folder)
    else:
        for i, url in enumerate(parse_urls(stone_urls_text)):
            try:
                stone_imgs.append(load_image_from_url(url))
                stone_names.append(f"stone_{i+1}")
            except Exception as e:
                print(f"Stone URL {i+1} failed: {e}")

    if not stone_imgs:
        return "❌ No stones loaded", [], ring_imgs[0], None

    # All (ring × stone × variation) combos
    tasks = [
        (rn, sn, ri, si, v, custom_prompt)
        for ri, rn in zip(ring_imgs, ring_names)
        for si, sn in zip(stone_imgs, stone_names)
        for v in range(1, num_variations + 1)
    ]

    total = len(tasks)
    workers = int(max_workers)
    print(f"\n🚀 {total} tasks via Pinchtab")
    
    progress(0.05, desc=f"Generating {total} images...")
    
    success = failed = 0
    paths = []
    t0 = time.time()
    
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(generate_single, task, enable_validation): task for task in tasks}
        
        for future in as_completed(futures):
            task = futures[future]
            model_name, stone_name, _, _, variation, _ = task
            try:
                path, label, ok, quality_ok, reason = future.result()
            except Exception as exc:
                ok, quality_ok = False, False
                label = f"{model_name}+{stone_name}_v{variation}"
                path = None
                reason = f"Worker exception: {exc}"
            
            if ok:
                paths.append(path)
                success += 1
            else:
                failed += 1
                print(f"FAILED {label}: {reason}")
            
            done = success + failed
            progress(
                0.05 + 0.95 * done / total,
                desc=f"✅ {success} saved  ❌ {failed} failed ({done}/{total})"
            )
            
    elapsed = time.time() - t0
    summary = f"Batch complete in {elapsed:.1f}s. {success} successes, {failed} failures."
    return summary, paths, ring_imgs[0], stone_imgs[0]

# ──────────────────────────────────────────────────────────────
#  GRADIO UI
# ──────────────────────────────────────────────────────────────
def create_gui():
    with gr.Blocks(title="Pinchtab Ring Automation") as demo:
        gr.Markdown("# 💍 Pinchtab Gemini Image Generator")
        gr.Markdown("Uses Pinchtab to control your browser, upload 2 images, and generate jewelry modifications.")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 🔷 Ring Models")
                model_source = gr.Radio(["Upload Folder", "Image URL(s)"],
                                        value="Upload Folder", label="Source")
                model_folder = gr.File(label="Upload Ring Images",
                                       file_count="multiple",
                                       file_types=["image"], visible=True)
                model_urls   = gr.Textbox(label="URLs (one per line)", lines=4,
                                          placeholder="https://…/ring1.jpg",
                                          visible=False)
                model_source.change(toggle_model, model_source,
                                    [model_folder, model_urls])

                gr.Markdown("---")

                gr.Markdown("### 💎 Stone References")
                stone_source = gr.Radio(["Upload Folder", "Image URL(s)"],
                                        value="Upload Folder", label="Source")
                stone_folder = gr.File(label="Upload Stone Images",
                                       file_count="multiple",
                                       file_types=["image"], visible=True)
                stone_urls   = gr.Textbox(label="URLs (one per line)", lines=4,
                                          placeholder="https://…/stone1.jpg",
                                          visible=False)
                stone_source.change(toggle_stone, stone_source,
                                    [stone_folder, stone_urls])

                gr.Markdown("---")

                gr.Markdown("### ⚙️ Settings")
                custom_prompt = gr.Textbox(
                    label="Additional Instructions (optional)", lines=3,
                    placeholder="e.g. 'Make the metal look like brushed platinum'")
                num_variations = gr.Slider(
                    1, 3, value=1, step=1,
                    label="Variations per Combination")
                max_workers_slider = gr.Slider(
                    1, 3, value=1, step=1,
                    label="Parallel Workers (1 recommended)")
                enable_validation = gr.Checkbox(
                    label="Quality validation (retry blurry/blank images)",
                    value=True)
                generate_btn = gr.Button(
                    "🎨 Generate All", variant="primary", size="lg")

            with gr.Column(scale=2):
                output_text = gr.Textbox(label="Status")
                
                gr.Markdown("### 🖼️ Input Previews")
                with gr.Row():
                    model_preview = gr.Image(label="Ring Model (full res)",
                                             type="pil")
                    stone_preview = gr.Image(label="Stone Reference (full res)",
                                             type="pil")
                                             
                gallery = gr.Gallery(label="Generated Images")
                
        generate_btn.click(
            generate_rings_batch_pinchtab,
            inputs=[
                model_source, model_folder, model_urls,
                stone_source, stone_folder, stone_urls,
                custom_prompt, num_variations,
                enable_validation, max_workers_slider,
            ],
            outputs=[output_text, gallery, model_preview, stone_preview]
        )
        
    return demo

if __name__ == "__main__":
    # Try to find an open port starting from 7861
    import socket
    def get_available_port(start_port, max_attempts=10):
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', port)) != 0:
                    return port
        return None

    port = get_available_port(7861)
    if port:
        print(f"🚀 Starting Gradio UI on port {port}")
        create_gui().launch(server_name="127.0.0.1", server_port=port, share=True)
    else:
        print("❌ Error: Could not find an available port in range 7861-7870")
