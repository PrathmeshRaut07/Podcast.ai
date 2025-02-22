from fastapi import APIRouter, Depends, HTTPException
from models.podcast_model import PodcastCreate, Podcast
from database.db import podcasts_collection
from functions.auth import get_current_user
from functions.podcast import PodcastGenerator
import base64
import os
from datetime import datetime
import uuid
from typing import List
from pydub import AudioSegment
from io import BytesIO
from dotenv import load_dotenv
load_dotenv()
router = APIRouter(prefix="/podcasts", tags=["Podcasts"])
generator = PodcastGenerator(google_api_key=os.getenv("GOOGLE_API_KEY"))

def audio_to_base64(audio_segment: AudioSegment) -> str:
    """Convert AudioSegment to base64 string"""
    buffer = BytesIO()
    audio_segment.export(buffer, format="mp3")
    return base64.b64encode(buffer.getvalue()).decode()

def base64_to_audio(base64_string: str) -> AudioSegment:
    """Convert base64 string to AudioSegment"""
    audio_data = base64.b64decode(base64_string)
    buffer = BytesIO(audio_data)
    return AudioSegment.from_mp3(buffer)

@router.post("/create", response_model=Podcast)
async def create_podcast(
    podcast: PodcastCreate,
    user_email: str = Depends(get_current_user)
):
    """Create a new podcast for the authenticated user"""
    try:
        # Generate temporary file path
        temp_path = f"temp_{uuid.uuid4()}.mp3"
        
        # Generate podcast
        generator.generate_podcast(
            topic=podcast.topic,
            output_filename=temp_path
        )
        
        # Read the audio file and convert to base64
        audio = AudioSegment.from_mp3(temp_path)
        duration = len(audio) / 1000.0  # Duration in seconds
        audio_base64 = audio_to_base64(audio)
        
        # Clean up temporary file
        os.remove(temp_path)
        
        # Create podcast document
        podcast_doc = {
            "id": str(uuid.uuid4()),
            "user_email": user_email,
            "title": podcast.title,
            "description": podcast.description,
            "topic": podcast.topic,
            "audio_base64": audio_base64,
            "created_at": datetime.now(),
            "duration_seconds": duration
        }
        
        # Insert into database
        result = podcasts_collection.insert_one(podcast_doc)
        
        # Return the created podcast
        return podcast_doc

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate podcast: {str(e)}"
        )

@router.get("/", response_model=List[Podcast])
async def get_user_podcasts(user_email: str = Depends(get_current_user)):
    """Get all podcasts for the authenticated user"""
    try:
        podcasts = list(podcasts_collection.find({"user_email": user_email}))
        return podcasts
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch podcasts: {str(e)}"
        )

@router.get("/{podcast_id}", response_model=Podcast)
async def get_podcast(
    podcast_id: str,
    user_email: str = Depends(get_current_user)
):
    """Get a specific podcast by ID"""
    podcast = podcasts_collection.find_one({
        "id": podcast_id,
        "user_email": user_email
    })
    
    if not podcast:
        raise HTTPException(
            status_code=404,
            detail="Podcast not found"
        )
    
    return podcast

@router.delete("/{podcast_id}")
async def delete_podcast(
    podcast_id: str,
    user_email: str = Depends(get_current_user)
):
    """Delete a podcast by ID"""
    result = podcasts_collection.delete_one({
        "id": podcast_id,
        "user_email": user_email
    })
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Podcast not found"
        )
    
    return {"message": f"Podcast {podcast_id} deleted successfully"}

@router.get("/{podcast_id}/audio")
async def get_podcast_audio(
    podcast_id: str,
    user_email: str = Depends(get_current_user)
):
    """Get the audio file for a podcast"""
    from fastapi.responses import StreamingResponse
    
    podcast = podcasts_collection.find_one({
        "id": podcast_id,
        "user_email": user_email
    })
    
    if not podcast:
        raise HTTPException(
            status_code=404,
            detail="Podcast not found"
        )
    
    try:
        # Convert base64 to audio
        audio = base64_to_audio(podcast["audio_base64"])
        
        # Create a buffer for streaming
        buffer = BytesIO()
        audio.export(buffer, format="mp3")
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'attachment; filename="{podcast["title"]}.mp3"'
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process audio: {str(e)}"
        )