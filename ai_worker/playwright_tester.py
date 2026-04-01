import re
from playwright.sync_api import Page, expect
import imagehash
from PIL import Image
from skimage.metrics import structural_similarity as ssim
import numpy as np

class Playwright:
    def __init__(self, open_on: str = 'http://localhost:3000/'):
        self.open_on = open_on


    def test_has_title(self, page: Page):
        page.goto(self.open_on)

        # Expect a title "to contain" a substring.
        expect(page).to_have_title(re.compile("Playwright"))

    def test_page_exists(self, page: Page, url: str):
        page.goto(f"{self.open_on}{url}")
        expect(page).to_have_url(re.compile(url))

    def get_screenshot_of_component(self, page: Page, component_selector: str, path: str = "component.png"):
        page.locator(component_selector).screenshot(path=path)

    def phash_compare(self, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(component_selector, "component.png")

        hash1 = imagehash.phash(Image.open("component.png"))
        hash2 = imagehash.phash(Image.open(figma_screenshot))

        return hash1 - hash2 # Lower = more similar, 0 means identical

    def ssim_compare(self, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(component_selector, "component.png")

        # TODO: Implement SSIM comparison
        pass

    def mse_compare(self, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(component_selector, "component.png")

        # TODO: Implement MSE comparison
        pass

    def histogram_compare(self, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(component_selector, "component.png")

        # TODO: Implement histogram comparison
        pass

    def feature_matching(self, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(component_selector, "component.png")

        # TODO: Implement feature matching
        pass

    # this could be used to determine if I did import the data correctly when populating a page
    # this searches for an image inside another image

    def template_match(self, component_selector: str, used_image: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(component_selector, "component.png")

        # TODO: Implement template matching
        pass

    # this seems to be using AI to compare the images

    def clip_similarity(self, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(component_selector, "component.png")

        # TODO: Implement clip similarity
        pass
