import asyncio
import os
import time
from playwright.async_api import async_playwright
from PIL import Image
import io
import base64
import requests
from dotenv import load_dotenv

class LinkedInCaptchaSolver:
    def __init__(self, email, password):
        print("Initializing LinkedIn CAPTCHA Solver...")
        self.email = email
        self.password = password
        self.page = None
        self.browser = None
        self.context = None
        self.login_count = 0

    async def init_browser(self):
        print("Starting browser initialization...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        print("Browser launched successfully")
        
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        print("Browser context created")
        
        self.page = await self.context.new_page()
        self.page.set_default_timeout(30000)
        self.page.set_default_navigation_timeout(30000)
        print("Page created with timeouts set")

    async def logout(self):
        print("\n=== Starting Logout Process ===")
        try:
            # Click the Me dropdown
            print("Looking for Me menu button...")
            me_button = await self.page.wait_for_selector('button[aria-label="Open menu"]')
            if me_button:
                await me_button.click()
                await asyncio.sleep(1)

            # Click Sign Out
            print("Looking for Sign Out button...")
            sign_out_button = await self.page.wait_for_selector('a[href*="logout"]')
            if sign_out_button:
                await sign_out_button.click()
                await asyncio.sleep(2)
                print("Successfully logged out")
                return True
            else:
                print("Could not find Sign Out button")
                return False
        except Exception as e:
            print(f"Logout error: {str(e)}")
            return False

    async def check_for_security_verification(self):
        """Check if we're on the security verification page and handle it"""
        try:
            print("Checking for security verification...")
            
            # Clear any existing cache at the very beginning
            print("🔄 Clearing any existing CAPTCHA cache at start...")
            await self.clear_captcha_cache()
            await asyncio.sleep(1)
            
            # First check if we're on a challenge URL
            current_url = self.page.url
            if "checkpoint/challenge" in current_url:
                print(f"Detected challenge URL: {current_url}")
                
                # Wait longer for page load
                await asyncio.sleep(3)
                
                # Take debug screenshot
                # await self.page.screenshot(path=f"debug_challenge_page_{time.strftime('%H-%M-%S')}.png", full_page=True)
                
                # Get all frames
                frames = self.page.frames
                print(f"\nFound {len(frames)} total frames on page")
                
                # Find all Arkoselabs frames
                arkose_frames = [f for f in frames if 'arkoselabs.com' in f.url]
                print(f"Found {len(arkose_frames)} Arkoselabs frames")
                
                for i, frame in enumerate(arkose_frames):
                    print(f"Arkoselabs frame {i}: {frame.url}")
                
                # Look for Start Puzzle button in any Arkoselabs frame
                start_clicked = False
                for frame in arkose_frames:
                    try:
                        # Look for start button
                        start_button = await frame.wait_for_selector('button:has-text("Start Puzzle")', timeout=3000)
                        if start_button:
                            print(f"Found Start Puzzle button in frame: {frame.url}")
                            await start_button.click()
                            print("Clicked Start Puzzle button")
                            start_clicked = True
                            break
                    except:
                        continue
                
                if not start_clicked:
                    print("No Start Puzzle button found - CAPTCHA should be already visible after retry")
                    # Continue with the existing CAPTCHA solving logic below
                
                # After clicking Start Puzzle, wait longer and look more comprehensively
                print("Waiting for puzzle images to load...")
                await asyncio.sleep(10)  # Even longer wait

                # Take screenshot after clicking start
                # await self.page.screenshot(path="debug_after_start_puzzle.png", full_page=True)

                # Function to recursively check frames and nested frames
                async def check_frame_for_captcha(frame, frame_path=""):
                    try:
                        print(f"\n{frame_path}Checking frame: {frame.url}")
                        
                        # Try very specific CAPTCHA selectors first
                        captcha_selectors = [
                            'div[role="button"][tabindex]',  # CAPTCHA tiles are usually divs with button role and tabindex
                            'div[onclick][style*="background"]',  # Clickable divs with background images
                            'button[aria-label*="image"]',  # Image buttons with aria labels
                            'div[class*="tile"]',  # Tile classes
                            'div[class*="image"]',  # Image classes
                            'div[class*="option"]',  # Option classes
                            'div[data-index]',  # Elements with data-index (common in CAPTCHAs)
                            'canvas',  # Canvas elements
                        ]
                        
                        for selector in captcha_selectors:
                            try:
                                elements = await frame.query_selector_all(selector)
                                if len(elements) == 6:  # Perfect match for 6 CAPTCHA images
                                    print(f"  {frame_path}✅ Found exactly 6 CAPTCHA elements with '{selector}' - Perfect match!")
                                    # Verify they're actually clickable/visible
                                    visible_clickable = []
                                    for elem in elements:
                                        try:
                                            is_visible = await elem.is_visible()
                                            if is_visible:
                                                visible_clickable.append(elem)
                                        except:
                                            continue
                                    
                                    if len(visible_clickable) == 6:
                                        return frame, visible_clickable, selector
                                elif len(elements) >= 4 and len(elements) <= 9:
                                    print(f"  {frame_path}🔍 Found {len(elements)} elements with '{selector}' - Possible CAPTCHA")
                                    # Check if they're visible and potentially the right ones
                                    visible_elements = []
                                    for elem in elements:
                                        try:
                                            is_visible = await elem.is_visible()
                                            # Additional check: see if element has image-like properties
                                            has_bg_image = await elem.evaluate('el => getComputedStyle(el).backgroundImage !== "none"')
                                            has_click_handler = await elem.evaluate('el => el.onclick !== null || el.getAttribute("onclick") !== null')
                                            
                                            if is_visible and (has_bg_image or has_click_handler):
                                                visible_elements.append(elem)
                                        except:
                                            continue
                                    
                                    if len(visible_elements) >= 6:
                                        print(f"  {frame_path}✅ Found {len(visible_elements)} GOOD CAPTCHA candidates with '{selector}'!")
                                        return frame, visible_elements[:6], selector  # Take first 6
                                        
                            except Exception as e:
                                continue
                        
                        # Fallback: try generic selectors but with better filtering
                        all_selectors = [
                            'div',  # All divs
                            'button',  # All buttons  
                            'img',  # All images
                            '*[onclick]',  # Anything clickable
                            '*[role="button"]',  # Anything with button role
                        ]
                        
                        for selector in all_selectors:
                            try:
                                elements = await frame.query_selector_all(selector)
                                if len(elements) >= 6:
                                    print(f"  {frame_path}Found {len(elements)} elements with '{selector}' - checking properties...")
                                    
                                    # Filter for actual CAPTCHA elements
                                    captcha_candidates = []
                                    for i, elem in enumerate(elements):
                                        try:
                                            is_visible = await elem.is_visible()
                                            has_bg_image = await elem.evaluate('el => getComputedStyle(el).backgroundImage !== "none"')
                                            has_click_handler = await elem.evaluate('el => el.onclick !== null || el.getAttribute("onclick") !== null')
                                            tag_name = await elem.evaluate('el => el.tagName')
                                            class_name = await elem.evaluate('el => el.className')
                                            
                                            # Skip instruction/container elements
                                            if 'instruction' in class_name.lower() or 'container' in class_name.lower():
                                                continue
                                            
                                            # Look for elements that could be CAPTCHA tiles
                                            if is_visible and (has_bg_image or has_click_handler or tag_name.lower() == 'img'):
                                                captcha_candidates.append(elem)
                                                print(f"    Candidate {len(captcha_candidates)}: {tag_name} with class '{class_name}', bg={has_bg_image}, click={has_click_handler}")
                                                
                                                if len(captcha_candidates) == 6:  # Stop when we have 6 good candidates
                                                    break
                                                    
                                        except:
                                            continue
                                    
                                    if len(captcha_candidates) >= 6:
                                        print(f"  {frame_path}✅ Found {len(captcha_candidates)} FILTERED CAPTCHA candidates!")
                                        return frame, captcha_candidates[:6], selector
                                        
                            except Exception as e:
                                continue
                        
                        # Check nested frames
                        try:
                            child_frames = frame.child_frames
                            if child_frames:
                                print(f"  {frame_path}Found {len(child_frames)} child frames")
                                for i, child_frame in enumerate(child_frames):
                                    result = await check_frame_for_captcha(child_frame, f"{frame_path}  Child {i}: ")
                                    if result:
                                        return result
                        except Exception as e:
                            print(f"  {frame_path}Error checking child frames: {e}")

                        return None
                        
                    except Exception as e:
                        print(f"{frame_path}Error checking frame: {e}")
                        return None

                # Check all frames and nested frames
                frames = self.page.frames
                arkose_frames = [f for f in frames if 'arkoselabs.com' in f.url]
                print(f"\nScanning {len(arkose_frames)} Arkoselabs frames and their nested frames...")

                best_result = None

                for i, frame in enumerate(arkose_frames):
                    result = await check_frame_for_captcha(frame, f"Frame {i}: ")
                    if result:
                        best_result = result
                        break

                if not best_result:
                    print("\nNo CAPTCHA found in Arkoselabs frames, checking ALL frames...")
                    for i, frame in enumerate(frames):
                        result = await check_frame_for_captcha(frame, f"All Frame {i}: ")
                        if result:
                            best_result = result
                            break

                if not best_result:
                    print("No CAPTCHA images found in any frame")
                    return False

                best_frame, clickable_elements, best_selector = best_result
                print(f"\n✅ Using frame with {len(clickable_elements)} visible elements (selector: {best_selector})")
                print(f"Frame URL: {best_frame.url}")

                # Take screenshot of the best frame
                # try:
                #     await best_frame.page.screenshot(path="debug_best_frame.png", full_page=True)
                # except:
                #     pass
                
                # Clear any existing cache BEFORE taking screenshot
                print("🔄 Clearing any existing CAPTCHA cache before starting...")
                await self.clear_captcha_cache()
                await asyncio.sleep(1)
                
                # Send screenshot to solving server
                try:
                    # Try to find a container element first
                    container_selectors = ['.challenge-container', '[class*="challenge"]', '[class*="puzzle"]', 'body']
                    screenshot_taken = False
                    screenshot = None
                    
                    for container_sel in container_selectors:
                        try:
                            container = await best_frame.wait_for_selector(container_sel, timeout=2000)
                            if container:
                                screenshot = await container.screenshot(type='png')
                                print(f"✅ Took screenshot using container: {container_sel}")
                                screenshot_taken = True
                                break
                        except:
                            continue
                    
                    if not screenshot_taken:
                        # Fallback to full page screenshot
                        screenshot = await best_frame.page.screenshot(full_page=True, type='png')
                        print("✅ Took full page screenshot as fallback")
                    
                    # Send to solving server (without clearing again since we already did)
                    sent = await self.send_captcha_to_server_direct(screenshot)
                    if not sent:
                        print("Failed to send to solving server")
                        return False
                    
                    # Wait for human answer
                    print("Waiting for human solution...")
                    answer = await self.poll_for_answer()
                    if answer is None:
                        print("No answer received")
                        return False
                    
                    print(f"Received answer: {answer}")
                    
                    # Use the clickable elements we already found
                    print(f"Found {len(clickable_elements)} total clickable elements")

                    # Try to filter to get only the CAPTCHA images (usually 6)
                    if len(clickable_elements) > 6:
                        print(f"Filtering {len(clickable_elements)} elements to find the 6 CAPTCHA images...")
                        
                        # Debug: Show properties of all elements
                        for i, elem in enumerate(clickable_elements):
                            try:
                                tag_name = await elem.evaluate('el => el.tagName')
                                has_background = await elem.evaluate('el => getComputedStyle(el).backgroundImage !== "none"')
                                has_onclick = await elem.evaluate('el => el.onclick !== null')
                                is_visible = await elem.is_visible()
                                print(f"  Element {i}: {tag_name}, background={has_background}, onclick={has_onclick}, visible={is_visible}")
                            except Exception as e:
                                print(f"  Element {i}: Error getting properties - {e}")
                        
                        # Try to filter by common CAPTCHA characteristics
                        captcha_candidates = []
                        for elem in clickable_elements:
                            try:
                                # Check if element has image-like properties
                                tag_name = await elem.evaluate('el => el.tagName')
                                has_background = await elem.evaluate('el => getComputedStyle(el).backgroundImage !== "none"')
                                has_onclick = await elem.evaluate('el => el.onclick !== null')
                                
                                if has_background or has_onclick or tag_name.lower() == 'img':
                                    captcha_candidates.append(elem)
                            except:
                                continue
                        
                        if len(captcha_candidates) >= 6:
                            clickable_elements = captcha_candidates[:6]  # Take first 6
                            print(f"Filtered to {len(clickable_elements)} CAPTCHA image candidates")
                        else:
                            print(f"Could not filter properly, using first 6 of {len(clickable_elements)} elements")
                            clickable_elements = clickable_elements[:6]

                    print(f"Final selection: Using {len(clickable_elements)} elements for CAPTCHA")

                    if len(clickable_elements) > answer:
                        print(f"Clicking CAPTCHA element at index {answer}")
                        
                        # Debug: Show what we're about to click
                        try:
                            elem_to_click = clickable_elements[answer]
                            tag_name = await elem_to_click.evaluate('el => el.tagName')
                            class_name = await elem_to_click.evaluate('el => el.className')
                            print(f"About to click: {tag_name} with class '{class_name}'")
                        except:
                            print("Could not get element details")
                        
                        await clickable_elements[answer].click()
                        print("Clicked solution element")
                        
                        # Wait longer to see if anything changes
                        await asyncio.sleep(10)  # Increased wait time
                        
                        # Take final screenshot
                        # await self.page.screenshot(path="debug_after_click.png", full_page=True)
                        
                        # Check if CAPTCHA failed and needs retry
                        print("Checking for CAPTCHA failure and retry options...")
                        captcha_failed = False
                        try_again_button = None
                        
                        # Check main page for error message
                        try:
                            error_message = await self.page.wait_for_selector('text="Whoops! That\'s not quite right."', timeout=2000)
                            if error_message:
                                captcha_failed = True
                                print("❌ CAPTCHA failed! (Main page)")
                        except:
                            pass
                        
                        # Check Arkoselabs frames for error message
                        if not captcha_failed:
                            try:
                                frames = self.page.frames
                                arkose_frames = [f for f in frames if 'arkoselabs.com' in f.url]
                                for frame in arkose_frames:
                                    try:
                                        error_message = await frame.wait_for_selector('text="Whoops! That\'s not quite right."', timeout=2000)
                                        if error_message:
                                            captcha_failed = True
                                            print("❌ CAPTCHA failed! (Arkoselabs frame)")
                                            break
                                    except:
                                        continue
                            except:
                                pass
                        
                        if captcha_failed:
                            print("❌ CAPTCHA failed! Looking for Try again button...")
                            try:
                                # Look for "Try again" button in main page
                                try_again_button = await self.page.wait_for_selector('button:has-text("Try again")', timeout=3000)
                                if try_again_button:
                                    print("🔄 Found Try again button in main page, clicking to retry...")
                                    await try_again_button.click()
                                    await asyncio.sleep(3)  # Wait for new CAPTCHA to load
                                    print("🔄 Retrying CAPTCHA...")
                                    return await self.check_for_security_verification()  # Recursive call
                            except:
                                pass
                            
                            # Look for "Try again" button in Arkoselabs frames
                            if not try_again_button:
                                try:
                                    frames = self.page.frames
                                    arkose_frames = [f for f in frames if 'arkoselabs.com' in f.url]
                                    for frame in arkose_frames:
                                        try:
                                            try_again_button = await frame.wait_for_selector('button:has-text("Try again")', timeout=3000)
                                            if try_again_button:
                                                print("🔄 Found Try again button in Arkoselabs frame, clicking to retry...")
                                                await try_again_button.click()
                                                await asyncio.sleep(3)  # Wait for new CAPTCHA to load
                                                print("🔄 Retrying CAPTCHA...")
                                                return await self.check_for_security_verification()  # Recursive call
                                        except:
                                            continue
                                except Exception as e:
                                    print(f"❌ Error looking for Try again button in frames: {e}")
                            
                            if not try_again_button:
                                print("❌ Try again button not found anywhere")
                        else:
                            print("No CAPTCHA failure detected")
                        
                        # Check if there's another CAPTCHA round
                        print("Checking for additional CAPTCHA rounds...")
                        try:
                            # Look for another Start Puzzle button or new challenge
                            next_captcha = await self.page.wait_for_selector('button:has-text("Start Puzzle")', timeout=3000)
                            if next_captcha:
                                print("🔄 Another CAPTCHA round detected! Solving...")
                                return await self.check_for_security_verification()  # Recursive call
                        except:
                            print("No additional CAPTCHA detected")
                        
                        # Check final URL and success indicators
                        final_url = self.page.url
                        print(f"Final URL: {final_url}")
                        
                        # More comprehensive success check
                        if 'feed' in final_url or 'home' in final_url:
                            print("✅ Successfully redirected to LinkedIn feed!")
                            return True
                        elif 'login' in final_url or 'checkpoint' in final_url:
                            print("❌ Still on challenge/login page")
                            
                            # Check if we're actually logged in but still on challenge page
                            try:
                                success_indicators = [
                                    'button[aria-label="Open menu"]',
                                    '.global-nav',
                                    '[data-test-id="nav-home"]'
                                ]
                                for indicator in success_indicators:
                                    element = await self.page.wait_for_selector(indicator, timeout=2000)
                                    if element:
                                        print("✅ Found login success indicator - Login successful!")
                                        return True
                            except:
                                pass
                            
                            return False
                        else:
                            print("✅ Successfully passed CAPTCHA - redirected to new page!")
                            return True
                    else:
                        print(f"Invalid answer index: {answer} (max: {len(clickable_elements)-1})")
                        return False
                        
                except Exception as e:
                    print(f"Error in CAPTCHA solving: {e}")
                    return False
            
            print("Not on a challenge URL")
            return False
            
        except Exception as e:
            print(f"Error in security check detection: {str(e)}")
            return False

    async def run_login_attempts(self, attempts=1):  # Reduced to 2 attempts
        print(f"\n=== Starting {attempts} Login Attempts to Trigger CAPTCHA ===")
        
        async def take_debug_screenshot(name):
            """Helper to take debug screenshots"""
            pass  # Removed screenshot functionality
        
        for attempt in range(1, attempts + 1):
            print(f"\n=== Attempt {attempt}/{attempts} ===")
            
            try:
                # Clear cookies before navigation
                await self.context.clear_cookies()
                
                # Go to login page with cache disabled
                print("Navigating to login page...")
                await self.page.goto('https://www.linkedin.com/login', 
                                   wait_until='domcontentloaded',
                                   timeout=20000)
                await take_debug_screenshot("login_page")
                await asyncio.sleep(1)
                
                # Now try to clear storage (catch errors)
                try:
                    await self.page.evaluate("window.localStorage.clear()")
                    await self.page.evaluate("window.sessionStorage.clear()")
                except Exception as e:
                    print(f"Warning: Could not clear storage: {e}")
                
                # Fill credentials quickly
                print("Entering credentials...")
                await self.page.fill('input[name="session_key"]', self.email)
                await self.page.fill('input[name="session_password"]', self.password)
                await take_debug_screenshot("credentials_filled")
                
                # Click sign in
                print("Clicking sign in...")
                await self.page.click('button[type="submit"]')
                await asyncio.sleep(2)  # Wait a bit longer to let page load
                await take_debug_screenshot("after_submit")
                
                # Debug: Print current URL
                current_url = self.page.url
                print(f"Current URL after login: {current_url}")
                
                # Debug: Check for various elements
                print("\nDebug: Checking page elements...")
                for selector in [
                    'text="Let\'s do a quick security check"',
                    'text="Security Verification"',
                    'text="Protecting your account"',
                    '.challenge-container',
                    'button:has-text("Start Puzzle")',
                    'img[alt*="CAPTCHA"]'
                ]:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            print(f"Found element: {selector}")
                        else:
                            print(f"Not found: {selector}")
                    except Exception as e:
                        print(f"Error checking {selector}: {e}")
                
                # Check for security verification with longer wait
                print("\nChecking for security verification...")
                if await self.check_for_security_verification():
                    print("Successfully handled security check!")
                    return True
                
                # Take final screenshot before next attempt
                await take_debug_screenshot("end_of_attempt")
                print("No security check detected, will try again...")
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error during attempt: {str(e)}")
                await take_debug_screenshot("error_state")
                # On error, clear cookies and continue
                try:
                    await self.context.clear_cookies()
                except:
                    pass
                continue
        
        print("Completed all attempts without solving CAPTCHA")
        return False

    async def human_type(self, selector, text):
        print(f"Attempting to type into field with selector: {selector}")
        try:
            element = await self.page.wait_for_selector(selector)
            if element:
                await element.click()
                for char in text:
                    await element.type(char, delay=100)
                    await asyncio.sleep(0.1)
                print(f"Successfully typed into {selector}")
                return True
            else:
                print(f"Element not found: {selector}")
                return False
        except Exception as e:
            print(f"Error typing into {selector}: {str(e)}")
            return False

    async def clear_captcha_cache(self):
        """Clear any existing CAPTCHA answer before sending new one"""
        print("Clearing CAPTCHA cache...")
        try:
            # Send a dummy image to clear the previous answer
            dummy_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xe7\x07\x13\x0c\x1d\x1c\xc8\xc8\xc8\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf6\x178\xea\x00\x00\x00\x00IEND\xaeB`\x82'
            files = {'image': ('clear.png', dummy_image, 'image/png')}
            response = requests.post('https://www.sellmyagent.com/solve', files=files, timeout=10)
            if response.status_code == 200:
                print("✅ CAPTCHA cache cleared successfully")
                return True
            else:
                print(f"⚠️  Cache clear failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️  Error clearing cache: {e}")
            return False

    async def send_captcha_to_server_direct(self, image_bytes):
        """Send CAPTCHA image without clearing cache (for when cache is already cleared)"""
        print("Sending CAPTCHA image to www.sellmyagent.com...")
        try:
            files = {'image': ('captcha.png', image_bytes, 'image/png')}
            response = requests.post('https://www.sellmyagent.com/solve', files=files, timeout=10)
            if response.status_code == 200:
                print("✅ CAPTCHA image sent to www.sellmyagent.com successfully")
                return True
            else:
                print(f"❌ Failed to send CAPTCHA image: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error sending CAPTCHA to server: {e}")
            return False

    async def send_captcha_to_server(self, image_bytes):
        print("Attempting to send CAPTCHA to www.sellmyagent.com...")
        try:
            # First clear any existing cache
            await self.clear_captcha_cache()
            
            # Wait a moment for cache to clear
            await asyncio.sleep(1)
            
            # Now send the actual CAPTCHA image
            return await self.send_captcha_to_server_direct(image_bytes)
        except Exception as e:
            print(f"❌ Error in send_captcha_to_server: {e}")
            return False

    async def poll_for_answer(self, timeout=120):
        print("Starting to poll for human answer...")
        start = time.time()
        attempts = 0
        
        while time.time() - start < timeout:
            try:
                response = requests.get('https://www.sellmyagent.com/answer', timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get('answer')
                    
                    if answer is not None and str(answer).isdigit():
                        answer_int = int(answer)
                        if 0 <= answer_int <= 5:  # Valid CAPTCHA answer range
                            print(f"✅ Received valid answer: {answer_int}")
                            return answer_int
                        else:
                            print(f"⚠️  Invalid answer range: {answer_int} (should be 0-5)")
                    else:
                        attempts += 1
                        if attempts % 10 == 0:  # Show progress every 20 seconds
                            print(f"⏳ Waiting for answer... (attempt {attempts})")
                        else:
                            print("Waiting for answer...")
                else:
                    print(f"⚠️  Polling error: HTTP {response.status_code}")
            except Exception as e:
                print(f"⚠️  Polling error: {e}")
            
            await asyncio.sleep(2)
        
        print("❌ Timeout waiting for human answer")
        return None

    async def solve_captcha(self):
        print("Starting CAPTCHA solving process...")
        try:
            print("Looking for Start Puzzle button...")
            start_button = await self.page.wait_for_selector('button:has-text("Start Puzzle")', timeout=5000)
            if start_button:
                print("Found Start Puzzle button, clicking...")
                await asyncio.sleep(1)
                await start_button.click()
                print("Waiting for CAPTCHA images to load...")
                await self.page.wait_for_selector('img[src*="data:image"]', timeout=5000)
                print("Looking for CAPTCHA container...")
                captcha_area = await self.page.query_selector('.challenge-container')
                if captcha_area:
                    print("Taking screenshot of CAPTCHA...")
                    screenshot = await captcha_area.screenshot(type='png')
                    print("Sending CAPTCHA to solving server...")
                    sent = await self.send_captcha_to_server(screenshot)
                    if not sent:
                        print("Failed to send CAPTCHA to server")
                        return False
                    print("Waiting for human answer...")
                    answer = await self.poll_for_answer()
                    if answer is None or not (0 <= answer <= 5):
                        print(f"Invalid answer received: {answer}")
                        return False
                    print(f"Got valid answer: {answer}, finding image elements...")
                    images = await self.page.query_selector_all('img[src*="data:image"]')
                    if len(images) > answer:
                        print(f"Clicking image at index {answer}")
                        await asyncio.sleep(1)
                        await images[answer].click()
                        await asyncio.sleep(2)
                        print("CAPTCHA solved successfully")
                        return True
                    else:
                        print(f"Image index {answer} out of range. Total images: {len(images)}")
                else:
                    print("Could not find CAPTCHA container")
        except Exception as e:
            print(f"Error solving CAPTCHA: {str(e)}")
        return False

    async def login(self):
        print("\n=== Starting LinkedIn Login Process ===")
        try:
            print("Navigating to LinkedIn login page...")
            await self.page.goto('https://www.linkedin.com/login')
            await asyncio.sleep(2)
            print("Page loaded, checking for 'Sign in with email' button...")

            try:
                print("Looking for 'Sign in with email' button...")
                sign_in_email_btn = await self.page.query_selector('button:has-text("Sign in with email")')
                if sign_in_email_btn:
                    print("Found 'Sign in with email' button, clicking...")
                    await sign_in_email_btn.click()
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"No 'Sign in with email' button found or error: {e}")

            print("Waiting for login form fields...")
            await self.page.wait_for_selector('input[name="session_key"], input#username, input[name="username"]', timeout=10000)
            await self.page.wait_for_selector('input[name="session_password"], input#password, input[name="password"]', timeout=10000)
            print("Login form fields found")

            email_selectors = ['input[name="session_key"]', 'input#username', 'input[name="username"]']
            password_selectors = ['input[name="session_password"]', 'input#password', 'input[name="password"]']

            print("Attempting to enter email...")
            email_entered = False
            for sel in email_selectors:
                try:
                    if await self.human_type(sel, self.email):
                        email_entered = True
                        print(f"Successfully entered email using selector: {sel}")
                        break
                except Exception as e:
                    print(f"Failed to enter email with selector {sel}: {e}")
                    continue

            if not email_entered:
                print("Failed to enter email with any selector")
                return False

            await asyncio.sleep(0.5)
            
            print("Attempting to enter password...")
            password_entered = False
            for sel in password_selectors:
                try:
                    if await self.human_type(sel, self.password):
                        password_entered = True
                        print(f"Successfully entered password using selector: {sel}")
                        break
                except Exception as e:
                    print(f"Failed to enter password with selector {sel}: {e}")
                    continue

            if not password_entered:
                print("Failed to enter password with any selector")
                return False

            await asyncio.sleep(0.5)

            print("Clicking sign in button...")
            sign_in_button = await self.page.wait_for_selector('button[type="submit"][aria-label="Sign in"], button.sign-in-form__submit-button')
            if sign_in_button:
                await sign_in_button.click()
                print("Sign in button clicked")
            else:
                print("Could not find sign in button")
                return False
            
            await asyncio.sleep(2)

            print("Checking for CAPTCHA...")
            while True:
                try:
                    captcha_exists = await self.page.wait_for_selector('button:has-text("Start Puzzle")', timeout=5000)
                    if captcha_exists:
                        print("CAPTCHA detected, attempting to solve...")
                        success = await self.solve_captcha()
                        if not success:
                            print("Failed to solve CAPTCHA")
                            break
                except:
                    print("No CAPTCHA found or login successful")
                    break

            print("Verifying login success...")
            try:
                await self.page.wait_for_selector('button[aria-label="Open menu"]', timeout=5000)
                print("Login successful! Feed page loaded.")
                return True
            except:
                print("Login verification failed - could not find menu button")
                return False

        except Exception as e:
            print(f"Login error: {str(e)}")
            return False

    async def cleanup(self):
        print("Cleaning up browser resources...")
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        print("Cleanup complete")

async def main():
    email = "my.new.gallery.album@gmail.com"
    password = "Aswin04310"
    
    print("\n=== Starting LinkedIn CAPTCHA Solver ===")
    solver = LinkedInCaptchaSolver(email, password)
    try:
        await solver.init_browser()
        
        # Single login attempt
        print("\n=== Starting Single Login Attempt ===")
        
        # Go to login page
        await solver.page.goto('https://www.linkedin.com/login', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        
        # Clear storage
        try:
            await solver.page.evaluate("window.localStorage.clear()")
            await solver.page.evaluate("window.sessionStorage.clear()")
        except:
            pass
        
        # Enter credentials
        print("Entering credentials...")
        await solver.page.fill('input[name="session_key"]', email)
        await solver.page.fill('input[name="session_password"]', password)
        # await solver.page.screenshot(path="debug_login_filled.png", full_page=True)
        
        # Click sign in
        print("Clicking sign in...")
        await solver.page.click('button[type="submit"]')
        await asyncio.sleep(3)
        
        # Check for CAPTCHA and solve it
        success = await solver.check_for_security_verification()
        
        if success:
            print("\n=== CAPTCHA SOLVED SUCCESSFULLY! ===")
            
            # Wait a bit more for final page load
            await asyncio.sleep(3)
            
            # Verify we're logged in
            current_url = solver.page.url
            print(f"Final URL: {current_url}")
            
            # Take final verification screenshot
            # await solver.page.screenshot(path="debug_final_verification.png", full_page=True)
            
            # Check for login success indicators
            try:
                # Look for LinkedIn feed or profile elements
                success_indicators = [
                    '.feed-identity-module',
                    '[data-test-id="nav-home"]',
                    '.global-nav',
                    'button[aria-label="Open menu"]',
                    '.nav-item__profile-member-photo'
                ]
                
                logged_in = False
                for indicator in success_indicators:
                    try:
                        element = await solver.page.wait_for_selector(indicator, timeout=5000)
                        if element:
                            print(f"✅ LOGIN SUCCESS! Found indicator: {indicator}")
                            logged_in = True
                            break
                    except:
                        continue
                
                if not logged_in and 'feed' in current_url.lower():
                    print("✅ LOGIN SUCCESS! On LinkedIn feed page")
                    logged_in = True
                
                if not logged_in:
                    print("❌ LOGIN VERIFICATION FAILED - Could not find success indicators")
                    print("Current page might still be loading or there might be additional challenges")
                
            except Exception as e:
                print(f"Error during login verification: {e}")
        else:
            print("\n❌ CAPTCHA SOLVING FAILED")
    
    finally:
        print("\nKeeping browser open for 10 seconds for verification...")
        await asyncio.sleep(10)
        await solver.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 