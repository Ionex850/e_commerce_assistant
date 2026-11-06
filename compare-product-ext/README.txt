Cart · Compare — Chrome Extension
===================================

INSTALL
-------
1. Open Chrome → chrome://extensions
2. Enable "Developer mode" (toggle top-right)
3. Click "Load unpacked" → select this folder (cart-compare-ext)

HOW TO USE
----------
1. Navigate to your first product page
2. Click the Cart · Compare icon in the toolbar
3. Click "Capture this tab" in the Product A slot
4. Navigate to the second product page
5. Click the icon again → "Capture this tab" for Product B
6. Click "Save both pages"
   → product_A.html and product_B.html download to your Downloads folder

PYTHON INTEGRATION
------------------
Pass the two saved HTML files to your backend, e.g.:

  python compare.py \
    ~/Downloads/product_A.html \
    ~/Downloads/product_B.html

FILE STRUCTURE
--------------
  manifest.json   — extension config (Manifest V3)
  popup.html      — popup UI
  popup.js        — capture, storage, download logic
  icons/          — toolbar icons (16, 48, 128 px)

PERMISSIONS USED
----------------
  activeTab   — read the currently visible tab
  scripting   — inject a script to grab page HTML
  downloads   — save the HTML files to disk
  storage     — remember captured pages between popup opens
