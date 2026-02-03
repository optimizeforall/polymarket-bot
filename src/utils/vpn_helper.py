"""
vpn_helper.py - Configure HTTP clients to use residential proxy or VPN

This module patches the py_clob_client's httpx client to route traffic
through a residential proxy (Bright Data) or WireGuard VPN interface.

This allows Polymarket API calls to appear from a residential IP instead
of the AWS server IP, bypassing Cloudflare blocking.
"""

import httpx
import socket
from typing import Optional

# =============================================================================
# IPROYAL RESIDENTIAL PROXY CONFIGURATION
# =============================================================================
PROXY_HOST = "geo.iproyal.com"
PROXY_PORT = 12321
PROXY_USERNAME = "wYdIhMIOHa6q7ick"
PROXY_PASSWORD = "KQHCd2W9LhIR7aux_country-ca_session-K2gtLaDP_lifetime-168h"

# Construct proxy URL
PROXY_URL = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{PROXY_PORT}"

# WireGuard VPN interface IP (fallback)
VPN_LOCAL_ADDRESS = "10.70.79.182"


def check_proxy_available() -> bool:
    """Check if the IPRoyal proxy is configured."""
    return bool(PROXY_USERNAME and PROXY_PASSWORD)


def check_vpn_available() -> bool:
    """Check if the WireGuard VPN interface is up and available."""
    try:
        # Try to bind to the VPN IP
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((VPN_LOCAL_ADDRESS, 0))
        sock.close()
        return True
    except OSError:
        return False


def create_proxy_transport() -> httpx.HTTPTransport:
    """Create an httpx transport that uses IPRoyal residential proxy."""
    return httpx.HTTPTransport(
        proxy=PROXY_URL,
        http2=True
    )


def create_vpn_transport() -> httpx.HTTPTransport:
    """Create an httpx transport that uses the VPN interface."""
    return httpx.HTTPTransport(
        local_address=VPN_LOCAL_ADDRESS,
        http2=True
    )


def create_proxy_client() -> httpx.Client:
    """Create an httpx client configured to use IPRoyal proxy."""
    transport = create_proxy_transport()
    return httpx.Client(transport=transport, http2=True, timeout=30.0)


def create_vpn_client() -> httpx.Client:
    """Create an httpx client configured to use the VPN interface."""
    transport = create_vpn_transport()
    return httpx.Client(transport=transport, http2=True)


def patch_polymarket_client(use_proxy: bool = True) -> bool:
    """
    Monkey-patch the py_clob_client's httpx client to use residential proxy or VPN.
    
    Args:
        use_proxy: If True, use Bright Data proxy. If False, try VPN.
    
    Returns True if patching was successful, False otherwise.
    """
    try:
        # Import the helpers module
        from py_clob_client.http_helpers import helpers
        
        if use_proxy and check_proxy_available():
            # Use IPRoyal residential proxy
            new_client = create_proxy_client()
            method = f"IPRoyal proxy (Canada)"
        elif check_vpn_available():
            # Fallback to VPN
            new_client = create_vpn_client()
            method = f"VPN ({VPN_LOCAL_ADDRESS})"
        else:
            print("⚠️ No proxy or VPN available - using default network")
            return False
        
        # Replace the global client
        old_client = helpers._http_client
        helpers._http_client = new_client
        
        # Close old client
        try:
            old_client.close()
        except:
            pass
        
        print(f"✅ Polymarket client patched to use {method}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to patch Polymarket client: {e}")
        return False


def test_proxy_connection() -> Optional[str]:
    """
    Test the Bright Data proxy connection.
    
    Returns the external IP if successful, None otherwise.
    """
    if not check_proxy_available():
        return None
    
    try:
        client = create_proxy_client()
        response = client.get("https://api.ipify.org", timeout=15)
        client.close()
        return response.text.strip()
    except Exception as e:
        print(f"Proxy test failed: {e}")
        return None


def test_vpn_connection() -> Optional[str]:
    """
    Test the VPN connection by making a request to ifconfig.me/ip.
    
    Returns the external IP if successful, None otherwise.
    """
    if not check_vpn_available():
        return None
    
    try:
        client = create_vpn_client()
        response = client.get("https://api.ipify.org", timeout=10)
        client.close()
        return response.text.strip()
    except Exception as e:
        print(f"VPN test failed: {e}")
        return None


def get_proxy_status() -> dict:
    """Get current proxy status information."""
    proxy_available = check_proxy_available()
    proxy_ip = test_proxy_connection() if proxy_available else None
    
    return {
        "proxy_available": proxy_available,
        "proxy_host": PROXY_HOST if proxy_available else None,
        "proxy_country": "Canada",
        "proxy_external_ip": proxy_ip,
        "status": "connected" if proxy_ip else ("configured" if proxy_available else "not_configured")
    }


def get_vpn_status() -> dict:
    """Get current VPN status information."""
    vpn_available = check_vpn_available()
    vpn_ip = test_vpn_connection() if vpn_available else None
    
    return {
        "vpn_available": vpn_available,
        "vpn_local_address": VPN_LOCAL_ADDRESS if vpn_available else None,
        "vpn_external_ip": vpn_ip,
        "status": "connected" if vpn_ip else ("interface_up" if vpn_available else "disconnected")
    }


if __name__ == "__main__":
    # Test the proxy/VPN helper
    print("Proxy/VPN Helper Test")
    print("=" * 40)
    
    # Test IPRoyal Proxy first
    print("\n1. Testing IPRoyal Residential Proxy...")
    proxy_status = get_proxy_status()
    print(f"   Proxy Available: {proxy_status['proxy_available']}")
    print(f"   Proxy Host: {proxy_status['proxy_host']}")
    print(f"   Proxy Country: {proxy_status['proxy_country']}")
    print(f"   Proxy External IP: {proxy_status['proxy_external_ip']}")
    print(f"   Status: {proxy_status['status']}")
    
    # Test VPN as fallback
    print("\n2. Testing WireGuard VPN (fallback)...")
    vpn_status = get_vpn_status()
    print(f"   VPN Available: {vpn_status['vpn_available']}")
    print(f"   VPN Local Address: {vpn_status['vpn_local_address']}")
    print(f"   VPN External IP: {vpn_status['vpn_external_ip']}")
    print(f"   Status: {vpn_status['status']}")
    
    # Patch client
    print("\n3. Patching Polymarket client...")
    success = patch_polymarket_client(use_proxy=True)
    print(f"   Patch successful: {success}")
    
    # Test Polymarket API
    if success:
        print("\n4. Testing Polymarket API...")
        try:
            from py_clob_client.http_helpers import helpers
            response = helpers._http_client.get("https://clob.polymarket.com/markets?limit=1", timeout=15)
            if response.status_code == 200:
                print("   ✅ Polymarket API accessible!")
            else:
                print(f"   ❌ Polymarket API returned {response.status_code}")
        except Exception as e:
            print(f"   ❌ Polymarket API error: {e}")
