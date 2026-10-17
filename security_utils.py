"""Security and URL validation utilities.

Provides defense against Server-Side Request Forgery (SSRF), internal IP leakage,
unbounded responses, and malicious file uploads.
"""

import ipaddress
import os
import socket
from urllib.parse import urlparse, urljoin
import requests

# Maximum allowed file size for resume uploads (10 MB)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Maximum allowed response size when fetching external web pages (512 KB)
MAX_RESPONSE_SIZE_BYTES = 512 * 1024

# Default request timeout in seconds
REQUEST_TIMEOUT = 6

# Standard user agent for safe metadata discovery
SAFE_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 CareerReadinessAnalyzer/2.0"


def is_ip_private_or_restricted(ip_str: str) -> bool:
    """Check if an IP string belongs to private, loopback, link-local, or reserved ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        )
    except ValueError:
        return True


def is_safe_url(url: str) -> tuple[bool, str]:
    """Validate that a URL is safe to fetch and does not target internal or restricted networks.
    
    Returns:
        (is_safe, reason_or_error_message)
    """
    if not url or not isinstance(url, str):
        return False, "Empty or invalid URL"

    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception as exc:
        return False, f"Malformed URL: {exc}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unsupported URL scheme: {parsed.scheme} (only HTTP and HTTPS are permitted)"

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname in URL"

    hostname_lower = hostname.lower()

    # Block well-known internal hostnames
    blocked_hosts = {
        "localhost",
        "127.0.0.1",
        "::1",
        "metadata.google.internal",
        "instance-data",
    }
    if hostname_lower in blocked_hosts or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
        return False, "Access to localhost or internal network destinations is blocked"

    # Attempt DNS resolution to check resolved IP
    try:
        # Resolve all addresses (IPv4 and IPv6)
        addr_info = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        for item in addr_info:
            ip_str = item[4][0]
            if is_ip_private_or_restricted(ip_str):
                return False, f"URL resolves to private or restricted IP address: {ip_str}"
    except socket.gaierror:
        return False, f"Hostname could not be resolved via DNS: {hostname}"
    except Exception as exc:
        return False, f"DNS resolution error: {exc}"

    return True, "Safe"


def safe_fetch(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    max_redirects: int = 3,
    max_bytes: int = MAX_RESPONSE_SIZE_BYTES,
    timeout: int = REQUEST_TIMEOUT,
) -> tuple[bool, int | None, str | bytes, str]:
    """Safely fetch a URL following redirects with SSRF validation at every hop.
    
    Returns:
        (success, status_code, content, message)
    """
    current_url = url
    req_headers = {"User-Agent": SAFE_USER_AGENT, "Accept": "*/*"}
    if headers:
        req_headers.update(headers)

    for redirect_count in range(max_redirects + 1):
        safe, reason = is_safe_url(current_url)
        if not safe:
            return False, None, "", f"Blocked unsafe URL: {reason}"

        try:
            # We handle redirects manually to validate each target
            with requests.request(
                method=method,
                url=current_url,
                headers=req_headers,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            ) as resp:
                # Handle redirects (301, 302, 303, 307, 308)
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        return False, resp.status_code, "", "Redirect with missing Location header"
                    # Resolve relative redirects
                    current_url = urljoin(current_url, location)
                    continue

                # Read response up to max_bytes to avoid memory exhaustion
                content_chunks = []
                bytes_read = 0
                for chunk in resp.iter_content(chunk_size=8192):
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    if bytes_read > max_bytes:
                        break
                    content_chunks.append(chunk)

                raw_data = b"".join(content_chunks)
                try:
                    encoding = resp.encoding or "utf-8"
                    text_content = raw_data.decode(encoding, errors="replace")
                except Exception:
                    text_content = raw_data.decode("utf-8", errors="replace")

                return True, resp.status_code, text_content, "OK"

        except requests.exceptions.Timeout:
            return False, None, "", "Request timed out"
        except requests.exceptions.SSLError:
            return False, None, "", "SSL certificate verification failed"
        except requests.exceptions.ConnectionError:
            return False, None, "", "Connection failed"
        except Exception as exc:
            return False, None, "", f"Request failed: {type(exc).__name__}"

    return False, None, "", "Exceeded maximum allowed redirects"


def validate_pdf_file(uploaded_file) -> tuple[bool, str]:
    """Validate uploaded PDF file format, size, and header.
    
    Returns:
        (is_valid, error_message)
    """
    if uploaded_file is None:
        return False, "No file was uploaded."

    filename = getattr(uploaded_file, "name", "file.pdf")
    if not filename.lower().endswith(".pdf"):
        return False, "Only PDF (.pdf) files are accepted."

    size = getattr(uploaded_file, "size", 0)
    if size > MAX_FILE_SIZE_BYTES:
        return False, f"File size ({size / (1024 * 1024):.1f} MB) exceeds maximum allowed limit (10 MB)."

    # Read first 1024 bytes to check PDF header
    try:
        current_pos = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
        header = uploaded_file.read(1024)
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(current_pos)

        if not header.startswith(b"%PDF-"):
            # Some PDFs have comments or BOM before %PDF-
            if b"%PDF-" not in header[:512]:
                return False, "File does not appear to be a valid PDF document (missing %PDF signature)."
    except Exception as exc:
        return False, f"Could not inspect uploaded file: {exc}"

    return True, "Valid PDF"
