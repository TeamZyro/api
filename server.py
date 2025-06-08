from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import aiohttp
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import base64
import os
from typing import Optional, Dict, Any

app = FastAPI(title="NAMEBOT API", version="1.0.0")

# Configuration
MONGO_URL = "mongodb+srv://test12:test12@cluster0.z1pajuv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_TOKEN = "7641338523:AAHFp7CqS1bTcBJy5xKu-EdVY1ijMel4ucg"
REQUIRED_CHANNEL = "https://t.me/Zyro_Network"
CHANNEL_USERNAME = "Zyro_Network"
EXTERNAL_API_URL = "http://cheatbot.twc1.net/getName"
API_TOKEN = "TEST-API-TOKEN"

# MongoDB setup
client = AsyncIOMotorClient(MONGO_URL)
db = client['character_database']
characters_collection = db['characters1']

class CharacterRequest(BaseModel):
    user_id: int
    img_unique_id: str
    bot_token: str
    file_id: str

class ChannelCheckResponse(BaseModel):
    is_member: bool
    message: str
    join_link: Optional[str] = None

class CharacterResponse(BaseModel):
    success: bool
    character_name: Optional[str] = None
    message: str
    source: Optional[str] = None  # "database" or "api"

async def check_channel_membership(user_id: int) -> ChannelCheckResponse:
    """Check if user is member of required channel"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params={
                "chat_id": f"@{CHANNEL_USERNAME}",
                "user_id": user_id
            }) as response:
                data = await response.json()
                
                if data.get("ok"):
                    member_status = data["result"]["status"]
                    if member_status in ["member", "administrator", "creator"]:
                        return ChannelCheckResponse(
                            is_member=True,
                            message="User is a member of the channel"
                        )
                
                return ChannelCheckResponse(
                    is_member=False,
                    message="Please join our channel first",
                    join_link=REQUIRED_CHANNEL
                )
                
        except Exception as e:
            return ChannelCheckResponse(
                is_member=False,
                message=f"Error checking membership: {str(e)}",
                join_link=REQUIRED_CHANNEL
            )

async def get_character_from_mongo(img_unique_id: str) -> Optional[Dict[str, Any]]:
    """Get character from MongoDB"""
    try:
        character = await characters_collection.find_one({"image_id": img_unique_id})
        return character
    except Exception as e:
        print(f"MongoDB error: {e}")
        return None

async def download_and_process_image(file_id: str) -> Optional[str]:
    """Download image from Telegram and process with external API"""
    try:
        # Get file path from Telegram
        file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status != 200:
                    return None
                    
                file_data = await response.json()
                if not file_data.get("ok"):
                    return None
                
                file_path = file_data["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                
                # Download the actual image
                async with session.get(download_url) as img_response:
                    if img_response.status != 200:
                        return None
                    
                    image_data = await img_response.read()
                    
                    # Convert to base64
                    encoded_string = base64.b64encode(image_data).decode()
                    
                    # Send to external API
                    payload = {
                        "api_token": API_TOKEN,
                        "photo_b64": encoded_string
                    }
                    
                    async with session.post(EXTERNAL_API_URL, json=payload) as api_response:
                        if api_response.status == 200:
                            api_data = await api_response.json()
                            if api_data.get("status", False):
                                return api_data.get("name")
                        
                        return None
                        
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

@app.post("/get_character", response_model=CharacterResponse)
async def get_character(request: CharacterRequest):
    """Main endpoint to get character name"""
    
    # Step 1: Verify bot token
    if request.bot_token != BOT_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid bot token")
    
    # Step 2: Check channel membership
    membership_check = await check_channel_membership(request.user_id)
    if not membership_check.is_member:
        return CharacterResponse(
            success=False,
            message=membership_check.message,
            character_name=membership_check.join_link
        )
    
    # Step 3: Check MongoDB for existing character
    character = await get_character_from_mongo(request.img_unique_id)
    if character and character.get("name"):
        return CharacterResponse(
            success=True,
            character_name=character["name"],
            message="Character found in database",
            source="database"
        )
    
    # Step 4: Download image and process with external API
    character_name = await download_and_process_image(request.file_id)
    if character_name:
        # Save to MongoDB for future use
        try:
            await characters_collection.insert_one({
                "image_id": request.img_unique_id,
                "name": character_name,
                "file_id": request.file_id
            })
        except Exception as e:
            print(f"Error saving to MongoDB: {e}")
        
        return CharacterResponse(
            success=True,
            character_name=character_name,
            message="Character found via external API",
            source="api"
        )
    
    # Step 5: Character not found
    return CharacterResponse(
        success=False,
        message="Character not found",
        character_name=None
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "NAMEBOT API is running"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to NAMEBOT API",
        "version": "1.0.0",
        "endpoints": {
            "get_character": "/get_character",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
