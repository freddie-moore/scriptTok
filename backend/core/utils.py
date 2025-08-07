import re

def extract_script_contents(html: str) -> str:
    """
    Extracts the content of the first <script>...</script> tag from the input string.
    If no script tags are found, returns the original string.
    """
    match = re.search(r'<script[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return html