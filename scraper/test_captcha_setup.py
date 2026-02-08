#!/usr/bin/env python3
"""
Test script to verify CAPTCHA solving and anti-detection setup
Enhanced with pydoll, Patchright, and Botright support
"""

import asyncio
import os
from consent_handler import (
    create_undetected_browser,
    close_undetected_browser,
    navigate_with_cloudflare_bypass,
    apply_anti_automation_measures,
    detect_and_solve_captcha,
    handle_consent_and_blockages,
    verify_fingerprint_consistency,
    PYDOLL_AVAILABLE,
    PATCHRIGHT_AVAILABLE,
    BOTRIGHT_AVAILABLE,
)


async def test_eventbrite_access():
    """Test accessing Eventbrite with enhanced anti-detection"""
    print("=" * 60)
    print("Testing Eventbrite Access with Enhanced Anti-Detection")
    print("=" * 60)
    
    # Check for API keys
    nopecha_key = os.environ.get("NOPECHA_API_KEY")
    captcha_key = os.environ.get("CAPTCHA_SOLVER_API_KEY")
    anticaptcha_key = os.environ.get("ANTICAPTCHA_API_KEY")
    
    print("\n📋 Available Technologies:")
    print(f"  pydoll (Cloudflare bypass): {'✅ Available' if PYDOLL_AVAILABLE else '❌ Not installed'}")
    print(f"  Patchright (Enhanced stealth): {'✅ Available' if PATCHRIGHT_AVAILABLE else '❌ Not installed'}")
    print(f"  Botright (Advanced anti-detect): {'✅ Available' if BOTRIGHT_AVAILABLE else '❌ Not installed'}")
    
    print("\n📋 CAPTCHA API Key Status:")
    print(f"  NopeCHA: {'✅ Set' if nopecha_key else '❌ Not set'}")
    print(f"  2Captcha: {'✅ Set' if captcha_key else '❌ Not set'}")
    print(f"  Anti-Captcha: {'✅ Set' if anticaptcha_key else '❌ Not set'}")
    
    if not PYDOLL_AVAILABLE and not PATCHRIGHT_AVAILABLE:
        print("\n⚠️  WARNING: No enhanced browser engines available!")
        print("   Install for better results:")
        print("   pip install pydoll patchright")
    
    browser = None
    browser_type = None
    
    try:
        print("\n🚀 Creating undetected browser...")
        browser, page, browser_type = await create_undetected_browser(
            use_pydoll=True,
            use_patchright=True,
            use_botright=False,
            headless=False  # Set to False to see what's happening
        )
        
        print(f"✅ Using {browser_type} browser")
        
        # Verify fingerprint consistency
        print("\n🔍 Verifying fingerprint consistency...")
        is_consistent, issues = await verify_fingerprint_consistency(page, browser_type)
        
        if not is_consistent:
            print("⚠️  Fingerprint has issues - may be detected")
        
        # Apply additional measures for non-pydoll browsers
        if browser_type != 'pydoll':
            print("🛡️  Applying anti-detection measures...")
            await apply_anti_automation_measures(page)
        
        # Test URL
        test_url = "https://www.eventbrite.com/d/ca--los-angeles/free--events/?page=1"
        
        print(f"\n🌐 Navigating to: {test_url}")
        nav_success = await navigate_with_cloudflare_bypass(page, test_url, browser_type, timeout=30000)
        
        if not nav_success:
            print("❌ Failed to navigate to page")
            return
        
        print("✅ Page loaded successfully")
        
        # Check for CAPTCHA (pydoll handles Cloudflare automatically)
        if browser_type != 'pydoll':
            print("\n🔍 Checking for CAPTCHA...")
            captcha_detected = await detect_and_solve_captcha(page, max_wait=60)
            
            if captcha_detected:
                print("✅ CAPTCHA was detected and handled!")
            else:
                print("ℹ️  No CAPTCHA detected")
        else:
            print("\n✅ pydoll automatically handles Cloudflare challenges")
        
        # Check for consent screens
        print("\n🍪 Checking for consent screens...")
        await handle_consent_and_blockages(page, test_url)
        
        # Wait a bit
        await page.wait_for_timeout(3000)
        
        # Check page content
        print("\n📄 Analyzing page content...")
        
        # Get content based on browser type
        if hasattr(page, 'content'):  # For Playwright-based browsers
            content = await page.content()
        else:  # For pydoll Tab objects
            result = await page.execute_script("return document.documentElement.outerHTML")
            # Handle potential dict response from pydoll
            if isinstance(result, dict) and 'result' in result:
                content = result['result']
            elif isinstance(result, dict) and 'value' in result:
                content = result['value']
            elif isinstance(result, str):
                content = result
            else:
                content = str(result) if result is not None else ""

        # Check for blocking indicators
        blocking_indicators = [
            'captcha', 'verify', 'robot', 'challenge', 
            'access denied', 'blocked', 'unusual traffic'
        ]
        
        content_lower = content.lower()
        blocked = any(indicator in content_lower for indicator in blocking_indicators)
        
        if blocked:
            print("❌ Page appears to be blocked or showing CAPTCHA")
            print("   This may be normal - check the browser window")
        else:
            print("✅ Page appears to be accessible!")
            
            # Check for event content
            if 'event' in content_lower and ('card' in content_lower or 'listing' in content_lower):
                print("✅ Event content detected on page!")
            else:
                print("⚠️  No event content detected yet (may need to wait)")
        
        # Take a screenshot
        screenshot_path = "test_eventbrite_access.png"
        if browser_type == 'pydoll':
            await page.screenshot(screenshot_path)
        else:
            await page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n📸 Screenshot saved to: {screenshot_path}")
        
        print("\n⏸️  Keeping browser open for 10 seconds for inspection...")
        await asyncio.sleep(10)
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if browser:
            print("\n🔒 Closing browser...")
            await close_undetected_browser(browser, browser_type)
        
        print("\n✅ Test completed!")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Enhanced CAPTCHA & Anti-Detection Test Suite")
    print("=" * 60)
    
    await test_eventbrite_access()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    print("\nRecommendations:")
    
    if not PYDOLL_AVAILABLE:
        print("📦 Install pydoll for Cloudflare bypass: pip install pydoll")
    if not PATCHRIGHT_AVAILABLE:
        print("📦 Install Patchright for enhanced stealth: pip install patchright")
    
    print("\n💡 Next steps:")
    print("1. If successful, run: python scrapeevents.py")
    print("2. Monitor console for '🌐 Using [browser_type] browser'")
    print("3. Check for '✅ Cloudflare bypass completed' messages")


if __name__ == "__main__":
    asyncio.run(main())
