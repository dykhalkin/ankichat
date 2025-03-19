# Deck Management and CSV User Manual

This guide provides instructions on using the deck management and CSV import/export features of AnkiChat.

## Deck Management

### Creating a New Deck

1. Navigate to your decks view
2. Select "Create New Deck"
3. Enter a name and optional description
4. Click "Create"

Your new deck will be created immediately and ready for use.

### Renaming a Deck

1. Open the deck you want to rename
2. Click the "Settings" or "Edit" button
3. Select "Rename Deck"
4. Enter the new name
5. Click "Save"

### Deleting a Deck

1. Open the deck you want to delete
2. Click the "Settings" or "Edit" button
3. Select "Delete Deck"
4. Confirm the deletion

**Warning**: Deleting a deck will permanently remove all flashcards it contains.

### Moving Flashcards Between Decks

1. Open the deck containing the flashcard(s)
2. Select the flashcard(s) you want to move
3. Click "Move to Deck"
4. Choose the destination deck
5. Click "Move"

### Automatic Deck Suggestion

When creating new flashcards:

1. Create your flashcard (front and back)
2. Click "Suggest Deck"
3. The system will analyze your content and suggest an appropriate deck
4. Accept the suggestion or choose a different deck

## CSV Import/Export

### Exporting Decks to CSV

#### Exporting a Single Deck

1. Open the deck you want to export
2. Click "Export" or "Export to CSV"
3. Choose a destination folder
4. Click "Export"

The exported file will contain all flashcards in the deck with their complete metadata.

#### Exporting All Decks

1. From the main decks view, click "Export All"
2. Choose a destination folder
3. Click "Export"

Each deck will be exported as a separate CSV file.

### Importing from CSV

#### Basic Import

1. From the main decks view, click "Import"
2. Select a CSV file
3. Choose import options:
   - Import into existing deck
   - Create new decks based on CSV content
4. Click "Import"

#### Smart Import with Automatic Categorization

1. From the main decks view, click "Smart Import"
2. Select a CSV file
3. The system will analyze your flashcards and organize them into appropriate decks
4. Review the suggested organization
5. Click "Import"

### CSV Format

If you're creating your own CSV files for import, use the following format:

```
id,front,back,language,created_at,due_date,interval,ease_factor,review_count,deck_id,deck_name
,French Word,English translation,fr,,,1.0,2.5,0,,French Vocabulary
```

Notes:
- The header row is required
- The `id` field can be left empty for new cards
- The `deck_name` field is used for organizing cards during import
- Dates should be in ISO format (YYYY-MM-DDTHH:MM:SS)

## Tips and Best Practices

1. **Regular Exports**: Export your decks regularly as a backup
2. **Organize by Topic**: Create decks for specific topics or subjects
3. **Use Automatic Suggestions**: Let the system help organize your content
4. **Move Cards**: Don't be afraid to reorganize - moving cards between decks doesn't affect your learning progress
5. **CSV for Bulk Operations**: Use CSV import/export for bulk operations or transferring content