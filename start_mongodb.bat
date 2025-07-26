@echo off
echo Starting MongoDB...
echo Please make sure MongoDB is installed on your system.
echo.
echo If MongoDB is not installed, you can:
echo 1. Install MongoDB Community Server from https://www.mongodb.com/try/download/community
echo 2. Or use MongoDB Atlas (cloud) and update the MONGODB_URI in config.py
echo.
echo Starting local MongoDB (if installed)...
mongod --dbpath "C:\data\db"
pause
