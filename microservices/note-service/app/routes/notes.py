# microservices/note-service/app/routes/notes.py
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
import logging
from datetime import datetime

from ..models.note import Note, NoteCreate, NoteUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory storage (replace with database in production)
notes_db = {}
note_id_counter = 1


@router.get("/", response_model=List[Note])
async def get_notes(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        tag: Optional[str] = None
):
    """Get all notes with optional filtering"""
    try:
        all_notes = list(notes_db.values())

        # Filter by tag if provided
        if tag:
            all_notes = [note for note in all_notes if tag in note.tags]

        # Apply pagination
        notes = all_notes[skip:skip + limit]

        logger.info(f"Retrieved {len(notes)} notes (filtered by tag: {tag})")
        return notes

    except Exception as e:
        logger.error(f"Error retrieving notes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=Note)
async def create_note(note_data: NoteCreate, request: Request):
    """Create a new note"""
    try:
        global note_id_counter

        note = Note(
            id=note_id_counter,
            title=note_data.title,
            content=note_data.content,
            tags=note_data.tags or [],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        notes_db[note_id_counter] = note
        note_id_counter += 1

        logger.info(f"Created new note: {note.title} (ID: {note.id})")
        return note

    except Exception as e:
        logger.error(f"Error creating note: {e}")
        raise HTTPException(status_code=500, detail="Failed to create note")


@router.get("/{note_id}", response_model=Note)
async def get_note(note_id: int, request: Request):
    """Get a specific note by ID"""
    try:
        if note_id not in notes_db:
            logger.warning(f"Note not found: {note_id}")
            raise HTTPException(status_code=404, detail="Note not found")

        note = notes_db[note_id]
        logger.info(f"Retrieved note: {note.title} (ID: {note_id})")
        return note

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving note {note_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{note_id}", response_model=Note)
async def update_note(note_id: int, note_data: NoteUpdate, request: Request):
    """Update an existing note"""
    try:
        if note_id not in notes_db:
            logger.warning(f"Note not found for update: {note_id}")
            raise HTTPException(status_code=404, detail="Note not found")

        note = notes_db[note_id]

        # Update fields if provided
        if note_data.title is not None:
            note.title = note_data.title
        if note_data.content is not None:
            note.content = note_data.content
        if note_data.tags is not None:
            note.tags = note_data.tags

        note.updated_at = datetime.utcnow()

        logger.info(f"Updated note: {note.title} (ID: {note_id})")
        return note

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating note {note_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update note")


@router.delete("/{note_id}")
async def delete_note(note_id: int, request: Request):
    """Delete a note"""
    try:
        if note_id not in notes_db:
            logger.warning(f"Note not found for deletion: {note_id}")
            raise HTTPException(status_code=404, detail="Note not found")

        deleted_note = notes_db.pop(note_id)
        logger.info(f"Deleted note: {deleted_note.title} (ID: {note_id})")

        return {"message": f"Note {note_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting note {note_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete note")



    @router.get("/health", tags=["Monitoring"])
    async def health_check():
        return {"status": "healthy"}


