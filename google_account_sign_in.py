from uiautomator import Device, JsonRPCError
from subprocess import call
from timeout_decorator import timeout, TimeoutError
from sys import argv
from time import sleep, time
import argparse

TIMEOUT_DURATION = 600
RETRIES = 2

class GoogleAccountSignInScript:

    # d is the uiautomator Device corresponding to this handler
    d = None

    # Create a parser to accept command line arguments.
    def parse_arguments(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--username", type=str, required=True,
            help="Google account username")
        parser.add_argument("--password", type=str, required=True,
            help="Google account password")
        parser.add_argument("--apps", type=str, nargs='+',
            help="Google Play Store app names to install. Multiple arguments allowed. Example: 'Google Maps' 'Facebook'")
        parser.add_argument("--verify-installation", dest="verify_installation", action='store_true',
            help="Should we verify that these apps were installed successfully? (strongly recommended).\n" +
            "If this flag is not set, then the exit code will be based on whether installation started successfully or not,\n" +
            "but if set, then the exit code will be based on whether the app was verified to open successfully or not.")
        args = parser.parse_args(argv[1:])
        for arg in vars(args):
            setattr(self, arg, getattr(args, arg))

    def clear_device_state(self):
        self.d = None
        for command in [["adb", "uninstall", "com.github.uiautomator"],
            ["adb", "uninstall", "com.github.uiautomator.test"],
            ["adb", "shell", "am", "start", "-a", "android.intent.action.MAIN",
                "-c", "android.intent.category.HOME"]]:
            try:
                call(command)
            except Exception:
                pass

    # Initialize the UIAutomator device
    def initialize_device(self, retry=True):
        try:
            self.d = Device()
            self.d.orientation = "n"
            self.d.press.home()
        except JsonRPCError as e:
            if retry:
                sleep(3)
                self.clear_device_state()
                self.initialize_device(retry=False)
            else:
                raise e

    # Create a uiautomator Device when we create a GoogleAccountSignInScript object
    def __init__(self):
        self.initialize_device()

    # Delete the uiautomator Device when we delete a GoogleAccountSignInScript object,
    # and uninstall any added packages from the device
    def __del__(self):
        self.clear_device_state()

    def dismiss_any_sporadic_popups(self):
        print("Handling initial sporadic popups")
        popup_selectors = {
            "safeSimSelector": {"textMatches": ".*(?i)\\b(sim|mobile data)\\b.*"},
            "unfortunatelySelector": {"textStartsWith": "Unfortunately"},
            "notRespondingSelector": {"textContains": "responding"},
            "safeWhitelistSelector": {"textMatches": ".*(?i)\\b(attention|hands free activation|multi window|select home|update firmware)\\b.*"},
            "negatorySelector": {"clickable": True, "textMatches": ".*(?i)\\b(cancel|later|no|deny|decline|skip|close app|don't send|block)\\b.*"},
            "closeSelector": {"clickable": True, "description": "Close"},
            "affirmatorySelector": {"clickable": True, "textMatches": ".*(?i)\\b(ok|okay|yes|start|accept|allow)\\b.*"},
            "affirmatorySelectorFalsePositive": {"clickable": True, "textMatches": ".*(?i)\\b(autostart)\\b.*"},
            "doNotShowAgainSelector": {"clickable": True, "textMatches": "(?i)(do not|don't) show again"}
        }
        def dont_show_again():
            if (self.d(**popup_selectors["doNotShowAgainSelector"]).exists and
                not self.d(**popup_selectors["doNotShowAgainSelector"]).checked):
                self.d(**popup_selectors["doNotShowAgainSelector"]).click.wait()

        i = 0
        while i < 5:
            if self.d(**popup_selectors["negatorySelector"]).exists:
                dont_show_again()
                self.d(**popup_selectors["negatorySelector"]).click.wait()
                i+=1
            if self.d(**popup_selectors["closeSelector"]).exists:
                dont_show_again()
                self.d(**popup_selectors["closeSelector"]).click.wait()
                i+=1
            if self.d(**popup_selectors["affirmatorySelector"]).exists:
                if (self.d(**popup_selectors["safeSimSelector"]).exists or
                    self.d(**popup_selectors["unfortunatelySelector"]).exists or
                    self.d(**popup_selectors["notRespondingSelector"]).exists or
                    self.d(**popup_selectors["safeWhitelistSelector"]).exists):
                    dont_show_again()
                    self.d(**popup_selectors["affirmatorySelector"]).click.wait()
                elif self.d(**popup_selectors["affirmatorySelectorFalsePositive"]).exists:
                    return True
                else:
                    self.d.press.back()
                i+=1
            else:
                print("Handled initial sporadic popups")
                return True
        print("Failed to handle initial sporadic popups")
        return False


    @timeout(TIMEOUT_DURATION)
    def perform_google_play_walkthrough(self):
        success = False
        attempts = 0
        call(["adb", "shell", "pm", "clear", "com.android.settings"])
        call(["adb", "shell", "pm", "clear", "com.android.vending"])
        self.dismiss_any_sporadic_popups()
        while attempts < RETRIES and not success:
            try:
                success = self.download_and_launch_apps()
            except Exception as e:
                print("Failed due to an error:", type(e), e, e.message if "message" in e.__dict__ else "")
                print("This was the current screen state: %s"%self.d.dump())
            attempts+=1

        return success

    def sign_into_google(self):
        try:
            self.d(textMatches=".*(?i)checking info.*(?i)").wait.gone(timeout=60000)

            # Input username.
            self.d(className="android.widget.EditText").set_text(self.username)
            sleep(1)

            # Click next.
            if self.d(textMatches=".*(?i)next.*").exists:
                self.d(textMatches=".*(?i)next.*").click.wait()
            elif self.d(descriptionMatches=".*(?i)next.*").exists:
                self.d(descriptionMatches=".*(?i)next.*").click.wait()
            else:
                self.d.press.back()
                sleep(4)
                if self.d(textMatches=".*(?i)next.*").exists:
                    self.d(textMatches=".*(?i)next.*").click.wait()
                elif self.d(descriptionMatches=".*(?i)next.*").exists:
                    self.d(descriptionMatches=".*(?i)next.*").click.wait()
                else:
                    self.d(className="android.widget.EditText").click.wait()
                    self.d.press.enter()
                    self.d.press.enter()

            if self.d(textContains=self.username).exists:
                self.d(textContains=self.username).wait.gone(timeout=15000)
                sleep(1)
            else:
                sleep(3)
            self.d(className="android.widget.EditText").wait.exists(timeout=5000)

            # Input password, click next.
            self.d(className="android.widget.EditText").set_text(self.password)
            sleep(1)

            # Click next.
            if self.d(textMatches=".*(?i)next.*").exists:
                self.d(textMatches=".*(?i)next.*").click.wait()
            elif self.d(descriptionMatches=".*(?i)next.*").exists:
                self.d(descriptionMatches=".*(?i)next.*").click.wait()
            else:
                self.d.press.back()
                sleep(4)
                if self.d(textMatches=".*(?i)next.*").exists:
                    self.d(textMatches=".*(?i)next.*").click.wait()
                elif self.d(descriptionMatches=".*(?i)next.*").exists:
                    self.d(descriptionMatches=".*(?i)next.*").click.wait()
                else:
                    self.d(className="android.widget.EditText").click.wait()
                    self.d.press.enter()
                    self.d.press.enter()

            sleep(5)

            if self.d(textMatches="(?i)don\'t sync.*").exists:
                self.d(textMatches="(?i)don\'t sync.*").click.wait()
                sleep(5)
            elif self.d(descriptionMatches="(?i)don\'t sync.*").exists:
                self.d(descriptionMatches="(?i)don\'t sync.*").click.wait()
                sleep(5)

            # Click 'I agree'
            if self.d(textMatches="(?i)i agree").exists:
                self.d(textMatches="(?i)i agree").click.wait()
            elif self.d(descriptionMatches="(?i)i agree").exists:
                self.d(descriptionMatches="(?i)i agree").click.wait()
            else:
                self.d(resourceIdMatches=".*(?i)next.*").click.wait()

            sleep(5)

            if self.d(textMatches=".*(?i)close.*").exists:
                self.d(textMatches=".*(?i)close.*").click.wait()
                sleep(5)
            elif self.d(descriptionMatches=".*(?i)close.*").exists:
                self.d(descriptionMatches=".*(?i)close.*").click.wait()
                sleep(5)

            if self.d(className="android.widget.ProgressBar").exists:
                self.d(className="android.widget.ProgressBar").wait.gone(timeout=30000)
            else:
                sleep(15)

            # Click 'More' or scroll down
            if self.d(className="android.support.v7.widget.RecyclerView").exists:
                self.d(className="android.support.v7.widget.RecyclerView").fling.toEnd()

            if self.d(textMatches="(?i)accept").exists and self.d(scrollable=True).exists:
                self.d(scrollable=True).scroll.to(textMatches="(?i)accept")

            if self.d(textMatches="(?i)accept").exists:
                self.d(textMatches="(?i)accept").click.wait()
            sleep(3)
            return True

        except Exception as e:
            print("Ran into a problem while logging into a Google account: %s"%e)

        for i in range(3):
            self.d.press.back()
            sleep(2)
        return False

        

    def download_app(self, app):
        success = False
        try:
            call(["adb", "shell", "am", "start", "-n",
                "com.android.vending/com.google.android.finsky.activities.MainActivity"])
            self.d(textStartsWith="Search").wait.exists(timeout=10000)
            if not self.d(textStartsWith="Search").exists:
                self.d.press.back()
                call(["adb", "shell", "am", "start", "-n",
                    "com.android.vending/com.google.android.finsky.activities.MainActivity"])
                self.d(textStartsWith="Search").wait.exists(timeout=10000)
            self.d(textStartsWith="Search").click.wait()
            self.d(textStartsWith="Search").set_text(app)
            self.d.press("enter")
            print("Searching for %s"%app)
            self.d(textStartsWith="Install").wait.exists(timeout=15000)
            for string in ["Install", "Update"]:
                if not self.d(text="Open").exists and self.d(textStartsWith=string).exists:
                    self.d(textStartsWith=string).click.wait()
                    print("Clicked install, and now waiting until it finishes")
                    sleep(5)
                    if self.d(textStartsWith="Continue").exists:
                        self.d(textStartsWith="Continue").click.wait()
                        sleep(1)
                        self.d(textStartsWith="Skip").click.wait()
                    self.d(text="Open").wait.exists(timeout=300000)

            print("Now checking if %s is launchable"%app)
            if self.d(text="Open").exists:
                old_package = self.d.info["currentPackageName"]
                self.d(text="Open").click.wait()
                sleep(10)
                success = self.d.info["currentPackageName"] != old_package
            elif self.d(textContains="Pending").exists and self.d(textContains="Cancel").exists:
                self.d(textContains="Cancel").click.wait()

        except Exception as e:
            print("Ran into a problem while downloading the app '%s': %s"%(app, e))

        for i in range(5):
            self.d.press.back()
            sleep(2)
        return success

    @timeout(TIMEOUT_DURATION/RETRIES)
    def download_and_launch_apps(self):
        try:
            call(["adb", "shell", "am", "start", "-n",
                "com.android.vending/com.google.android.finsky.activities.MainActivity"])
            self.d(descriptionStartsWith="Voice").wait.exists(timeout=10000)

            if not self.d(textContains=self.username).exists:
                if self.d(textMatches="(?i)sign in").exists:
                    self.d(textMatches="(?i)sign in").click.wait()
                else:
                    call(["adb", "shell", "am", "start", "-W", "-a", "android.settings.SYNC_SETTINGS"])
                    sleep(3)
                    if not self.d(textContains=self.username).exists:
                        self.d(textMatches="(?i).*(add account).*").click.wait()
                        sleep(3)
                        self.d(textMatches="(?i)google")[-1].click.wait()
                        sleep(3)
                        print("Navigated to the Google Sign-in page")

                if not self.d(textContains=self.username).exists:
                    if not self.sign_into_google():
                        print("Failed to sign into the Google account")
                        self.d.press.back()
                        self.d.press.back()
                        return False

                self.d.press.back()
                self.d.press.back()
                call(["adb", "shell", "am", "start", "-n",
                    "com.android.vending/com.google.android.finsky.activities.MainActivity"])
                self.d(descriptionStartsWith="Voice").wait.exists(timeout=10000)

            if self.d(textMatches='.*(?i)not now.*').exists:
                self.d(textMatches='.*(?i)not now.*').click.wait()

            if self.d(descriptionStartsWith="Signed in").exists:
                self.d(descriptionStartsWith="Signed in").click.wait()
            elif self.d(descriptionStartsWith='Voice').exists:
                self.d(descriptionStartsWith='Voice').right(className='android.widget.ImageView').click.wait()
            else:
                self.d(textStartsWith="Search").right(className='android.widget.ImageView').click.wait()
            
            self.d(descriptionContains="Expand account list").wait.exists(timeout=10000)
            if self.d(descriptionContains="Expand account list").exists or not self.d(textContains=self.username).exists:
                self.d(descriptionContains="Expand account list").click.wait()
                sleep(1)
            self.d(textContains=self.username).click.wait()
            sleep(3)

            print("Going to download each app")

            success = True
            if self.verify_installation:
                for app in self.apps:
                    success = success and self.download_app(app)
            else:
                for app in self.apps:
                    self.download_app(app)

            return success

        except Exception as e:
            print("Failed due to an error:", type(e), e, e.message if "message" in e.__dict__ else "")
            print("This was the current screen state: %s"%self.d.dump())
            if type(e) is TimeoutError:
                raise e
        return False

if __name__ == "__main__":
    start_time = time()
    print("Starting script!")
    success = False
    duration = -1
    try:
        google_account_sign_in_class = GoogleAccountSignInScript()
        google_account_sign_in_class.parse_arguments()
        TIMEOUT_DURATION += 300 * (len(google_account_sign_in_class.apps)-1)
        try:
            success = device_farm_google_account_sign_in_class.perform_google_play_walkthrough()
        except TimeoutError:
            print("Timed out!")
            success = False
        duration = time()-start_time
        google_account_sign_in_class = None
    except Exception as e:
        print(type(e), e, e.message if "message" in e.__dict__ else "")
    print("Took %s to %s complete the script"%
        (duration, "successfully" if success else "unsuccessfully"))
    exit(0 if success else 1)
