import asyncio 
from random import randint, choice
from PIL import Image 
import os
from time import sleep
import requests
from pathlib import Path


# ✅ FIX FILE PATHS - ONLY ADDITION TO YOUR CODE
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "Data"
FRONTEND_FILES_DIR = PROJECT_ROOT / "Frontend" / "Files"


# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
FRONTEND_FILES_DIR.mkdir(parents=True, exist_ok=True)


# --------- helpers to classify prompts and (optionally) fetch spec hints ---------
def _classify_prompt(p: str):
    lp = p.lower().strip()
    human_terms = {
        "human","person","people","man","woman","male","female","boy","girl",
        "portrait","headshot","model","actor","actress","couple","family",
        "kid","child","old man","old woman","young man","young woman","selfie"
    }
    product_terms = {
        "iphone","ipad","macbook","imac","galaxy","pixel","oneplus","xiaomi",
        "sony","playstation","xbox","tesla","bmw","audi","mercedes","honda",
        "toyota","suzuki","kia","hyundai","nikon","canon","dji","gopro","rog",
        "lenovo","acer","asus","msi","laptop","phone","camera","watch","earbuds",
        "headphones","tablet","monitor","tv","router","speaker","controller"
    }
    wants_humans = any(t in lp for t in human_terms)
    is_product   = any(t in lp for t in product_terms)
    return wants_humans, is_product  # keeps external behavior intact


def _spec_hint_if_model(p: str) -> str:
    import re
    lp = p.lower()
    model_hints = {"iphone","galaxy","pixel","oneplus","tesla","bmw","audi","mercedes","nikon","canon","sony"}
    generic_skip = {"cat","dog","animal","car","vehicle","boy","girl","man","woman","person","people","human"}
    if not any(h in lp for h in model_hints) or any(g in lp for g in generic_skip):
        return ""
    BRAVE_KEY = os.getenv("BraveAPIKey", "")
    if not BRAVE_KEY:
        return ""
    try:
        headers = {"X-Subscription-Token": BRAVE_KEY}
        params  = {"q": p, "count": 5, "country": "in", "search_lang": "en"}
        r = requests.get("https://api.search.brave.com/res/v1/web/search", headers=headers, params=params, timeout=6)
        if not r.ok:
            return ""
        data = r.json()
        items = data.get("web", {}).get("results", [])
        def score(it):
            u = (it.get("url","") or "").lower()
            good = any(k in u for k in ["apple.com","samsung.com","google.com","oneplus.com","tesla.com","bmw.com","audi.com","mercedes","nikon","canon","sony.com"])
            return (10 if good else 0) + len(it.get("title",""))
        items.sort(key=score, reverse=True)
        top = items[0] if items else None
        if not top:
            return ""
        title = top.get("title","")
        snip  = top.get("description","")
        cut = re.sub(r"[^a-zA-Z0-9 ,\-:]", " ", f"{title}. {snip}")[:180]
        return cut.strip()
    except Exception:
        return ""


# UNCHANGED
def open_images(prompt):
    folder_path = str(DATA_DIR)
    prompt = prompt.replace(" ", "_")
    Files = [f"{prompt}{i}.jpg" for i in range(1, 3)]  # Only open first 2 images
    for jpg_file in Files:
        image_path = os.path.join(folder_path, jpg_file)
        try:
            img = Image.open(image_path)
            print(f"Opening image: {image_path}")
            img.show()
            sleep(1)
        except IOError:
            print(f"Unable to open {image_path}")


