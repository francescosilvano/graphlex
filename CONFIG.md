# Configuration

## Key Configuration Files

### **scripts/config.py**
Contains all configuration parameters:
- **API Credentials**: Bluesky authentication settings
- **Keywords**: Define which keywords to track
- **Analysis Settings**: Co-occurrence thresholds, date ranges, filters
- **Archive Settings**: Enable/disable run archiving
- **Output Paths**: Configure where results are saved

### **scripts/main.py**
Application entry point that orchestrates:
1. Data collection from Bluesky API
2. Co-occurrence analysis
3. Network graph generation
4. Metric computation
5. Visualization and export

### **scripts/graph.py**
Network analysis implementation using NetworkX:
- Graph construction from co-occurrence data
- Local metrics: degree, strength, betweenness, closeness
- Global metrics: density, clustering, diameter
- Community detection (Louvain algorithm)
- Visualization generation

### **scripts/archive.py**
Run management utilities:
- UUID-based directory creation
- Manifest generation
- Run indexing
- CLI tools for browsing and cleanup

## Customizing Keywords

Edit `settings.json` in the project root to modify keywords and other settings:

```json

{
    "1ST_GROUP": [
        "main_keyword_1",
        "main_keyword_2",
        "main_keyword_3",
        "main_keyword_4",
        "main_keyword_5",
        "main_keyword_6",
        "main_keyword_7",
        "main_keyword_8",
        "main_keyword_9",
        "main_keyword_10"
    ],
    "2ND_GROUP": [
    "group_keyword_1",
    "group_keyword_2",
    "group_keyword_3",
    "group_keyword_4",
    "group_keyword_5",
    "group_keyword_6",
    "group_keyword_7",
    "group_keyword_8",
    "group_keyword_9",
    "group_keyword_10"
    ],
    "3RD_GROUP": [
        "extra_keyword_1",
        "extra_keyword_2",
        "extra_keyword_3",
        "extra_keyword_4",
        "extra_keyword_5"
    ],
    "LOCATION_KEYWORDS": ["california", "quebec", "norway"],
    "DATE_START": "2023-01-01",
    "DATE_END": "2025-11-25",
    "MIN_CO_OCCURRENCES": 1,
    "INPUT_FILE": "../exports/bluesky_posts_complex.csv",
    "OUTPUT_DIR": "../exports",
    "ARCHIVE_ENABLED": true,
    "ARCHIVE_DIR": "../exports/runs"
}
```

All keyword searches are **case-insensitive** for comprehensive matching.

The CLI reads this file when it starts. The first analysis uses `1ST_GROUP`,
the second adds `2ND_GROUP`, and the full analysis adds `3RD_GROUP`. To use
another file, set `GRAPHLEX_SETTINGS_FILE` to its path before launching the CLI.
Dates must use `YYYY-MM-DD` format.

## Environment Variables

Create a `.env` file in the project root:

```env
BLUESKY_HANDLE=your.handle.bsky.social
BLUESKY_PASSWORD=your-password
```