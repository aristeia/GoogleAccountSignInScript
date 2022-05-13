# GoogleAccountSignInScript
This script will automatically sign into a given Google account on an attached Android device, and automatically download apps from the app store. It assumes that the device is the only Android device connected to your machine, and that the device is authorized over ADB for debugging. The script can be used at the beginning of an automation test so that your device will begin pre-provisioned with a Google account and apps from the app store, and has been tested against a large swath of device models. In my own testing, I've found that this script works well against AWS Device Farm public devices.  

There is a list of device models known to generally work well with this script in the file `known_working_devices.txt`.

# Build Instructions for Local Development
We recommend building this repository using a Python3 virtual environment. Initialize such an environment as follows:

```python
python3 -m virtualenv .
. ./bin/activate
```

Then, you can install the required dependencies:
```python
pip install -r requirements.txt
```

And now, you can run the script locally for development purposes.

# Usage Instructions

```bash
usage: google_account_sign_in.py [-h] --username USERNAME --password PASSWORD
                                      --apps APPS [APPS ...]] [--verify-installation]

optional arguments:
  -h, --help            show this help message and exit
  --username USERNAME   Google account username
  --password PASSWORD   Google account password
  --apps APPS [APPS ...]
                        Google Play Store app names to install. Multiple arguments allowed.
                        Example: 'Google Maps' 'Facebook'
  --verify-installation
                        Should we verify that these apps were installed successfully? (strongly
                        recommended). If this flag is not set, then the exit code will be based on
                        whether installation started successfully or not, but if set, then the exit
                        code will be based on whether the app was verified to open successfully or
                        not.
```

# Usage Instructions in AWS Device Farm

This script can be ran in AWS Device Farm using a custom environment mode test spec file (ref https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environments.html). Simply add the script to your test package, and add instructions for running the script to your test spec file based on your test type (described below):

## If you are using the Appium Python test type
If you are using the Appium Python test type, then you will either want to combine this test with your test suite code, or separately include it in a subdirectory of your existing ZIP package. You can reuse the same instructions you're currently using for your test package, and just run this script as a standard Python script before running your real Python code using extremely similar instructions. The main difference is that this script is meant to be ran directly from the Python binary and not from any test framework like pytest or unittest.

## If you are using any other Appium test type
If you are using any other Appium test type, then simply include these files in the root of your existing test ZIP bundle. Then, you would add the following commands to the install phase of your test spec file:

```yaml
      - cd $DEVICEFARM_TEST_PACKAGE_PATH
      - virtualenv3 .
      - . ./bin/activate
      - pip install --upgrade pip
      - pip install -r requirements.txt
```
Then the following code to the test phase of your test spec file:

```yaml
      - python google_account_sign_in.py YOUR_ARGUMENTS_HERE
```

## General Usage Note

If you want to guarantee that the script successfully executes before your Device Farm test, then we recommend putting this script at the beginning of your "test phase" for your custom environment mode test spec file (ref https://docs.aws.amazon.com/devicefarm/latest/developerguide/custom-test-environments.html). This script, when ran with the `--verify-installation` flag, will return a non-zero exit code if it fails to verify that the apps were installed, thereby preventing your test from running in subsequent test spec instructions.