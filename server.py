from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from pymongo import MongoClient
import os
import base64
import requests

app = FastAPI(title="NAMEBOT API")

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://test12:test12@cluster0.z1pajuv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['character_database']
characters_collection = db['characters1']

# External API configuration
EXTERNAL_API_URL = "http://cheatbot.twc1.net/getName"
API_TOKEN = os.getenv("API_TOKEN", "TEST-API-TOKEN")

# Telegram bot token
BOT_TOKEN = "7641338523:AAHFp7CqS1bTcBJy5xKu-EdVY1ijMel4ucg"
REQUIRED_CHANNEL = "Zyro_Network"

class CharacterRequest(BaseModel):
    user_id: int
    image_unique_id: str
    file_id: Optional[str] = None

async def check_channel_membership(user_id: int) -> bool:
    """Check if a user is a member of the required Telegram channel."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {
        "chat_id": f"@{REQUIRED_CHANNEL}",
        "user_id": user_id
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("result", {}).get("status") not in ["left", "kicked"]:
                return True
        return False
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False

@app.post("/identify")
async def identify_character(request: CharacterRequest):
    """
    Identify an anime character from an image.
    
    First checks if the user is a member of the required channel.
    Then tries to find the character in MongoDB using the image_unique_id.
    If not found and file_id is provided, downloads the image and queries the external API.
    """
    # Check if user is a member of the required channel
    is_member = await check_channel_membership(request.user_id)
    if not is_member:
        return {
            "status": False,
            "error": "You must join our channel first",
            "join_link": f"https://t.me/{REQUIRED_CHANNEL}"
        }
    
    # Try to find character in MongoDB
    character = characters_collection.find_one({"image_id": request.image_unique_id})
    if character:
        return {
            "status": True,
            "name": character.get("name"),
            "anime": character.get("anime", "Unknown"),
            "rarity": character.get("rarity", "Unknown")
        }
    
    # If not found and file_id is provided, download and query API
    if request.file_id:
        # Get file path
        file_info_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
        file_params = {"file_id": request.file_id}
        
        try:
            file_response = requests.get(file_info_url, params=file_params)
            if file_response.status_code == 200:
                file_data = file_response.json()
                if file_data.get("ok"):
                    file_path = file_data["result"]["file_path"]
                    
                    # Download file
                    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                    image_response = requests.get(download_url)
                    if image_response.status_code == 200:
                        # Convert to base64
                        encoded_image = base64.b64encode(image_response.content).decode('utf-8')
                        
                        # Query external API
                        payload = {
                            "api_token": API_TOKEN,
                            "photo_b64": encoded_image
                        }
                        
                        api_response = requests.post(EXTERNAL_API_URL, json=payload)
                        if api_response.status_code == 200:
                            result = api_response.json()
                            
                            if result.get("status", False):
                                name = result.get("name")
                                
                                # Save to MongoDB for future use
                                if name and name.strip() != "":
                                    characters_collection.insert_one({
                                        "image_id": request.image_unique_id,
                                        "name": name
                                    })
                                
                                return {
                                    "status": True,
                                    "name": name,
                                    "source": "external_api"
                                }
        except Exception as e:
            return {"status": False, "error": str(e)}
    
    return {"status": False, "error": "Character not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
