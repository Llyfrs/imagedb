import lancedb
import os
from pathlib import Path
from datetime import datetime
from .image_record import ImageRecord


class ImageDB:
    def __init__(self, db_path: str = None):
        # Respect XDG Base Directory
        if not db_path:
            base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
            self.db_dir = base_dir / "imagedb" / "index.lance"
            self.image_dir = base_dir / "imagedb" / "images"
        else:
            self.db_dir = Path(db_path)
            base_dir = self.db_dir.parent
            self.image_dir = base_dir / "images"

        # Ensure directories exist
        self.db_dir.parent.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)

        # Connect to embedded DB
        self.db = lancedb.connect(self.db_dir)
        
        # Create or open the table
        # We pass the Schema class so it knows how to format the data
        self.table_name = "images"
        if self.table_name not in self.db.table_names():
            self.table = self.db.create_table(self.table_name, schema=ImageRecord)
        else:
            self.table = self.db.open_table(self.table_name)

    def add_image(self, embedding: list[float], description: str, file_hash: str, original_filename: str):
        """
        Saves the metadata to LanceDB.
        """
        # Construct the local path where you saved the image
        image_path = str(self.image_dir / f"{file_hash}.png")
        
        data = ImageRecord(
            vector=embedding,
            filename=original_filename or "clipboard.png",
            file_hash=file_hash,
            description=description,
            created_at=datetime.now(),
            path=image_path
        )
        
        # Add to table
        self.table.add([data])

    def search(self, query_vector: list[float], limit: int = 1):
        """
        Performs the vector search.
        """
        # This is the "magic" line for vector search
        results = self.table.search(query_vector).limit(limit).to_list()
        
        return results

    def delete_image(self, file_hash: str) -> bool:
        """
        Deletes an image from the database by file hash.
        Returns True if the image was found and deleted, False otherwise.
        """
        # Check if record exists using a metadata search
        # We search with no vector and a filter
        try:
            results = self.table.search(None).where(f"file_hash = '{file_hash}'").to_list()
            if not results:
                return False
        except Exception:
            # Fallback to a broader check if the above fails
            return False
        
        # Delete from database using file_hash
        # Note: LanceDB delete operation
        self.table.delete(f"file_hash = '{file_hash}'")
        
        # Also delete the image file if it exists
        image_path = self.image_dir / f"{file_hash}.png"
        if image_path.exists():
            try:
                image_path.unlink()
            except OSError:
                pass
        
        return True

