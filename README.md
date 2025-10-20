# 🏢 Jyoti Cards - Stock Management System

A clean, B2B-focused stock checking application for Jyoti Cards.

---

## 📁 Project Structure

```
jyoti-cards-stock-management-streamlit-app/
├── app.py                          # Main application file
├── data/                           # Data folder (UPDATE FILES HERE)
│   ├── website stock.xlsx          # 📊 MAIN STOCK FILE - Update this regularly
│   ├── ALTER LIST 2026.xlsx        # Alternative items
│   └── PORTAL MINIMUM STOCK.xlsx   # Minimum stock thresholds
├── images/                         # Product images (526 photos)
├── docs/                           # Documentation
│   ├── B2B_CHANGES.md
│   └── IMPROVEMENTS.md
├── requirements.txt                # Python dependencies
├── Procfile                        # Deployment config
├── venv/                           # Virtual environment
└── README.md                       # This file
```

---

## 🚀 How to Use

### **For Daily Use (Stock Updates)**

1. **Update Stock File**

   - Open `data/website stock.xlsx`
   - Update the quantities in the file
   - Save the file

2. **Run the Application**

   ```bash
   source venv/bin/activate
   streamlit run app.py
   ```

3. **Reload Data**
   - In the app, click the 🔄 reload button
   - OR restart the application
   - Stock will automatically refresh!

---

## 🎯 Features

✅ **Simple Stock Check** - Customers see "In Stock" or "Out of Stock"  
✅ **Item Images** - Display product photos  
✅ **Alternative Items** - Show alternatives when out of stock  
✅ **WhatsApp Integration** - Pre-filled messages with item numbers  
✅ **Call Button** - Direct phone link  
✅ **Mobile Optimized** - Works perfectly on phones  
✅ **B2B Privacy** - Stock quantities hidden from customers

---

## 📞 Contact Settings

Edit these in `app.py` (lines 25-26):

```python
phone_number = "07312506986"          # Call button
whatsapp_phone = "919516789702"       # WhatsApp button
```

---

## 🎨 Customization

### Change Offer Banner

Edit `app.py` (line 33):

```python
OFFER_TEXT = "🎉 New arrivals now available"
```

### Disable Offer Banner

Edit `app.py` (line 32):

```python
OFFER_ENABLED = False
```

---

## 📊 Data Files Explained

### 1. `website stock.xlsx` (MAIN FILE - Update This!)

- Contains current stock quantities
- Update this file when stock changes
- App reads from column 0 (Item Number) and column 2 (Quantity)

### 2. `ALTER LIST 2026.xlsx`

- Lists alternative items for each product
- Use when main item is out of stock
- Columns: Item No, Alt1, Alt2, Alt3

### 3. `PORTAL MINIMUM STOCK.xlsx`

- Minimum stock thresholds
- Determines "Low Stock" vs "In Stock"
- Customers don't see these numbers

---

## 🖼️ Adding New Product Images

1. Add image to `images/` folder
2. Name it with item number: `1001.jpeg`
3. Supported formats: `.jpg`, `.jpeg`, `.png`
4. Restart app or reload data

---

## 🔧 Troubleshooting

### Application Won't Start

```bash
cd /Users/sourabhagrawal/Downloads/anshul/jyoti-cards-stock-management-streamlit-app
source venv/bin/activate
streamlit run app.py
```

### Stock Not Updating

1. Click 🔄 reload button in app
2. OR restart the application
3. Check that file is saved properly

### Image Not Showing

- Check filename matches item number
- Image must be in `images/` folder
- Supported: `.jpg`, `.jpeg`, `.png`

---

## 🌐 Access Points

### Local (Your Computer)

```
http://localhost:8501
```

### Network (Mobile/Other Devices)

```
http://YOUR_IP:8501
```

(IP shown when app starts)

---

## 📱 Mobile Access

1. Start the app on your computer
2. Note the "Network URL" in terminal
3. Open that URL on your mobile
4. Bookmark it for easy access!

---

## 🛠️ Technical Details

**Built With:**

- Python 3.13
- Streamlit 1.50.0
- Pandas for data processing
- OpenPyXL for Excel files

**Performance:**

- Cached data loading
- Cached image lookups
- Fast response times

---

## 📋 Quick Reference

| Task          | Action                         |
| ------------- | ------------------------------ |
| Update Stock  | Edit `data/website stock.xlsx` |
| Start App     | `streamlit run app.py`         |
| Reload Data   | Click 🔄 in app                |
| Add Image     | Copy to `images/` folder       |
| Change Phone  | Edit `app.py` lines 25-26      |
| Change Banner | Edit `app.py` line 33          |

---

## ⚠️ Important Notes

1. **Always save Excel files** before reloading in app
2. **Don't rename** the data folder or files
3. **Keep file formats** as they are (`.xlsx`)
4. **Stock quantities** are hidden from customers
5. **Update `website stock.xlsx`** - that's the main file!

---

## 💡 Tips

✅ **Bookmark the app URL** on mobile  
✅ **Keep `website stock.xlsx` updated daily**  
✅ **Use WhatsApp for customer inquiries**  
✅ **Check alternatives list periodically**  
✅ **Add new product images regularly**

---

## 📞 Support

For technical issues or questions about the application, contact your technical support.

---

## 🎉 Success!

Your application is clean, organized, and ready to use!

Just update `data/website stock.xlsx` and reload the app whenever stock changes. That's it! 🚀

---

**Version:** 2.0  
**Last Updated:** October 2025  
**Status:** ✅ Production Ready