# Enhanced Pollinations query function (Unlimited Free)
async def query(payload):
    try:
        print(f" Generating with Enhanced Pollinations: {payload['inputs'][:50]}...")


        # Per‑image randomization so all 4 are distinct
        seed = randint(0, 1_000_000)  # unique per call
        product_angles = ["front angle", "left three-quarter", "right three-quarter", "top-down flat-lay"]
        portrait_angles = ["head-and-shoulders", "three-quarter portrait", "profile view", "environmental portrait"]
        lightings = ["soft studio lighting", "backlit rim light", "natural window light", "dramatic split lighting"]


        subject_full = payload['inputs']
        subject = subject_full.split(",", 1)[0].strip()
        wants_humans, is_product = _classify_prompt(subject)
        spec_hint = _spec_hint_if_model(subject) if is_product and not wants_humans else ""


        if wants_humans:
            refined = (
                f"photorealistic portrait photo of {subject}, {choice(portrait_angles)}, "
                f"{choice(lightings)}, natural skin tones, eyes in sharp focus, "
                f"high resolution, no text, no watermark, variant v{seed}"
            )
        elif is_product:
            extra = f" ({spec_hint})" if spec_hint else ""
            refined = (
                f"photorealistic studio product photo of {subject}{extra}, {choice(product_angles)}, "
                f"plain white background, {choice(lightings)}, high resolution, sharp details, "
                f"no people, no hands, no text, no watermark, variant v{seed}"
            )
        else:
            refined = (
                f"photorealistic image of {subject}, clean composition, {choice(lightings)}, "
                f"high resolution, no text, no watermark, variant v{seed}"
            )


        encoded_prompt = refined.replace(' ', '%20').replace(',', '%2C')


        # Multiple endpoints; also add seed as a query param to break any caching
        urls = [
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&enhance=true&style=photorealistic&seed={seed}",
            f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=1024&nologo=1&quality=high&realistic=true&seed={seed}",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=turbo&nologo=true&photorealistic=true&seed={seed}"
        ]


        for url in urls:
            try:
                response = await asyncio.to_thread(requests.get, url, timeout=60)
                if response.status_code == 200 and len(response.content) > 5000:
                    print(f" Enhanced Pollinations image generated: {len(response.content)} bytes")
                    return response.content
            except:
                continue


        print(" Enhanced Pollinations failed")
        return b""


    except Exception as e:
        print(f" Generation error: {e}")
        return b""


# UNCHANGED
async def generate_images(prompt: str):
    tasks = []
    for _ in range(2):  # Two requests
        payload = {
            "inputs": f"{prompt}, quality=4K, sharpness=maximum, Ultra High details, high resolution, seed = {randint(0, 1000000)}",
        }
        task = asyncio.create_task(query(payload))
        tasks.append(task)
        await asyncio.sleep(5)  # 5-second delay between requests
    image_bytes_list = await asyncio.gather(*tasks)
    for i, image_bytes in enumerate(image_bytes_list):
        if image_bytes and (image_bytes.startswith(b'\x89PNG') or image_bytes.startswith(b'\xff\xd8\xff')):
            image_file_path = DATA_DIR / f"{prompt.replace(' ', '_')}{i+1}.jpg"
            with open(image_file_path, "wb") as f:
                f.write(image_bytes)
                print(f" Saved: {image_file_path}")
        else:
            print(f" Invalid image data for image {i+1}")


# UNCHANGED
def GenerateImages(prompt: str):
    asyncio.run(generate_images(prompt))
    open_images(prompt)


# UNCHANGED
while True:
    try:
        image_generation_data_file = FRONTEND_FILES_DIR / "ImageGeneration.data"
        with open(image_generation_data_file, "r") as f:
            Data: str = f.read().strip()
        Prompt, Status = Data.split(",")
        if Status.strip() == "True":
            print("Generating Images with Enhanced Pollinations (Unlimited Free)...")
            ImageStatus = GenerateImages(prompt=Prompt.strip())
            with open(image_generation_data_file, "w") as f:
                f.write("False,False")
            break
        else:
            sleep(1)
    except FileNotFoundError:
        print(" ImageGeneration.data file not found! Creating one...")
        FRONTEND_FILES_DIR.mkdir(parents=True, exist_ok=True)
        with open(image_generation_data_file, "w") as f:
            f.write("False,False")
        sleep(1)
    except ValueError as e:
        print(f" File format error: {e}")
        print(" File should contain: 'prompt,True' or 'prompt,False'")
        break
    except Exception as e:
        print(f" Unexpected error: {e}")
        break
