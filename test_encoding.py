import sys
import os
import locale


try:
    print(f"System Encoding: {sys.getdefaultencoding()}")
    print(f"FileSystem Encoding: {sys.getfilesystemencoding()}")
    print(f"Stdout Encoding: {sys.stdout.encoding}")
    print(f"Locale Preferred Encoding: {locale.getpreferredencoding()}")
    print(f"PYTHONUTF8 env var: {os.environ.get('PYTHONUTF8', 'Not Set')}")
    
    # Check if we are running in UTF-8 mode
    if sys.flags.utf8_mode:
         print("SUCCESS: Python is running in UTF-8 mode.")
    else:
         print("WARNING: Python is NOT running in UTF-8 mode. Ensure PYTHONUTF8=1 is set.")

    test_str = "안녕하세요 안티그래비티"

    print(f"Printing Korean: {test_str}")
    
    filename = "test_korean.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(test_str)
        
    with open(filename, "r", encoding="utf-8") as f:
        read_str = f.read()
        
    print(f"Read from file: {read_str}")
    
    if test_str == read_str:
        print("SUCCESS: File I/O with UTF-8 works.")
    else:
        print("FAILURE: File I/O mismatch.")

    # Test without encoding (default)
    try:
        with open("test_default.txt", "w") as f:
            f.write(test_str)
        with open("test_default.txt", "r") as f:
            read_default = f.read()
        print(f"Default encoding used: {read_default}")
    except Exception as e:
        print(f"Default encoding failed: {e}")

except Exception as e:
    print(f"ERROR: {e}")
