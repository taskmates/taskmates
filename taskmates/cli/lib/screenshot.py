import subprocess


def take_screenshot(output_path):
    # Use the screencapture command to take a screenshot
    subprocess.run(["screencapture", "-i", output_path])
