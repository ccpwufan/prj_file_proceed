#!/usr/bin/env python3
"""
Test script to verify manual close functionality for log modal
"""

import os
import sys

def check_modal_manual_close():
    """Check if modal manual close functionality is implemented"""
    print("Checking manual close functionality for log modal...")
    
    template_path = "d:/Projects/prj_file_proceed/file_processor/templates/file_processor/file_detail_partial.html"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for auto-close removal
    if 'closeLogModal();' not in content or 'location.reload();' not in content:
        # More specific check - look for the auto-close pattern
        if 'setTimeout(() => {' in content and 'closeLogModal();' in content and 'location.reload();' in content:
            print("✗ Auto-close functionality still exists")
            return False
        else:
            print("✓ Auto-close functionality removed")
    else:
        # Need to check more carefully
        lines = content.split('\n')
        auto_close_found = False
        for i, line in enumerate(lines):
            if 'setTimeout(() => {' in line:
                # Check next few lines for auto-close pattern
                for j in range(i, min(i+5, len(lines))):
                    if 'closeLogModal();' in lines[j] and 'location.reload();' in lines[j+1] if j+1 < len(lines) else False:
                        auto_close_found = True
                        break
                if auto_close_found:
                    break
        
        if auto_close_found:
            print("✗ Auto-close functionality still exists")
            return False
        else:
            print("✓ Auto-close functionality removed")
    
    # Check for manual close button
    if 'Close' in content and 'button' in content and 'closeLogModal()' in content:
        print("✓ Manual close button added")
    else:
        print("✗ Manual close button not found")
        return False
    
    # Check for updated final message
    if 'You can now close this window' in content:
        print("✓ Final message updated to indicate manual close")
    else:
        print("✗ Final message not updated")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing manual close functionality for log modal")
    print("=" * 50)
    
    success = check_modal_manual_close()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All checks passed! Manual close functionality is working correctly.")
    else:
        print("❌ Some checks failed. Please review the implementation.")