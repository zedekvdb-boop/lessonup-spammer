import os
import time
import threading
import logging
import random
import traceback
from typing import List

# --- Dependency Installation ---
# Make sure you have run: pip install selenium webdriver-manager
import selenium
import webdriver_manager
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# --- MODIFICATION: Correct import for Chromium ---
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType  # <-- This line is fixed
# --- END MODIFICATION ---


# --- Logger Configuration ---
# Suppress unnecessary logs from Selenium
# ... (rest of the file is unchanged) ...
logger = logging.getLogger('selenium.webdriver.remote.remote_connection')
logger.setLevel(logging.ERROR)
logging.getLogger('webdriver_manager').setLevel(logging.ERROR)


class LessonUpBot:
    """
    A bot to automate joining a LessonUp.app session with multiple users.
    
    Each user joins in a separate thread.
    """
    
    def __init__(self, code: str, base_name: str, bot_count: int):
        """
        Initializes the bot with the session code, base name, and bot count.
        
        Args:
            code (str): The LessonUp session code.
            base_name (str): The base name for the bots (e.g., "james").
            bot_count (int): The number of bots to create.
        """
        self.code = code
        
        # --- NEW: Automatically generate the names list ---
        self.names = []
        for i in range(1, bot_count + 1):
            self.names.append(f"{base_name}{i}")
        # --- END NEW ---
        
        if not self.names:
            print(f"Warning: The names list is empty. Bot will not join.")

    # The _load_names method has been removed, as we now define the names list in __init__

    @staticmethod
    def _join_user_thread(code: str, player: str):
        """
        The core logic for a single user joining the session.
        This function is executed in its own thread and manages its own WebDriver.
        
        Args:
            code (str): The LessonUp session code.
            player (str): The name of the player to join.
        """
        
        # --- FIX for NameError ---
        # Import dependencies inside the thread function to ensure they are in scope.
        from selenium import webdriver
        # --- MODIFICATION: Correct import for Chromium ---
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.core.os_manager import ChromeType  # <-- This line is fixed
        # --- END MODIFICATION ---
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.wait import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import traceback 
        # --- END FIX ---

        driver = None
        # --- MODIFICATION: Increased timeout for slow JS loading ---
        TIMEOUT = 35 
        
        try:
            # --- Progress Indicator ---
            print(f"[INFO] Thread started for {player}. Initializing browser...")

            # --- Driver Options ---
            # Use ChromeOptions
            options = webdriver.ChromeOptions()
            options.add_argument("--log-level=3")  # Suppress console logs
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_argument('--headless')  # Run in background (optional, remove if you want to see the browsers)
            options.add_argument('--disable-gpu') # Often needed for headless
            options.add_argument("--mute-audio") # Mute audio
            options.add_argument("--window-size=1920,1080") # Specify window size
            
            # --- REMOVED COLAB-SPECIFIC OPTIONS ---
            # options.binary_location = '/usr/bin/google-chrome' # This was for Linux/Colab
            # options.add_argument('--no-sandbox') # This was for Linux/Colab
            # options.add_argument('--disable-dev-shm-usage') # This was for Linux/Colab
            
            # --- NOTE FOR CHROMIUM ---
            # Pointing to your specific Chromium installation
            options.binary_location = r"C:\Users\zedek\AppData\Local\Chromium\Application\chrome.exe"
            # --- END NOTE ---

            # --- Driver Initialization ---
            # --- MODIFICATION: Use ChromeDriverManager pointed at Chromium ---
            driver_path = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
            # --- END MODIFICATION ---
            service = webdriver.ChromeService(driver_path, log_output=os.devnull)
            driver = webdriver.Chrome(service=service, options=options)
            
            # --- Selenium Logic ---
            print(f"[INFO] {player} opening URL...")
            driver.get(f"https://lessonup.app/?lang=en&code={code}")
            
            # --- NEW: Check for an error message first ---
            try:
                # Wait a brief moment (5s) for any error message to appear
                # We look for common error text patterns.
                error_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'error') or contains(@class, 'alert') or contains(text(), 'not found') or contains(text(), 'Invalid') or contains(text(), 'ongeldig') or contains(text(), 'niet gevonden')]"))
                )
                # If we find an error, print its text and stop this thread
                error_text = error_element.text.strip() or "Unknown Error"
                if error_text:
                    print(f"[ERROR] {player} found an error on the page: '{error_text}'. The session code might be invalid or expired.")
                else:
                    print(f"[ERROR] {player} found an error element, but it has no text. The session code might be invalid or expired.")
                return # Exit the function
            except Exception:
                # This is GOOD! It means no error was found.
                print(f"[INFO] {player} found no immediate errors. Proceeding...")
                pass
            # --- END NEW CHECK ---

            # --- NEW: Check if we are stuck on the code entry page ---
            try:
                # Wait 2 seconds to see if the code input field is still there.
                code_input = WebDriverWait(driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@name='code']"))
                )
                # If it's still there, the code was bad and the page didn't change.
                print(f"[ERROR] {player} is still on the code entry page. The session code is likely invalid or expired.")
                return # Exit the function
            except Exception:
                # This is GOOD! It means the code input is gone and we've moved to the next page.
                print(f"[INFO] {player} has left the code entry page. Looking for name input...")
                pass
            # --- END NEW CHECK ---
            
            print(f"[INFO] {player} checking current page for name input...")
            
            # Wait for the name input field to be present
            # We try multiple, more robust selectors instead of just one brittle XPath.
            name_input = None
            
            # Selector 1: Try finding by name attribute 'name', which is most common
            try:
                name_input = WebDriverWait(driver, TIMEOUT).until(
                    EC.presence_of_element_located((By.NAME, "name"))
                )
            except Exception:
                pass # Try next selector

            # Selector 2: Fallback: try finding by a placeholder containing "Name" or "name"
            if not name_input:
                try:
                    name_input = WebDriverWait(driver, TIMEOUT).until(
                        EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, 'Name') or contains(@placeholder, 'name')]"))
                    )
                except Exception:
                    pass # Try next selector

            # Selector 3: Fallback: Find the first text input inside a form
            if not name_input:
                try:
                    name_input = WebDriverWait(driver, TIMEOUT).until(
                        EC.presence_of_element_located((By.XPATH, "//form//input[@type='text']"))
                    )
                except Exception:
                    pass # Try last resort
            
            # Selector 4: Fallback: try the original brittle XPath (last resort)
            if not name_input:
                try:
                    name_input_xpath = "/html/body/div[3]/div/div[3]/div/div[1]/form/input[1]"
                    name_input = WebDriverWait(driver, TIMEOUT).until(
                        EC.presence_of_element_located((By.XPATH, name_input_xpath))
                    )
                except Exception as e:
                    # If all selectors fail, print a specific error
                    print(f"[ERROR] Could not find name input for {player}. Page structure may have changed, or the code is invalid.")
                    raise e # Re-raise the exception to be caught by the outer block
            
            
            # Send the player name
            name_input.clear()
            name_input.send_keys(player)
            
            # Instead of Keys.RETURN, let's find and click the submit button
            submit_button = None
            try:
                # Try to find a submit button within the same form
                submit_button = name_input.find_element(By.XPATH, "./ancestor::form//button[@type='submit']")
            except Exception:
                pass # Try another selector
            
            if not submit_button:
                try:
                    # Try finding a button with text 'Join', 'Play', or 'Go'
                    submit_button = driver.find_element(By.XPATH, "//button[contains(., 'Join') or contains(., 'Play') or contains(., 'Go')]")
                except Exception:
                    pass # Try just pressing Enter as a fallback

            if submit_button:
                print(f"[INFO] {player} clicking submit button...")
                # Click the button
                try:
                    # Use a JavaScript click as it's often more reliable
                    driver.execute_script("arguments[0].click();", submit_button)
                except Exception:
                    # Fallback to standard click
                    submit_button.click()
            else:
                # Fallback to pressing Enter if no button was found
                print(f"[WARNING] Could not find submit button for {player}. Trying to submit with Enter key.")
                name_input.send_keys(Keys.RETURN)
            
            # Short pause to ensure request is sent before quitting
            time.sleep(2) 
            print(f"[SUCCESS] Join request sent for: {player}")
            
        except Exception as e:
            # Check if it was a timeout error
            if "timeout" in str(e).lower():
                print(f"[ERROR] Failed to join with {player}: Timeout exceeded ({TIMEOUT}s). The page may not have loaded correctly or the session might be closed.")
            else:
                # Print a detailed error message using the traceback module
                print(f"[ERROR] Failed to join with {player}: {type(e).__name__} - {e}")
                print(f"[DEBUG] Full exception details for {player}:\n{traceback.format_exc()}")
        finally:
            # --- Cleanup ---
            # Ensure the driver is closed even if an error occurs
            if driver:
                driver.quit()

    def run(self):
        """
        Starts the process of joining all users from the names list.
        Each user is joined in a separate thread.
        """
        print(f"Starting to join session {self.code} with {len(self.names)} users...")
        threads = []
        for player in self.names:
            # Create a new thread for each player
            t = threading.Thread(target=self._join_user_thread, args=(self.code, player))
            threads.append(t)
            t.start()
            
            # --- MODIFICATION: Increased stagger to stabilize ---
            # Stagger the joins more to prevent overwhelming your computer
            time.sleep(random.uniform(1.0, 2.5)) 
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        print("-------------------")
        print("All join requests complete.")

    @staticmethod
    def titlebar():
        """Prints the script's title bar."""
        print("LessonUp.app Autojoiner")
        print("made by zedekvdb")
        print("-------------------")

    @staticmethod
    def clear_screen():
        """Clears the console screen."""
        os.system("cls" if os.name == "nt" else "clear")
        LessonUpBot.titlebar()


def main():
    """
    Main function to run the bot.
    """
    os.system("cls" if os.name == "nt" else "clear")
    LessonUpBot.titlebar()
    
    try:
        # --- NEW: Get all inputs ---
        code = input("Enter LessonUp code: ").strip()
        if not code:
            print("No code entered. Exiting.")
            return
            
        base_name = input("Enter the base name for the bots (e.g., 'james'): ").strip()
        if not base_name:
            print("No base name entered. Exiting.")
            return
        
        try:
            bot_count_str = input("How many bots do you want to send? (e.g., '10'): ").strip()
            bot_count = int(bot_count_str)
            if bot_count <= 0:
                print("Please enter a positive number.")
                return
        except ValueError:
            print("That's not a valid number. Exiting.")
            return
        # --- END NEW ---
            
        LessonUpBot.clear_screen()
        time.sleep(1) # Pause to show title
        
        # --- NEW: Pass all inputs to the bot ---
        bot = LessonUpBot(code, base_name, bot_count)
        bot.run()
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()